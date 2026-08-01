import os
import requests

WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

GRAPH_API_VERSION = "v21.0"


def send_whatsapp_message(to: str, message: str) -> bool:
    """
    Envoie un message texte à un numéro WhatsApp via l'API Cloud de Meta.
    'to' doit être au format international sans le '+' (ex: 25761998xxxx).
    Retourne True si l'envoi a réussi, False sinon.
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("WHATSAPP_ACCESS_TOKEN ou WHATSAPP_PHONE_NUMBER_ID manquant dans l'environnement.")
        return False

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Échec de l'envoi WhatsApp ({response.status_code}) : {response.text}")
            return False
    except requests.RequestException as e:
        print(f"Erreur réseau lors de l'envoi WhatsApp : {e}")
        return False

