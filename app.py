import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Choisis toi-même cette valeur (n'importe quelle chaîne secrète).
# Tu devras remettre EXACTEMENT la même valeur dans le champ
# "Vérifier le token" sur developers.facebook.com.
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
                # TODO: brancher ici le pipeline d'agents (filtre scope,
                # classificateur, extracteurs, chercheur, critique, directeur)

            elif message_type == "image":
                print(f"Image reçue de {from_number}")
                # TODO: brancher l'agent vision

            else:
                print(f"Type de message non géré pour le moment : {message_type}")

    except (KeyError, IndexError) as e:
        # Ce n'est pas un message entrant standard (ex: accusé de lecture) → on ignore
        print("Notification ignorée (pas un message entrant) :", e)

    return jsonify({"status": "reçu"}), 200


@app.route("/", methods=["GET"])
def health_check():
    """Simple route pour vérifier que le serveur est en ligne."""
    return "Tukutane Facts webhook actif", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

