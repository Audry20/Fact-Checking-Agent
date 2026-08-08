# import os
# from crewai import Agent, Task, Crew, LLM

# GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# critic_llm = LLM(model="groq/openai/gpt-oss-120b", api_key=GROQ_API_KEY, temperature=0)


# def critique_evidence(claim: str, evidence: str) -> str:
#     """
#     Agent critique : relit les preuves collectées par le chercheur et
#     vérifie qu'elles soutiennent réellement une conclusion, qu'il n'y a
#     pas de contradiction entre les sources, et que les sources citées
#     sont crédibles.

#     Ce pattern de "self-critique" (relecture par un agent séparé avant
#     la synthèse finale) est ce qui réduit le plus le risque d'halluciner
#     un verdict basé sur une preuve insuffisante ou douteuse.
#     """
#     critic = Agent(
#         role="Critique des preuves",
#         goal=(
#             "Vérifier la cohérence et la fiabilité des preuves avant "
#             "qu'un verdict ne soit rendu"
#         ),
#         backstory=(
#             "Tu es un rédacteur en chef exigeant, connu pour repérer les "
#             "faiblesses dans les preuves avant publication. Tu vérifies "
#             "systématiquement : est-ce que les preuves soutiennent vraiment "
#             "la conclusion qu'on veut en tirer ? Y a-t-il des contradictions "
#             "entre les sources ? Les sources sont-elles crédibles et "
#             "récentes ? Tu es sévère et n'hésites pas à signaler une "
#             "insuffisance de preuves plutôt que de laisser passer un "
#             "verdict mal fondé."
#         ),
#         llm=critic_llm,
#         verbose=False,
#     )

#     task = Task(
#         description=(
#             f'Affirmation à vérifier : "{claim}"\n\n'
#             f"Preuves collectées par le chercheur :\n{evidence}\n\n"
#             "Analyse ces preuves de façon critique :\n"
#             "1. Les preuves sont-elles suffisantes pour trancher "
#             "(vrai/faux/incertain) ?\n"
#             "2. Y a-t-il des contradictions entre les sources ?\n"
#             "3. Les sources semblent-elles crédibles ?\n\n"
#             "Termine ta réponse par une recommandation claire : "
#             "'PREUVES SUFFISANTES' ou 'PREUVES INSUFFISANTES', suivie "
#             "d'une brève justification."
#         ),
#         expected_output=(
#             "Une analyse critique des preuves, se terminant par "
#             "'PREUVES SUFFISANTES' ou 'PREUVES INSUFFISANTES' et une "
#             "justification."
#         ),
#         agent=critic,
#     )

#     crew = Crew(agents=[critic], tasks=[task], verbose=False)
#     result = crew.kickoff()
#     return str(result).strip()

import os
from crewai import Agent, Task, Crew, LLM

from utils.retry import run_crew_with_retry

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# gpt-oss-20b : la relecture critique n'a pas besoin du modèle 120b,
# et ça répartit la charge sur un quota tokens/minute séparé.
critic_llm = LLM(model="groq/openai/gpt-oss-20b", api_key=GROQ_API_KEY, temperature=0)


def critique_evidence(claim: str, evidence: str) -> str:
    """
    Agent critique : relit les preuves collectées par le chercheur et
    vérifie qu'elles soutiennent réellement une conclusion, qu'il n'y a
    pas de contradiction entre les sources, et que les sources citées
    sont crédibles.

    Ce pattern de "self-critique" (relecture par un agent séparé avant
    la synthèse finale) est ce qui réduit le plus le risque d'halluciner
    un verdict basé sur une preuve insuffisante ou douteuse.
    """
    critic = Agent(
        role="Critique des preuves",
        goal=(
            "Vérifier la cohérence et la fiabilité des preuves avant "
            "qu'un verdict ne soit rendu"
        ),
        backstory=(
            "Tu es un rédacteur en chef exigeant, connu pour repérer les "
            "faiblesses dans les preuves avant publication. Tu vérifies "
            "systématiquement : est-ce que les preuves soutiennent vraiment "
            "la conclusion qu'on veut en tirer ? Y a-t-il des contradictions "
            "entre les sources ? Les sources sont-elles crédibles et "
            "récentes ? Tu es sévère et n'hésites pas à signaler une "
            "insuffisance de preuves plutôt que de laisser passer un "
            "verdict mal fondé."
        ),
        llm=critic_llm,
        verbose=False,
    )

    task = Task(
        description=(
            f'Affirmation à vérifier : "{claim}"\n\n'
            f"Preuves collectées par le chercheur :\n{evidence}\n\n"
            "Analyse ces preuves de façon critique :\n"
            "1. Les preuves sont-elles suffisantes pour trancher "
            "(vrai/faux/incertain) ?\n"
            "2. Y a-t-il des contradictions entre les sources ?\n"
            "3. Les sources semblent-elles crédibles ?\n\n"
            "Termine ta réponse par une recommandation claire : "
            "'PREUVES SUFFISANTES' ou 'PREUVES INSUFFISANTES', suivie "
            "d'une brève justification."
        ),
        expected_output=(
            "Une analyse critique des preuves, se terminant par "
            "'PREUVES SUFFISANTES' ou 'PREUVES INSUFFISANTES' et une "
            "justification."
        ),
        agent=critic,
    )

    crew = Crew(agents=[critic], tasks=[task], verbose=False)
    result = run_crew_with_retry(crew)
    return str(result).strip()