import os
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Environment Variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secure_verify_token")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Instagram Business Account ID
INSTAGRAM_ACCOUNT_ID = "17841415584226490"

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
            print("WEBHOOK_VERIFIED SUCCESSFULLY", flush=True)
            return challenge, 200
        else:
            print("VERIFICATION_FAILED: Invalid token", flush=True)
            return "Forbidden", 403
    return "Bad Request", 400

# Webhook Message Handler
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("--- INCOMING WEBHOOK PAYLOAD ---", flush=True)
    print(data, flush=True)

    if not data:
        return "NO_DATA", 200

    try:
        for entry in data.get("entry", []):
            # Standard Instagram Messaging Format
            messaging_events = entry.get("messaging", [])
            
            # Alternative Changes Format (Meta Webhook Test)
            if not messaging_events and "changes" in entry:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        messaging_events = value.get("messages", [])

            for event in messaging_events:
                sender_id = event.get("sender", {}).get("id") or event.get("from", {}).get("id")
                
                message_obj = event.get("message", {})
                user_text = message_obj.get("text")
                is_echo = message_obj.get("is_echo", False)

                if user_text and sender_id and not is_echo:
                    print(f"[+] Processing message from {sender_id}: {user_text}", flush=True)
                    
                    # 1. Generate AI Reply via Groq
                    ai_reply = get_groq_response(user_text)
                    print(f"[+] AI Response: {ai_reply}", flush=True)
                    
                    # 2. Send Message Back to Instagram User
                    send_instagram_message(sender_id, ai_reply)

    except Exception as e:
        print(f"[-] ERROR IN WEBHOOK EXECUTION: {str(e)}", flush=True)

    return "EVENT_RECEIVED", 200

def get_groq_response(user_message):
    """Groq API Call to Generate AI Reply"""
    if not groq_client:
        print("[-] GROQ_API_KEY missing in Environment Variables", flush=True)
        return "Sorry, AI service is currently unconfigured."
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful, friendly Instagram AI assistant. Keep responses short and simple for chat."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[-] GROQ API ERROR: {str(e)}", flush=True)
        return "Sorry, I couldn't process that right now."

def send_instagram_message(recipient_id, text_message):
    """Send Message back using Meta Graph API v20.0"""
    if not PAGE_ACCESS_TOKEN:
        print("[-] PAGE_ACCESS_TOKEN missing in Environment Variables", flush=True)
        return

    url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ACCOUNT_ID}/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text_message},
        "messaging_type": "RESPONSE"
    }

    try:
        response = requests.post(url, params=params, json=payload, headers=headers)
        print(f"[+] META API Status Code: {response.status_code}", flush=True)
        print(f"[+] META API Response: {response.text}", flush=True)
    except Exception as e:
        print(f"[-] META API REQUEST FAILED: {str(e)}", flush=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
