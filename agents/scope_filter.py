import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Modèle rapide et peu coûteux : suffisant pour une classification binaire.
# Les modèles llama-3.3-70b-versatile et llama-3.1-8b-instant sont dépréciés
# depuis le 17 juin 2026 chez Groq — ne pas les utiliser.
SCOPE_MODEL = "openai/gpt-oss-20b"

SCOPE_CHECK_PROMPT = """Tu es un filtre de pertinence pour un assistant de vérification d'informations.

Le message ci-dessous entre-t-il dans un de ces sujets :
- politique internationale
- géopolitique
- économie (y compris finance, commerce, prêts, banques, marchés)
- santé publique
- organisations officielles (nationales ou internationales, ex: ONU, FMI, Banque mondiale, gouvernements)

Exemples qui doivent répondre OUI :
- "Le FMI a accordé un prêt de 500 millions au Burundi" (économie/organisation officielle)
- "Le président du Kenya a rencontré le secrétaire général de l'ONU" (politique/organisation officielle)
- "L'OMS alerte sur une nouvelle épidémie en Afrique de l'Est" (santé publique)

Exemples qui doivent répondre NON :
- "Quelle est la meilleure recette de beignets ?" (hors-sujet)
- "Mon équipe de foot a gagné hier" (hors-sujet)

Réponds uniquement par un seul mot : OUI ou NON.

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
    thématique de Tukutane Facts. Retourne True/False.
    En cas d'erreur API, on retourne False par prudence (on préfère
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
            max_completion_tokens=500,   # laisse de la place au raisonnement interne du modèle
            reasoning_effort="medium",   # "low" faisait mal classer des cas simples ; medium plus fiable
            reasoning_format="hidden",   # garantit que 'content' ne contient QUE la réponse finale
        )
        answer = response.choices[0].message.content.strip().upper()
        print(f"[DEBUG scope_filter] Réponse brute du modèle : {answer!r}")
        # startswith d'abord (cas normal), "in" en filet de sécurité si jamais
        # du texte résiduel précède la réponse malgré reasoning_format=hidden.
        return answer.startswith("OUI") or "OUI" in answer.split()

    except Exception as e:
        print(f"Erreur lors de l'appel au filtre de scope : {e}")
        return False


def get_refusal_message(lang: str) -> str:
    """Retourne le message de refus dans la langue détectée (fr par défaut)."""
    return REFUSAL_MESSAGES.get(lang, REFUSAL_MESSAGES["fr"])