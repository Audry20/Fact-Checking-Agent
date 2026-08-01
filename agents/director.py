import os
from typing import List, Literal

from pydantic import BaseModel
from crewai import Agent, Task, Crew, LLM

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

director_llm = LLM(model="groq/openai/gpt-oss-120b", api_key=GROQ_API_KEY, temperature=0)


class Verdict(BaseModel):
    verdict: Literal["REEL", "FAUX", "INCERTAIN"]
    confidence: float  # 0.0 à 1.0
    langue: Literal["fr", "en"]
    sources: List[str]
    explication: str


def render_verdict(claim: str, evidence: str, critique: str, lang: str) -> Verdict:
    """
    Agent directeur : synthétise l'affirmation, les preuves du chercheur
    et l'analyse du critique pour rendre un verdict final structuré
    (toujours dans le même format grâce à Pydantic), avec les sources
    citées et une explication rédigée pour l'utilisateur.
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
            "si tu as de très bonnes raisons de penser le contraire. "
            "Cite dans 'sources' les URLs les plus pertinentes trouvées par "
            "le chercheur."
        ),
        expected_output=(
            "Un verdict structuré : REEL, FAUX ou INCERTAIN, avec un score "
            "de confiance entre 0 et 1, les sources utilisées, et une "
            "explication claire pour l'utilisateur."
        ),
        agent=director,
        output_pydantic=Verdict,
    )

    crew = Crew(agents=[director], tasks=[task], verbose=False)
    result = crew.kickoff()

    verdict_obj = result.pydantic
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