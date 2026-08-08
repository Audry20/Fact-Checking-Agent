# 

import os
from tavily import TavilyClient

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

from trusted_domains import TRUSTED_DOMAINS
from utils.retry import run_crew_with_retry

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# Modèle dédié au chercheur : Llama 4 Scout, non-raisonneur, sur un quota
# tokens/minute totalement séparé des modèles gpt-oss (partagés par
# l'extracteur et le critique). Déjà utilisé et éprouvé pour la vision.
research_llm = LLM(
    model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=GROQ_API_KEY,
    temperature=0.3,
)

tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# Combine tous les domaines de confiance en une seule liste, toutes
# catégories confondues (le scope est déjà garanti par le filtre de
# scope en amont, pas besoin de re-catégoriser ici).
ALL_TRUSTED_DOMAINS = list({d for domains in TRUSTED_DOMAINS.values() for d in domains})


@tool("Recherche web Tavily")
def tavily_search(query: str) -> str:
    """
    Recherche une requête sur le web via Tavily. Retourne les résultats
    formatés (titre, extrait, URL).

    Note : on ne restreint plus aux seuls domaines de confiance
    (include_domains) — ça excluait parfois des couvertures locales ou
    officielles pertinentes (ex: annonces gouvernementales, presse
    régionale non listée), menant à trop de verdicts INCERTAIN par manque
    de résultats. La liste ALL_TRUSTED_DOMAINS sert maintenant de guide
    dans le prompt de l'agent (préférence, pas filtre strict) plutôt que
    de restriction technique côté API.
    """
    if tavily_client is None:
        return "Erreur : TAVILY_API_KEY non configurée."

    try:
        results = tavily_client.search(
            query=query,
            topic="general",
            max_results=8,
        )
    except Exception as e:
        return f"Erreur lors de la recherche Tavily : {e}"

    if not results.get("results"):
        return "Aucun résultat trouvé pour cette requête."

    formatted = []
    for r in results["results"]:
        excerpt = (r.get("content") or "")[:300]
        formatted.append(f"- {r['title']} ({r['url']})\n  {excerpt}")

    return "\n\n".join(formatted)


def research_claim(claim: str) -> str:
    """
    Agent chercheur : génère plusieurs requêtes de recherche différentes
    pour la même affirmation, croise les résultats via Tavily, et
    retourne une synthèse des preuves trouvées avec leurs sources.
    """
    researcher = Agent(
        role="Chercheur web spécialisé en vérification de faits",
        goal=(
            "Trouver des preuves fiables, sourcées et récentes pour "
            "confirmer ou infirmer une affirmation"
        ),
        backstory=(
            "Tu es un chercheur méticuleux qui croise systématiquement "
            "plusieurs sources avant de conclure quoi que ce soit. Tu "
            "formules plusieurs requêtes de recherche différentes pour une "
            "même affirmation, afin de ne pas te fier à un seul angle ou "
            "une seule source. Quand plusieurs résultats se valent, tu "
            "privilégies les sources comme les organisations officielles "
            "(ONU, FMI, Banque mondiale, gouvernements), les grandes agences "
            "de presse (Reuters, AFP, AP), et la presse régionale reconnue "
            "(Jeune Afrique, The East African) — sans pour autant ignorer "
            "d'autres sources pertinentes si elles apportent une preuve "
            "utile qu'aucune des sources ci-dessus ne couvre."
        ),
        llm=research_llm,
        tools=[tavily_search],
        max_iter=4,  # filet de sécurité : 2 recherches + synthèse, avec une marge
        verbose=False,
    )

    task = Task(
        description=(
            f'Affirmation à vérifier : "{claim}"\n\n'
            "Effectue EXACTEMENT 2 recherches web (pas plus, pas moins), avec "
            "deux formulations différentes de cette affirmation, pour croiser "
            "les résultats. Résume ensuite les preuves trouvées : ce que "
            "disent les sources fiables, avec leurs URLs exactes. Sois "
            "factuel, ne conclus pas encore sur la véracité — contente-toi "
            "de rapporter les preuves."
        ),
        expected_output=(
            "Une synthèse des preuves trouvées, avec les URLs des sources utilisées."
        ),
        agent=researcher,
    )

    crew = Crew(agents=[researcher], tasks=[task], verbose=False)
    result = run_crew_with_retry(crew)
    return str(result).strip()