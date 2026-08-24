import os
import sys
import json
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Environment Variables
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "mysecrettoken")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq Client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

@app.route("/", methods=["GET"])
def home():
    return "Instagram AI Bot is Running!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED Successfully!", flush=True)
        return challenge, 200
    else:
        print("Webhook Verification Failed!", flush=True)
        return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Received Webhook Payload:", json.dumps(data), flush=True)

    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message = messaging_event.get("message", {})
                
                # Echo messages ignore karein
                if message.get("is_echo"):
                    continue

                message_text = message.get("text")
                if sender_id and message_text:
                    print(f"Message from {sender_id}: {message_text}", flush=True)
                    reply_text = get_ai_response(message_text)
                    send_instagram_message(sender_id, reply_text)

    return "EVENT_RECEIVED", 200

def get_ai_response(user_message):
    if not groq_client:
        print("ERROR: GROQ_API_KEY is missing in Environment Variables!", flush=True)
        return "Sorry, AI service is currently unconfigured."

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful and friendly Instagram AI assistant. Keep your responses short and engaging."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=150
        )
        ai_reply = response.choices[0].message.content
        print(f"Groq AI Reply: {ai_reply}", flush=True)
        return ai_reply
    except Exception as e:
        print(f"ERROR generating AI response: {str(e)}", flush=True)
        return "Sorry, I am having trouble responding right now."

def send_instagram_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        print("ERROR: PAGE_ACCESS_TOKEN is missing in Environment Variables!", flush=True)
        return

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    headers = {"Content-Type": "application/json"}

    print(f"Sending message to {recipient_id}...", flush=True)
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Meta API Status Code: {response.status_code}", flush=True)
        print(f"Meta API Response: {response.text}", flush=True)
    except Exception as e:
        print(f"ERROR sending message via Meta API: {str(e)}", flush=True)

if __name__ == "__main__":
    app.run(port=5000)
