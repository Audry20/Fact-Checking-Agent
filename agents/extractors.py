# import os
# import requests
# from bs4 import BeautifulSoup

# from crewai import Agent, Task, Crew, LLM
# from crewai.tools import tool

# GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# # Modèle texte : rapide, adapté à l'extraction/reformulation.
# # ATTENTION : llama-3.3-70b-versatile est déprécié chez Groq depuis
# # le 17 juin 2026 — ne pas l'utiliser (cf. cahier des charges).
# text_llm = LLM(model="groq/openai/gpt-oss-120b", api_key=GROQ_API_KEY, temperature=0)

# # Modèle vision : seul modèle multimodal disponible sur Groq à ce jour.
# vision_llm = LLM(
#     model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
#     api_key=GROQ_API_KEY,
#     temperature=0,
# )


# @tool("Récupérateur de page web")
# def fetch_page_content(url: str) -> str:
#     """Récupère et nettoie le contenu textuel d'une page web à partir de son URL."""
#     try:
#         response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, "html.parser")

#         for tag in soup(["script", "style", "nav", "footer", "header"]):
#             tag.decompose()

#         text = soup.get_text(separator=" ", strip=True)
#         return text[:5000]  # limite pour ne pas saturer le contexte du LLM
#     except requests.RequestException as e:
#         return f"Erreur lors de la récupération de la page : {e}"


# def extract_from_text(raw_text: str) -> str:
#     """
#     Agent d'extraction pour un message texte brut : isole l'affirmation
#     vérifiable exacte, en filtrant le bruit (salutations, contexte inutile).
#     """
#     extractor = Agent(
#         role="Extracteur d'affirmations",
#         goal="Isoler l'affirmation factuelle exacte et vérifiable contenue dans un message",
#         backstory=(
#             "Tu es un journaliste expérimenté, spécialisé dans l'identification "
#             "précise des affirmations vérifiables au sein de messages parfois "
#             "confus ou informels. Tu ne gardes que le cœur factuel testable, "
#             "sans opinion ni contexte inutile."
#         ),
#         llm=text_llm,
#         verbose=False,
#     )

#     task = Task(
#         description=(
#             f'Voici un message reçu sur WhatsApp : "{raw_text}"\n\n'
#             "Reformule-le en UNE SEULE phrase factuelle, claire et vérifiable. "
#             "Si le message contient plusieurs affirmations, garde la principale. "
#             "Ne réponds qu'avec la phrase reformulée, rien d'autre."
#         ),
#         expected_output="Une phrase factuelle unique et vérifiable.",
#         agent=extractor,
#     )

#     crew = Crew(agents=[extractor], tasks=[task], verbose=False)
#     result = crew.kickoff()
#     return str(result).strip()


# def extract_from_link(url: str) -> str:
#     """
#     Agent d'extraction pour un lien : récupère le contenu de la page,
#     puis isole l'affirmation principale qu'elle avance.
#     """
#     extractor = Agent(
#         role="Extracteur d'affirmations depuis une page web",
#         goal="Identifier l'affirmation factuelle principale défendue par un article",
#         backstory=(
#             "Tu es un journaliste expérimenté qui lit rapidement un article "
#             "et en extrait l'affirmation centrale, vérifiable, sans te laisser "
#             "distraire par le style ou les détails secondaires."
#         ),
#         llm=text_llm,
#         tools=[fetch_page_content],
#         verbose=False,
#     )

#     task = Task(
#         description=(
#             f"Récupère le contenu de cette page : {url}\n\n"
#             "Puis reformule en UNE SEULE phrase factuelle et vérifiable "
#             "l'affirmation principale défendue par cet article. "
#             "Ne réponds qu'avec la phrase reformulée, rien d'autre."
#         ),
#         expected_output="Une phrase factuelle unique et vérifiable.",
#         agent=extractor,
#     )

#     crew = Crew(agents=[extractor], tasks=[task], verbose=False)
#     result = crew.kickoff()
#     return str(result).strip()


# def extract_from_image(image_url: str) -> str:
#     """
#     Agent vision : décrit l'image et extrait le texte qu'elle contient
#     (capture d'écran, image avec texte incrusté, etc.), puis isole
#     l'affirmation vérifiable qui s'en dégage.

#     NOTE IMPORTANTE : les URLs d'images WhatsApp nécessitent une
#     authentification par token pour être téléchargées (contrairement à
#     une URL publique classique). Il faudra un utilitaire de récupération
#     des médias WhatsApp (Graph API /media/{media-id}) avant de brancher
#     cette fonction en production — TODO de la prochaine étape.
#     """
#     vision_agent = Agent(
#         role="Analyste visuel",
#         goal="Décrire une image et en extraire toute affirmation factuelle vérifiable",
#         backstory=(
#             "Tu es un analyste spécialisé en désinformation visuelle. Tu lis "
#             "attentivement le texte incrusté dans les images (captures d'écran, "
#             "mèmes, publications) et identifies l'affirmation factuelle "
#             "qu'elles véhiculent."
#         ),
#         llm=vision_llm,
#         multimodal=True,
#         verbose=False,
#     )

#     task = Task(
#         description=(
#             f"Analyse l'image à cette URL : {image_url}\n\n"
#             "Décris ce qu'elle montre, transcris tout texte visible, puis "
#             "reformule en UNE SEULE phrase factuelle et vérifiable "
#             "l'affirmation principale véhiculée par l'image. "
#             "Ne réponds qu'avec la phrase reformulée, rien d'autre."
#         ),
#         expected_output="Une phrase factuelle unique et vérifiable.",
#         agent=vision_agent,
#     )

