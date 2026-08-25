import os
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Environment Variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secure_verify_token")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Groq Client Setup
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

@app.route('/', methods=['GET'])
def home():
    return "Instagram AI Bot is running!", 200

# Meta Webhook Verification
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED SUCCESSFULLY")
            return challenge, 200
        else:
            print("VERIFICATION_FAILED: Invalid token")
            return "Forbidden", 403
    return "Bad Request", 400

# Webhook Message Handler
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("--- INCOMING WEBHOOK PAYLOAD ---")
    print(data)

    try:
        if data.get("object") == "instagram" or data.get("object") == "page":
            for entry in data.get("entry", []):
                # Process Messaging Events
                messaging_events = entry.get("messaging", [])
                for event in messaging_events:
                    sender_id = event.get("sender", {}).get("id")
                    
                    # Ignore echoes/bot's own sent messages
                    if event.get("message") and not event.get("message", {}).get("is_echo"):
                        user_text = event.get("message", {}).get("text")
                        
                        if user_text and sender_id:
                            print(f"[+] Message received from {sender_id}: {user_text}")
                            
                            # 1. Generate Response via Groq AI
                            ai_reply = get_groq_response(user_text)
                            print(f"[+] AI Response Generated: {ai_reply}")
                            
                            # 2. Send Response Back to Instagram User
                            send_instagram_message(sender_id, ai_reply)

    except Exception as e:
        print(f"[-] ERROR IN WEBHOOK EXECUTION: {str(e)}")

    return "EVENT_RECEIVED", 200

def get_groq_response(user_message):
    """Groq API Call to Generate AI Reply"""
    if not groq_client:
        print("[-] GROQ_API_KEY missing in Environment Variables")
        return "Sorry, AI service is currently unconfigured."
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful, friendly Instagram AI assistant. Keep your responses short, natural, and friendly for chat."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[-] GROQ API ERROR: {str(e)}")
        return "Sorry, I couldn't process that right now."

def send_instagram_message(recipient_id, text_message):
    """Send Message back using Meta Graph API"""
    if not PAGE_ACCESS_TOKEN:
        print("[-] PAGE_ACCESS_TOKEN missing in Environment Variables")
        return

    url = f"https://graph.facebook.com/v19.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text_message}
    }

    try:
        response = requests.post(url, params=params, json=payload, headers=headers)
        print(f"[+] META API Response Code: {response.status_code}")
        print(f"[+] META API Response Body: {response.text}")
    except Exception as e:
        print(f"[-] META API REQUEST FAILED: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
