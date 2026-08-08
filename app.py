# import os
# from flask import Flask, request, jsonify
# from dotenv import load_dotenv

# load_dotenv()

# # --- Correctif temporaire : bug connu CrewAI avec les fournisseurs
# # non-Anthropic (Groq inclus). CrewAI injecte un paramètre 'cache_breakpoint'
# # (pensé pour le cache de prompts Claude) qui fait planter Groq.
# # https://github.com/crewAIInc/crewAI/issues/5886
# import crewai.llms.cache as _crewai_cache
# _crewai_cache.mark_cache_breakpoint = lambda msg: msg
# # --- Fin du correctif ---

# from utils.lang_detect import detect_language
# from utils.whatsapp_sender import send_whatsapp_message
# from agents.scope_filter import is_in_scope, get_refusal_message
# from agents.classifier import classify_content_type, extract_url
# from agents.extractors import extract_from_text, extract_from_link, extract_from_image
# from agents.researcher import research_claim
# from agents.critic import critique_evidence
# from agents.director import render_verdict, format_verdict_message
# from cache.firestore_cache import get_cached_verdict, set_cached_verdict

# app = Flask(__name__)

# # Choisis toi-même cette valeur (n'importe quelle chaîne secrète).
# # Elle doit être IDENTIQUE au champ "Vérifier le token" sur developers.facebook.com.
# VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "tukutane_secret_2026")


# @app.route("/webhook", methods=["GET"])
# def verify_webhook():
#     """Meta appelle cette route une seule fois, quand tu cliques sur
#     'Vérifier et enregistrer', pour confirmer que le serveur t'appartient."""
#     mode = request.args.get("hub.mode")
#     token = request.args.get("hub.verify_token")
#     challenge = request.args.get("hub.challenge")

#     if mode == "subscribe" and token == VERIFY_TOKEN:
#         print("Webhook vérifié avec succès.")
#         return challenge, 200
#     else:
#         print("Échec de la vérification du webhook (token incorrect).")
#         return "Erreur de vérification", 403


# @app.route("/webhook", methods=["POST"])
# def receive_message():
#     """Meta appelle cette route à chaque message WhatsApp reçu."""
#     data = request.get_json()
#     print("Payload brut reçu :", data)

#     try:
#         entry = data["entry"][0]
#         changes = entry["changes"][0]
#         value = changes["value"]

#         if "messages" in value:
#             message = value["messages"][0]
#             from_number = message["from"]
#             message_type = message["type"]

#             if message_type == "text":
#                 text_body = message["text"]["body"]
#                 print(f"Texte reçu de {from_number} : {text_body}")
#                 handle_text_message(from_number, text_body)

#             elif message_type == "image":
#                 print(f"Image reçue de {from_number}")
#                 # L'agent vision (extract_from_image) existe déjà, mais nécessite
#                 # un utilitaire de récupération de média WhatsApp authentifié
#                 # (Graph API /media/{media-id}) avant de pouvoir être branché ici.
#                 # TODO: prochaine étape.
#                 send_whatsapp_message(
#                     from_number,
#                     "Le traitement des images arrive bientôt — pour l'instant, "
#                     "envoie-moi ton affirmation en texte.",
#                 )

#             else:
#                 print(f"Type de message non géré pour le moment : {message_type}")

#     except (KeyError, IndexError) as e:
#         # Ce n'est pas un message entrant standard (ex: accusé de lecture) → on ignore
#         print("Notification ignorée (pas un message entrant) :", e)

#     return jsonify({"status": "reçu"}), 200


# def handle_text_message(from_number: str, text_body: str) -> None:
#     """
#     Pipeline complet :
#     1. Détection de langue
#     2. Filtre de scope -> refus immédiat si hors-scope
#     3. Classification + extraction (texte ou lien)
#     4. Cache Firestore -> réponse immédiate si déjà vérifié récemment
#     5. Chercheur (Tavily) -> Critique -> Directeur -> Verdict structuré
#     6. Mise en cache + envoi de la réponse
#     """
#     lang = detect_language(text_body)
#     print(f"Langue détectée : {lang}")

#     if not is_in_scope(text_body):
#         print(f"Message hors-scope détecté, envoi du refus en {lang}.")
#         send_whatsapp_message(from_number, get_refusal_message(lang))
#         return

