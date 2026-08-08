# # import os
# # import json
# # import re
# # from typing import List, Literal

# # from pydantic import BaseModel
# # from crewai import Agent, Task, Crew, LLM

# # GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# # director_llm = LLM(model="groq/openai/gpt-oss-120b", api_key=GROQ_API_KEY, temperature=0)


# # class Verdict(BaseModel):
# #     verdict: Literal["REEL", "FAUX", "INCERTAIN"]
# #     confidence: float  # 0.0 à 1.0
# #     langue: Literal["fr", "en"]
# #     sources: List[str]
# #     explication: str


# # def _fallback_verdict(lang: str) -> Verdict:
# #     """Verdict de secours si le JSON du modèle est illisible, plutôt que de planter."""
# #     return Verdict(
# #         verdict="INCERTAIN",
# #         confidence=0.0,
# #         langue=lang,
# #         sources=[],
# #         explication=(
# #             "Une erreur technique a empêché de rendre un verdict fiable. "
# #             "Réessaie dans quelques instants."
# #             if lang == "fr"
# #             else "A technical error prevented rendering a reliable verdict. "
# #             "Please try again shortly."
# #         ),
# #     )


# # def render_verdict(claim: str, evidence: str, critique: str, lang: str) -> Verdict:
# #     """
# #     Agent directeur : synthétise l'affirmation, les preuves du chercheur
# #     et l'analyse du critique pour rendre un verdict final structuré, avec
# #     les sources citées et une explication rédigée pour l'utilisateur.

# #     NOTE : on n'utilise PAS output_pydantic ici (le mécanisme de CrewAI qui
# #     force un appel de "tool" pour produire du JSON structuré). C'est un bug
# #     documenté et récurrent avec les modèles Groq : Groq rejette parfois
# #     l'appel d'outil que CrewAI génère en interne ("tool call validation
# #     failed"), même quand le JSON produit est valide. On demande donc au
# #     modèle d'écrire du JSON en texte brut, qu'on parse nous-mêmes — plus
# #     robuste, avec un verdict de secours si jamais le parsing échoue.
# #     """
# #     director = Agent(
# #         role="Rédacteur en chef - verdict final",
# #         goal="Rendre un verdict de fact-checking clair, honnête et bien sourcé",
# #         backstory=(
# #             "Tu es le rédacteur en chef final de Tukutane Facts. Tu prends "
# #             "la responsabilité du verdict envoyé à l'utilisateur. Tu es "
# #             "rigoureux : si les preuves sont insuffisantes ou contradictoires, "
# #             "tu n'hésites pas à répondre INCERTAIN plutôt que de trancher "
# #             "à la légère. Tu écris toujours dans un style clair, direct, "
# #             "accessible à un lecteur non-expert."
# #         ),
# #         llm=director_llm,
# #         verbose=False,
# #     )

# #     lang_instruction = (
# #         "Rédige le champ 'explication' en français."
# #         if lang == "fr"
# #         else "Write the 'explication' field in English."
# #     )

# #     task = Task(
# #         description=(
# #             f'Affirmation initiale : "{claim}"\n\n'
# #             f"Preuves du chercheur :\n{evidence}\n\n"
# #             f"Analyse du critique :\n{critique}\n\n"
# #             f"{lang_instruction}\n\n"
# #             "Rends ton verdict final. Si l'analyse du critique indique "
# #             "'PREUVES INSUFFISANTES', ton verdict doit être INCERTAIN, sauf "
# #             "si tu as de très bonnes raisons de penser le contraire. "
# #             "Cite dans 'sources' les URLs les plus pertinentes trouvées par "
# #             "le chercheur.\n\n"
# #             "IMPORTANT : réponds UNIQUEMENT avec un objet JSON valide, sans "
# #             "aucun texte avant ou après, sans balises markdown, exactement "
# #             "dans ce format :\n"
# #             '{"verdict": "REEL", "confidence": 0.8, '
# #             f'"langue": "{lang}", "sources": ["https://..."], '
# #             '"explication": "..."}'
# #         ),
# #         expected_output="Un unique objet JSON valide respectant exactement le format demandé.",
# #         agent=director,
# #     )

# #     crew = Crew(agents=[director], tasks=[task], verbose=False)
# #     result = crew.kickoff()
# #     raw_output = str(result).strip()

# #     # Retire d'éventuelles balises markdown (```json ... ```) que le modèle
# #     # ajoute parfois malgré la consigne de ne pas en mettre.
# #     cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_output, flags=re.MULTILINE).strip()

