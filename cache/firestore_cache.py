import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

_db = None
_firestore_ready = False


def _init_firestore() -> bool:
    """
    Initialise Firebase à la demande (pas au chargement du module), une
    seule fois. Si les credentials sont absentes ou invalides, le cache
    est simplement désactivé — le reste du pipeline continue de
    fonctionner normalement (chaque requête est traitée comme un cache
    miss, donc re-vérifiée intégralement).

    Ça permet de développer et tester tout le reste du projet sans avoir
    à configurer Firestore tout de suite.
    """
    global _db, _firestore_ready

    if _db is not None:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        _firestore_ready = True
        print("Firestore initialisé avec succès.")

    except Exception as e:
        print(f"Firestore non disponible ({e}) — cache désactivé pour l'instant, "
              f"le pipeline continue sans mise en cache.")
        _firestore_ready = False

    return _firestore_ready


CACHE_COLLECTION = "verdicts_cache"
DEFAULT_TTL_HOURS = 36  # entre 24 et 48h, cf. cahier des charges section 10


def _make_cache_key(claim: str, lang: str) -> str:
    """Clé de cache stable, générée à partir de l'affirmation normalisée + langue."""
    normalized = claim.strip().lower()
    raw_key = f"{lang}:{normalized}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_cached_verdict(claim: str, lang: str) -> Optional[dict]:
    """
    Retourne le verdict en cache s'il existe et n'est pas expiré.
    Retourne None si le cache est désactivé, si rien n'est trouvé, ou
    si l'entrée a expiré.
    """
    if not _init_firestore():
        return None

    key = _make_cache_key(claim, lang)
    doc = _db.collection(CACHE_COLLECTION).document(key).get()

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
    Ne fait rien (silencieusement) si le cache est désactivé — non
    bloquant pour le reste du pipeline.
    """
    if not _init_firestore():
        return

    key = _make_cache_key(claim, lang)
    expire_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    _db.collection(CACHE_COLLECTION).document(key).set({
        "claim": claim,
        "lang": lang,
        "verdict": verdict,
        "createdAt": datetime.now(timezone.utc),
        "expireAt": expire_at,
    })
    print(f"Verdict mis en cache (clé {key[:8]}..., expire dans {ttl_hours}h)")