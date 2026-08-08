"""
Cache en mémoire, simple et sans dépendance externe (remplace Firestore).

Le cache est perdu à chaque redémarrage du serveur — c'est le compromis
accepté pour ne pas dépendre d'un service externe. Ça n'empêche en rien
le bot de fonctionner ; ça évite juste de re-traiter deux fois la même
affirmation pendant qu'une instance du serveur tourne.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

_cache_store: dict = {}

DEFAULT_TTL_HOURS = 36  # cf. cahier des charges section 10


def _make_cache_key(claim: str, lang: str) -> str:
    """Génère une clé de cache stable à partir de l'affirmation et de la langue."""
    normalized = claim.strip().lower()
    raw_key = f"{lang}:{normalized}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_cached_verdict(claim: str, lang: str) -> Optional[dict]:
    """Retourne le verdict en cache s'il existe et n'est pas expiré, sinon None."""
    key = _make_cache_key(claim, lang)
    entry = _cache_store.get(key)

    if entry is None:
        return None

    if entry["expireAt"] < datetime.now(timezone.utc):
        del _cache_store[key]
        return None

    print(f"Cache HIT pour la clé {key[:8]}...")
    return entry["verdict"]


def set_cached_verdict(claim: str, lang: str, verdict: dict, ttl_hours: int = DEFAULT_TTL_HOURS) -> None:
    """Enregistre un verdict en cache mémoire avec une date d'expiration."""
    key = _make_cache_key(claim, lang)
    _cache_store[key] = {
        "verdict": verdict,
        "expireAt": datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    }
    print(f"Verdict mis en cache mémoire (clé {key[:8]}..., expire dans {ttl_hours}h)")