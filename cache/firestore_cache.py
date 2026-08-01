import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation unique de l'app Firebase (évite les erreurs si le module
# est importé plusieurs fois, par exemple lors des rechargements Flask/Gunicorn).
if not firebase_admin._apps:
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

CACHE_COLLECTION = "verdicts_cache"
DEFAULT_TTL_HOURS = 36  # entre 24 et 48h, cf. cahier des charges section 10


def _make_cache_key(claim: str, lang: str) -> str:
    """
    Génère une clé de cache stable à partir de l'affirmation normalisée
    et de la langue. On hash pour éviter les caractères spéciaux/longueur
    excessive dans l'ID du document Firestore.
    """
    normalized = claim.strip().lower()
    raw_key = f"{lang}:{normalized}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_cached_verdict(claim: str, lang: str) -> Optional[dict]:
    """
    Cherche un verdict déjà mis en cache pour cette affirmation.
    Retourne le verdict (dict) s'il existe et n'est pas expiré, sinon None.

    La suppression effective des entrées expirées est gérée par la
    politique TTL native de Firestore (champ 'expireAt', à configurer
    dans la console Firestore) — on filtre quand même ici par sécurité,
    au cas où Firestore n'aurait pas encore nettoyé le document.
    """
    key = _make_cache_key(claim, lang)
    doc = db.collection(CACHE_COLLECTION).document(key).get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    expire_at = data.get("expireAt")

    if expire_at and expire_at < datetime.now(timezone.utc):
        return None

    print(f"Cache HIT pour la clé {key[:8]}...")
    return data.get("verdict")


def set_cached_verdict(claim: str, lang: str, verdict: dict, ttl_hours: int = DEFAULT_TTL_HOURS) -> None:
    """
    Enregistre un verdict en cache avec une date d'expiration.

    Le champ 'expireAt' doit être configuré comme politique TTL native
    dans la console Firestore (Google Cloud Console > Firestore > TTL)
    pour que Firestore supprime automatiquement le document une fois
    expiré, sans lecture ni logique supplémentaire côté application.
    """
    key = _make_cache_key(claim, lang)
    expire_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    db.collection(CACHE_COLLECTION).document(key).set({
        "claim": claim,
        "lang": lang,
        "verdict": verdict,
        "createdAt": datetime.now(timezone.utc),
        "expireAt": expire_at,
    })
    print(f"Verdict mis en cache (clé {key[:8]}..., expire dans {ttl_hours}h)")