# #     try:
# #         data = json.loads(cleaned)
# #         verdict_obj = Verdict.model_validate(data)
# #     except Exception as e:
# #         print(f"Erreur de parsing du verdict JSON ({e}) — verdict INCERTAIN de secours envoyé.")
# #         print(f"Sortie brute du modèle : {raw_output[:500]}")
# #         verdict_obj = _fallback_verdict(lang)

# #     verdict_obj.langue = lang  # on force la langue détectée, au cas où le modèle l'omette
# #     return verdict_obj


# # VERDICT_EMOJIS = {"REEL": "✅", "FAUX": "❌", "INCERTAIN": "❓"}


# # def format_verdict_message(verdict: Verdict) -> str:
# #     """Met en forme un Verdict pour l'envoi WhatsApp (emoji + sources listées)."""
# #     emoji = VERDICT_EMOJIS.get(verdict.verdict, "")
# #     header = f"{emoji} {verdict.verdict} — confiance : {int(verdict.confidence * 100)}%"

# #     sources_label = "Sources" if verdict.langue == "fr" else "Sources"
# #     sources_text = (
# #         "\n".join(f"- {s}" for s in verdict.sources) if verdict.sources else ""
# #     )
# #     footer = f"\n\n{sources_label} :\n{sources_text}" if sources_text else ""

# #     return f"{header}\n\n{verdict.explication}{footer}"

# import os
# import json
# import re
# from typing import List, Literal

# from pydantic import BaseModel
# from crewai import Agent, Task, Crew, LLM

# from utils.retry import run_crew_with_retry

# GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# director_llm = LLM(model="groq/openai/gpt-oss-120b", api_key=GROQ_API_KEY, temperature=0)


# class Verdict(BaseModel):
#     verdict: Literal["REEL", "FAUX", "INCERTAIN"]
#     confidence: float  # 0.0 à 1.0
#     langue: Literal["fr", "en"]
#     sources: List[str]
#     explication: str


# def _fallback_verdict(lang: str) -> Verdict:
#     """Verdict de secours si le JSON du modèle est illisible, plutôt que de planter."""
#     return Verdict(
#         verdict="INCERTAIN",
#         confidence=0.0,
#         langue=lang,
#         sources=[],
#         explication=(
#             "Une erreur technique a empêché de rendre un verdict fiable. "
#             "Réessaie dans quelques instants."
#             if lang == "fr"
#             else "A technical error prevented rendering a reliable verdict. "
#             "Please try again shortly."
#         ),
#     )


# def render_verdict(claim: str, evidence: str, critique: str, lang: str) -> Verdict:
#     """
#     Agent directeur : synthétise l'affirmation, les preuves du chercheur
#     et l'analyse du critique pour rendre un verdict final structuré, avec
#     les sources citées et une explication rédigée pour l'utilisateur.

#     NOTE : on n'utilise PAS output_pydantic ici (le mécanisme de CrewAI qui
#     force un appel de "tool" pour produire du JSON structuré). C'est un bug
#     documenté et récurrent avec les modèles Groq : Groq rejette parfois
#     l'appel d'outil que CrewAI génère en interne ("tool call validation
#     failed"), même quand le JSON produit est valide. On demande donc au
#     modèle d'écrire du JSON en texte brut, qu'on parse nous-mêmes — plus
#     robuste, avec un verdict de secours si jamais le parsing échoue.
#     """
#     director = Agent(
#         role="Rédacteur en chef - verdict final",
#         goal="Rendre un verdict de fact-checking clair, honnête et bien sourcé",
#         backstory=(
#             "Tu es le rédacteur en chef final de Tukutane Facts. Tu prends "
#             "la responsabilité du verdict envoyé à l'utilisateur. Tu es "
#             "rigoureux : si les preuves sont insuffisantes ou contradictoires, "
#             "tu n'hésites pas à répondre INCERTAIN plutôt que de trancher "
#             "à la légère. Tu écris toujours dans un style clair, direct, "
#             "accessible à un lecteur non-expert."
#         ),
#         llm=director_llm,
#         verbose=False,
#     )

#     lang_instruction = (
#         "Rédige le champ 'explication' en français."
#         if lang == "fr"
#         else "Write the 'explication' field in English."
#     )