#     # Extraction de l'affirmation vérifiable
#     content_type = classify_content_type("text", text_body)
#     if content_type == "lien":
#         url = extract_url(text_body)
#         print(f"Lien détecté : {url}")
#         claim = extract_from_link(url)
#     else:
#         print("Texte brut détecté.")
#         claim = extract_from_text(text_body)

#     print(f"Affirmation isolée : {claim}")

#     # Cache : évite de refaire tout le pipeline pour une affirmation
#     # déjà vérifiée récemment (même langue).
#     try:
#         cached = get_cached_verdict(claim, lang)
#     except Exception as e:
#         print(f"Erreur de lecture du cache (on continue sans cache) : {e}")
#         cached = None

#     if cached:
#         print("Verdict trouvé en cache, envoi immédiat.")
#         send_whatsapp_message(from_number, cached.get("message", ""))
#         return

#     # Pipeline complet : chercheur -> critique -> directeur
#     try:
#         evidence = research_claim(claim)
#         print(f"Preuves collectées : {evidence[:200]}...")

#         critique = critique_evidence(claim, evidence)
#         print(f"Analyse critique : {critique[:200]}...")

#         verdict = render_verdict(claim, evidence, critique, lang)
#         message = format_verdict_message(verdict)

#         send_whatsapp_message(from_number, message)

#         # Mise en cache pour les prochaines fois
#         try:
#             set_cached_verdict(claim, lang, {**verdict.model_dump(), "message": message})
#         except Exception as e:
#             print(f"Erreur d'écriture du cache (non bloquant) : {e}")

#     except Exception as e:
#         print(f"Erreur dans le pipeline de vérification : {e}")
#         error_message = (
#             "Désolé, une erreur est survenue pendant la vérification. "
#             "Réessaie dans quelques instants."
#             if lang == "fr"
#             else "Sorry, an error occurred during verification. Please try again shortly."
#         )
#         send_whatsapp_message(from_number, error_message)


# @app.route("/", methods=["GET"])
# def health_check():
#     """Simple route pour vérifier que le serveur est en ligne."""
#     return "Tukutane Facts webhook actif", 200


# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)

import os
from dotenv import load_dotenv

# Charge le fichier .env AVANT les imports des agents, car ceux-ci lisent
# les clés API dès leur import (ex: GROQ_API_KEY = os.environ.get(...)).
# En production sur Render, cette ligne ne fait rien de mal : les variables
# d'environnement sont déjà injectées directement par Render.
load_dotenv()

# --- Correctif temporaire : bug connu CrewAI 1.14.4 avec les fournisseurs
# non-Anthropic (Groq inclus). CrewAI injecte un paramètre 'cache_breakpoint'
# (pensé pour le cache de prompts Claude) qui fait planter Groq, qui ne le
# comprend pas. Contournement officiel en attendant le correctif upstream :
# https://github.com/crewAIInc/crewAI/issues/5886
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg
# --- Fin du correctif ---

from flask import Flask, request, jsonify

from utils.lang_detect import detect_language
from utils.whatsapp_sender import send_whatsapp_message
from agents.scope_filter import is_in_scope, get_refusal_message
from agents.classifier import classify_content_type, extract_url
from agents.extractors import extract_from_text, extract_from_link, extract_from_image
from agents.researcher import research_claim
from agents.critic import critique_evidence
from agents.director import render_verdict, format_verdict_message
from cache.memory_cache import get_cached_verdict, set_cached_verdict

app = Flask(__name__)

