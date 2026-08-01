import re

URL_REGEX = re.compile(r"https?://[^\s]+")


def classify_content_type(message_type: str, text_body: str = None) -> str:
    """
    Détermine vers quel agent d'extraction router le message.
    Ne nécessite aucun appel LLM : une simple détection de type WhatsApp
    + une recherche de lien suffit, c'est plus rapide et plus fiable
    qu'une classification par modèle pour cette tâche précise.

    Retourne : 'image', 'lien', ou 'texte'
    """
    if message_type == "image":
        return "image"

    if message_type == "text" and text_body:
        if URL_REGEX.search(text_body):
            return "lien"
        return "texte"

    return "inconnu"


def extract_url(text_body: str) -> str | None:
    """Extrait la première URL trouvée dans un message texte."""
    match = URL_REGEX.search(text_body)
    return match.group(0) if match else None