#     task = Task(
#         description=(
#             f'Affirmation initiale : "{claim}"\n\n'
#             f"Preuves du chercheur :\n{evidence}\n\n"
#             f"Analyse du critique :\n{critique}\n\n"
#             f"{lang_instruction}\n\n"
#             "Rends ton verdict final. Si l'analyse du critique indique "
#             "'PREUVES INSUFFISANTES', ton verdict doit être INCERTAIN, sauf "
#             "si tu as de très bonnes raisons de penser le contraire. "
#             "Cite dans 'sources' les URLs les plus pertinentes trouvées par "
#             "le chercheur.\n\n"
#             "IMPORTANT : réponds UNIQUEMENT avec un objet JSON valide, sans "
#             "aucun texte avant ou après, sans balises markdown, exactement "
#             "dans ce format :\n"
#             '{"verdict": "REEL", "confidence": 0.8, '
#             f'"langue": "{lang}", "sources": ["https://..."], '
#             '"explication": "..."}'
#         ),
#         expected_output="Un unique objet JSON valide respectant exactement le format demandé.",
#         agent=director,
#     )

#     crew = Crew(agents=[director], tasks=[task], verbose=False)
#     result = run_crew_with_retry(crew)
#     raw_output = str(result).strip()

#     # Retire d'éventuelles balises markdown (```json ... ```) que le modèle
#     # ajoute parfois malgré la consigne de ne pas en mettre.
#     cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_output, flags=re.MULTILINE).strip()

#     try:
#         data = json.loads(cleaned)
#         verdict_obj = Verdict.model_validate(data)
#     except Exception as e:
#         print(f"Erreur de parsing du verdict JSON ({e}) — verdict INCERTAIN de secours envoyé.")
#         print(f"Sortie brute du modèle : {raw_output[:500]}")
#         verdict_obj = _fallback_verdict(lang)

#     verdict_obj.langue = lang  # on force la langue détectée, au cas où le modèle l'omette
#     return verdict_obj


# VERDICT_EMOJIS = {"REEL": "✅", "FAUX": "❌", "INCERTAIN": "❓"}


# def format_verdict_message(verdict: Verdict) -> str:
#     """Met en forme un Verdict pour l'envoi WhatsApp (emoji + sources listées)."""
#     emoji = VERDICT_EMOJIS.get(verdict.verdict, "")
#     header = f"{emoji} {verdict.verdict} — confiance : {int(verdict.confidence * 100)}%"

#     sources_label = "Sources" if verdict.langue == "fr" else "Sources"
#     sources_text = (
#         "\n".join(f"- {s}" for s in verdict.sources) if verdict.sources else ""
#     )
#     footer = f"\n\n{sources_label} :\n{sources_text}" if sources_text else ""

#     return f"{header}\n\n{verdict.explication}{footer}"

import os
import json
import re
from typing import List, Literal

from pydantic import BaseModel
from crewai import Agent, Task, Crew, LLM

from utils.retry import run_crew_with_retry

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

director_llm = LLM(model="groq/openai/gpt-oss-120b", api_key=GROQ_API_KEY, temperature=0)


class Verdict(BaseModel):
    verdict: Literal["REEL", "FAUX", "INCERTAIN"]
    confidence: float  # 0.0 à 1.0
    langue: Literal["fr", "en"]
    sources: List[str]
    explication: str


def _fallback_verdict(lang: str) -> Verdict:
    """Verdict de secours si le JSON du modèle est illisible, plutôt que de planter."""
    return Verdict(
        verdict="INCERTAIN",
        confidence=0.0,
        langue=lang,
        sources=[],
        explication=(
            "Une erreur technique a empêché de rendre un verdict fiable. "
            "Réessaie dans quelques instants."
            if lang == "fr"
            else "A technical error prevented rendering a reliable verdict. "
            "Please try again shortly."
        ),
    )