# Choisis toi-même cette valeur (n'importe quelle chaîne secrète).
# Elle doit être IDENTIQUE au champ "Vérifier le token" sur developers.facebook.com.
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "tukutane_secret_2026")


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta appelle cette route une seule fois, quand tu cliques sur
    'Vérifier et enregistrer', pour confirmer que le serveur t'appartient."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook vérifié avec succès.")
        return challenge, 200
    else:
        print("Échec de la vérification du webhook (token incorrect).")
        return "Erreur de vérification", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Meta appelle cette route à chaque message WhatsApp reçu."""
    data = request.get_json()
    print("Payload brut reçu :", data)

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            message_type = message["type"]

            if message_type == "text":
                text_body = message["text"]["body"]
                print(f"Texte reçu de {from_number} : {text_body}")
                handle_text_message(from_number, text_body)

            elif message_type == "image":
                print(f"Image reçue de {from_number}")
                # L'agent vision (extract_from_image) existe déjà, mais nécessite
                # un utilitaire de récupération de média WhatsApp authentifié
                # (Graph API /media/{media-id}) avant de pouvoir être branché ici.
                # TODO: prochaine étape.
                send_whatsapp_message(
                    from_number,
                    "Le traitement des images arrive bientôt — pour l'instant, "
                    "envoie-moi ton affirmation en texte.",
                )

            else:
                print(f"Type de message non géré pour le moment : {message_type}")

    except (KeyError, IndexError) as e:
        # Ce n'est pas un message entrant standard (ex: accusé de lecture) → on ignore
        print("Notification ignorée (pas un message entrant) :", e)

    return jsonify({"status": "reçu"}), 200


def handle_text_message(from_number: str, text_body: str) -> None:
    """
    Pipeline complet :
    1. Détection de langue
    2. Filtre de scope -> refus immédiat si hors-scope
    3. Classification + extraction (texte ou lien)
    4. Cache Firestore -> réponse immédiate si déjà vérifié récemment
    5. Chercheur (Tavily) -> Critique -> Directeur -> Verdict structuré
    6. Mise en cache + envoi de la réponse
    """
    lang = detect_language(text_body)
    print(f"Langue détectée : {lang}")

    if not is_in_scope(text_body):
        print(f"Message hors-scope détecté, envoi du refus en {lang}.")
        send_whatsapp_message(from_number, get_refusal_message(lang))
        return

    # Extraction de l'affirmation vérifiable
    try:
        content_type = classify_content_type("text", text_body)
        if content_type == "lien":
            url = extract_url(text_body)
            print(f"Lien détecté : {url}")
            claim = extract_from_link(url)
        else:
            print("Texte brut détecté.")
            claim = extract_from_text(text_body)
    except Exception as e:
        print(f"Erreur pendant l'extraction (souvent un problème réseau passager) : {e}")
        error_message = (
            "Désolé, une erreur est survenue pendant l'analyse de ton message. "
            "Réessaie dans quelques instants."
            if lang == "fr"
            else "Sorry, an error occurred while analyzing your message. "
            "Please try again shortly."
        )
        send_whatsapp_message(from_number, error_message)
        return

    print(f"Affirmation isolée : {claim}")

    # Cache : évite de refaire tout le pipeline pour une affirmation
    # déjà vérifiée récemment (même langue).
    try:
        cached = get_cached_verdict(claim, lang)
    except Exception as e:
        print(f"Erreur de lecture du cache (on continue sans cache) : {e}")
        cached = None

    if cached:
        print("Verdict trouvé en cache, envoi immédiat.")
        send_whatsapp_message(from_number, cached.get("message", ""))
        return

    # Pipeline complet : chercheur -> critique -> directeur
    try:
        evidence = research_claim(claim)
        print(f"Preuves collectées : {evidence[:200]}...")

        critique = critique_evidence(claim, evidence)
        print(f"Analyse critique : {critique[:200]}...")

        verdict = render_verdict(claim, evidence, critique, lang)
        message = format_verdict_message(verdict)

        send_whatsapp_message(from_number, message)

        # Mise en cache pour les prochaines fois
        try:
            set_cached_verdict(claim, lang, {**verdict.model_dump(), "message": message})
        except Exception as e:
            print(f"Erreur d'écriture du cache (non bloquant) : {e}")

    except Exception as e:
        print(f"Erreur dans le pipeline de vérification : {e}")
        error_message = (
            "Désolé, une erreur est survenue pendant la vérification. "
            "Réessaie dans quelques instants."
            if lang == "fr"
            else "Sorry, an error occurred during verification. Please try again shortly."
        )
        send_whatsapp_message(from_number, error_message)


@app.route("/", methods=["GET"])
def health_check():
    """Simple route pour vérifier que le serveur est en ligne."""
    return "Tukutane Facts webhook actif", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)