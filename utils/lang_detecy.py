from langdetect import detect, DetectorFactory, LangDetectException


DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    """
    Détecte la langue d'un texte et la ramène à 'fr' ou 'en'.
    Si la détection échoue (texte trop court, vide, emojis seuls...),
    on retombe sur le français par défaut plutôt que de planter.
    """
    if not text or not text.strip():
        return "fr"

    try:
        detected = detect(text)
    except LangDetectException:
        return "fr"

    
    if detected == "fr":
        return "fr"
    return "en"