#     crew = Crew(agents=[vision_agent], tasks=[task], verbose=False)
#     result = crew.kickoff()
#     return str(result).strip()

import os
import requests
from bs4 import BeautifulSoup

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

from utils.retry import run_crew_with_retry

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Modèle texte : gpt-oss-20b plutôt que 120b pour cette tâche simple
# (reformulation) — répartit la charge sur un quota tokens/minute séparé
# de celui du chercheur/directeur, qui utilisent le modèle 120b.
# ATTENTION : llama-3.3-70b-versatile est déprécié chez Groq depuis
# le 17 juin 2026 — ne pas l'utiliser (cf. cahier des charges).
text_llm = LLM(model="groq/openai/gpt-oss-20b", api_key=GROQ_API_KEY, temperature=0)

# Modèle vision : seul modèle multimodal disponible sur Groq à ce jour.
vision_llm = LLM(
    model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=GROQ_API_KEY,
    temperature=0,
)


@tool("Récupérateur de page web")
def fetch_page_content(url: str) -> str:
    """Récupère et nettoie le contenu textuel d'une page web à partir de son URL."""
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return text[:5000]  # limite pour ne pas saturer le contexte du LLM
    except requests.RequestException as e:
        return f"Erreur lors de la récupération de la page : {e}"


def extract_from_text(raw_text: str) -> str:
    """
    Agent d'extraction pour un message texte brut : isole l'affirmation
    vérifiable exacte, en filtrant le bruit (salutations, contexte inutile).
    """
    extractor = Agent(
        role="Extracteur d'affirmations",
        goal="Isoler l'affirmation factuelle exacte et vérifiable contenue dans un message",
        backstory=(
            "Tu es un journaliste expérimenté, spécialisé dans l'identification "
            "précise des affirmations vérifiables au sein de messages parfois "
            "confus ou informels. Tu ne gardes que le cœur factuel testable, "
            "sans opinion ni contexte inutile."
        ),
        llm=text_llm,
        verbose=False,
    )

    task = Task(
        description=(
            f'Voici un message reçu sur WhatsApp : "{raw_text}"\n\n'
            "Reformule-le en UNE SEULE phrase factuelle, claire et vérifiable. "
            "Si le message contient plusieurs affirmations, garde la principale. "
            "Ne réponds qu'avec la phrase reformulée, rien d'autre."
        ),
        expected_output="Une phrase factuelle unique et vérifiable.",
        agent=extractor,
    )

    crew = Crew(agents=[extractor], tasks=[task], verbose=False)
    result = run_crew_with_retry(crew)
    return str(result).strip()


def extract_from_link(url: str) -> str:
    """
    Agent d'extraction pour un lien : récupère le contenu de la page,
    puis isole l'affirmation principale qu'elle avance.
    """
    extractor = Agent(
        role="Extracteur d'affirmations depuis une page web",
        goal="Identifier l'affirmation factuelle principale défendue par un article",
        backstory=(
            "Tu es un journaliste expérimenté qui lit rapidement un article "
            "et en extrait l'affirmation centrale, vérifiable, sans te laisser "
            "distraire par le style ou les détails secondaires."
        ),
        llm=text_llm,
        tools=[fetch_page_content],
        verbose=False,
    )

    task = Task(
        description=(
            f"Récupère le contenu de cette page : {url}\n\n"
            "Puis reformule en UNE SEULE phrase factuelle et vérifiable "
            "l'affirmation principale défendue par cet article. "
            "Ne réponds qu'avec la phrase reformulée, rien d'autre."
        ),
        expected_output="Une phrase factuelle unique et vérifiable.",
        agent=extractor,
    )

    crew = Crew(agents=[extractor], tasks=[task], verbose=False)
    result = run_crew_with_retry(crew)
    return str(result).strip()


def extract_from_image(image_url: str) -> str:
    """
    Agent vision : décrit l'image et extrait le texte qu'elle contient
    (capture d'écran, image avec texte incrusté, etc.), puis isole
    l'affirmation vérifiable qui s'en dégage.

    NOTE IMPORTANTE : les URLs d'images WhatsApp nécessitent une
    authentification par token pour être téléchargées (contrairement à
    une URL publique classique). Il faudra un utilitaire de récupération
    des médias WhatsApp (Graph API /media/{media-id}) avant de brancher
    cette fonction en production — TODO de la prochaine étape.
    """
    vision_agent = Agent(
        role="Analyste visuel",
        goal="Décrire une image et en extraire toute affirmation factuelle vérifiable",
        backstory=(
            "Tu es un analyste spécialisé en désinformation visuelle. Tu lis "
            "attentivement le texte incrusté dans les images (captures d'écran, "
            "mèmes, publications) et identifies l'affirmation factuelle "
            "qu'elles véhiculent."
        ),
        llm=vision_llm,
        multimodal=True,
        verbose=False,
    )

    task = Task(
        description=(
            f"Analyse l'image à cette URL : {image_url}\n\n"
            "Décris ce qu'elle montre, transcris tout texte visible, puis "
            "reformule en UNE SEULE phrase factuelle et vérifiable "
            "l'affirmation principale véhiculée par l'image. "
            "Ne réponds qu'avec la phrase reformulée, rien d'autre."
        ),
        expected_output="Une phrase factuelle unique et vérifiable.",
        agent=vision_agent,
    )

    crew = Crew(agents=[vision_agent], tasks=[task], verbose=False)
    result = run_crew_with_retry(crew)
    return str(result).strip()