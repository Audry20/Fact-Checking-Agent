import time
import litellm


def run_crew_with_retry(crew, max_retries: int = 3, base_delay: float = 5.0):
    """
    Lance crew.kickoff() avec des nouvelles tentatives automatiques en cas
    de limite de débit (RateLimitError) atteinte sur Groq. Le tier gratuit
    de Groq a un quota de tokens/minute assez bas — un pipeline qui enchaîne
    plusieurs agents peut le dépasser ponctuellement, surtout en rafale de
    tests. On attend un peu plus longtemps à chaque nouvelle tentative
    (backoff progressif) avant de réessayer.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return crew.kickoff()
        except litellm.RateLimitError as e:
            last_error = e
            delay = base_delay * attempt
            print(
                f"Limite de débit Groq atteinte (tentative {attempt}/{max_retries}) — "
                f"nouvelle tentative dans {delay:.0f}s..."
            )
            if attempt < max_retries:
                time.sleep(delay)

    # Toutes les tentatives ont échoué : on relance la dernière erreur pour
    # que le try/except de app.py prenne le relais avec son message générique.
    raise last_error