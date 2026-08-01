import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SCOPE_MODEL = "openai/gpt-oss-20b"

SCOPE_CHECK_PROMPT = """Tu es un filtre strict pour un assistant de vérification d'informations.

Détermine si le message suivant concerne UNIQUEMENT un de ces sujets :
- politique internationale
- géopolitique
- économie
- santé publique
- organisations officielles (nationales ou internationales)

Réponds uniquement par un seul mot : OUI ou NON.
Ne donne aucune explication, aucune ponctuation supplémentaire.

Message : {user_input}
"""

REFUSAL_MESSAGES = {
    "fr": (
        "Je suis un assistant spécialisé dans la vérification d'informations "
        "en politique, géopolitique, économie, santé et organisations officielles. "
        "Cette question sort de mon domaine."
    ),
    "en": (
        "I'm an assistant specialized in fact-checking politics, geopolitics, "
        "economy, health, and official organizations. This question is outside "
        "my scope."
    ),
}


def is_in_scope(user_input: str) -> bool:
    """
    Interroge Groq pour savoir si le message entre dans le périmètre
    thématique de Cheking Facts. Retourne True/False.
    En cas d'erreur API, retourne False par prudence (on préfère
    refuser une question légitime plutôt que de laisser passer du
    hors-scope non vérifié).
    """
    try:
        response = client.chat.completions.create(
            model=SCOPE_MODEL,
            messages=[
                {"role": "user", "content": SCOPE_CHECK_PROMPT.format(user_input=user_input)}
            ],
            temperature=0,
            max_tokens=5,
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer.startswith("OUI")

    except Exception as e:
        print(f"Erreur lors de l'appel au filtre de scope : {e}")
        return False


def get_refusal_message(lang: str) -> str:
    """Retourne le message de refus dans la langue détectée (fr par défaut)."""
    return REFUSAL_MESSAGES.get(lang, REFUSAL_MESSAGES["fr"])