def render_verdict(claim: str, evidence: str, critique: str, lang: str) -> Verdict:
    """
    Agent directeur : synthétise l'affirmation, les preuves du chercheur
    et l'analyse du critique pour rendre un verdict final structuré, avec
    les sources citées et une explication rédigée pour l'utilisateur.

    NOTE : on n'utilise PAS output_pydantic ici (le mécanisme de CrewAI qui
    force un appel de "tool" pour produire du JSON structuré). C'est un bug
    documenté et récurrent avec les modèles Groq : Groq rejette parfois
    l'appel d'outil que CrewAI génère en interne ("tool call validation
    failed"), même quand le JSON produit est valide. On demande donc au
    modèle d'écrire du JSON en texte brut, qu'on parse nous-mêmes — plus
    robuste, avec un verdict de secours si jamais le parsing échoue.
    """
    director = Agent(
        role="Rédacteur en chef - verdict final",
        goal="Rendre un verdict de fact-checking clair, honnête et bien sourcé",
        backstory=(
            "Tu es le rédacteur en chef final de Tukutane Facts. Tu prends "
            "la responsabilité du verdict envoyé à l'utilisateur. Tu es "
            "rigoureux : si les preuves sont insuffisantes ou contradictoires, "
            "tu n'hésites pas à répondre INCERTAIN plutôt que de trancher "
            "à la légère. Tu écris toujours dans un style clair, direct, "
            "accessible à un lecteur non-expert."
        ),
        llm=director_llm,
        verbose=False,
    )

    lang_instruction = (
        "Rédige le champ 'explication' en français."
        if lang == "fr"
        else "Write the 'explication' field in English."
    )

    task = Task(
        description=(
            f'Affirmation initiale : "{claim}"\n\n'
            f"Preuves du chercheur :\n{evidence}\n\n"
            f"Analyse du critique :\n{critique}\n\n"
            f"{lang_instruction}\n\n"
            "Rends ton verdict final. Si l'analyse du critique indique "
            "'PREUVES INSUFFISANTES', ton verdict doit être INCERTAIN, sauf "
            "si tu as de très bonnes raisons de penser le contraire.\n\n"
            "RÈGLE STRICTE SUR LES SOURCES : le champ 'sources' ne doit "
            "contenir QUE des URLs copiées mot pour mot depuis le texte des "
            "'Preuves du chercheur' ci-dessus. N'invente JAMAIS une URL "
            "(y compris des liens de recherche Google du type "
            "google.com/search?q=...). Si aucune URL exploitable n'apparaît "
            "dans les preuves du chercheur, laisse 'sources' à une liste "
            "vide [].\n\n"
            "RÈGLE SUR LA CLARTÉ : 'explication' doit être courte et directe "
            "(2 à 4 phrases maximum), compréhensible par quelqu'un qui n'a "
            "pas le contexte. Dis d'abord clairement ce qu'on sait avec "
            "certitude, puis pourquoi le verdict est INCERTAIN si c'est le "
            "cas (preuve manquante, source unique, pas de confirmation "
            "officielle...). Évite le jargon et les tournures trop "
            "académiques.\n\n"
            "IMPORTANT : réponds UNIQUEMENT avec un objet JSON valide, sans "
            "aucun texte avant ou après, sans balises markdown, exactement "
            "dans ce format :\n"
            '{"verdict": "REEL", "confidence": 0.8, '
            f'"langue": "{lang}", "sources": ["https://..."], '
            '"explication": "..."}'
        ),
        expected_output="Un unique objet JSON valide respectant exactement le format demandé.",
        agent=director,
    )

    crew = Crew(agents=[director], tasks=[task], verbose=False)
    result = run_crew_with_retry(crew)
    raw_output = str(result).strip()

    # Retire d'éventuelles balises markdown (```json ... ```) que le modèle
    # ajoute parfois malgré la consigne de ne pas en mettre.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_output, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
        verdict_obj = Verdict.model_validate(data)
    except Exception as e:
        print(f"Erreur de parsing du verdict JSON ({e}) — verdict INCERTAIN de secours envoyé.")
        print(f"Sortie brute du modèle : {raw_output[:500]}")
        verdict_obj = _fallback_verdict(lang)

    verdict_obj.langue = lang  # on force la langue détectée, au cas où le modèle l'omette
    return verdict_obj


VERDICT_EMOJIS = {"REEL": "✅", "FAUX": "❌", "INCERTAIN": "❓"}


def format_verdict_message(verdict: Verdict) -> str:
    """Met en forme un Verdict pour l'envoi WhatsApp (emoji + sources listées)."""
    emoji = VERDICT_EMOJIS.get(verdict.verdict, "")
    header = f"{emoji} {verdict.verdict} — confiance : {int(verdict.confidence * 100)}%"

    sources_label = "Sources" if verdict.langue == "fr" else "Sources"
    sources_text = (
        "\n".join(f"- {s}" for s in verdict.sources) if verdict.sources else ""
    )
    footer = f"\n\n{sources_label} :\n{sources_text}" if sources_text else ""

    return f"{header}\n\n{verdict.explication}{footer}"