import os
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Environment Variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secure_verify_token")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

INSTAGRAM_ACCOUNT_ID = "17841415584226490"

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

@app.route('/', methods=['GET'])
def home():
    return "Instagram AI Bot is running!", 200

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

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    print(f"=== INCOMING PAYLOAD: {data} ===", flush=True)

    try:
        # Extract entries from root payload
        entries = data.get("entry", [])
        if not entries and isinstance(data, list):
            entries = data

        for entry in entries:
            # 1. Check direct 'messaging' list
            events = entry.get("messaging", [])
            
            # 2. Check 'changes' format (Alternative Meta Payload)
            if not events and "changes" in entry:
                for change in entry.get("changes", []):
                    val = change.get("value", {})
                    if "messages" in val:
                        events.extend(val.get("messages", []))
                    elif "text" in val or "message" in val:
                        events.append(val)

            # 3. Process events
            for event in events:
                sender_id = None
                user_text = None

                # Extract sender ID
                if "sender" in event and "id" in event["sender"]:
                    sender_id = event["sender"]["id"]
                elif "from" in event and "id" in event["from"]:
                    sender_id = event["from"]["id"]
                elif "from" in event and isinstance(event["from"], str):
                    sender_id = event["from"]

                # Extract text message
                if "message" in event:
                    msg = event["message"]
                    if isinstance(msg, dict):
                        user_text = msg.get("text")
                        if msg.get("is_echo"):
                            print("[!] Echo message ignored", flush=True)
                            continue
                    elif isinstance(msg, str):
                        user_text = msg
                elif "text" in event:
                    user_text = event.get("text")

                print(f"[DEBUG] Extracted -> Sender: {sender_id} | Text: {user_text}", flush=True)

                if sender_id and user_text:
                    print(f"[+] Processing message from {sender_id}: {user_text}", flush=True)
                    ai_reply = get_groq_response(user_text)
                    send_instagram_message(sender_id, ai_reply)

    except Exception as e:
        print(f"[-] ERROR IN WEBHOOK EXECUTION: {str(e)}", flush=True)

    return "EVENT_RECEIVED", 200

def get_groq_response(user_message):
    if not groq_client:
        print("[-] GROQ_API_KEY missing", flush=True)
        return "AI service unconfigured."
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a concise Instagram bot assistant."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[-] GROQ ERROR: {str(e)}", flush=True)
        return "Error generating response."

def send_instagram_message(recipient_id, text_message):
    if not PAGE_ACCESS_TOKEN:
        print("[-] PAGE_ACCESS_TOKEN missing", flush=True)
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
        res = requests.post(url, params=params, json=payload, headers=headers)
        print(f"[+] META GRAPH API HTTP STATUS: {res.status_code}", flush=True)
        print(f"[+] META GRAPH API RESPONSE: {res.text}", flush=True)
    except Exception as e:
        print(f"[-] META REQUEST EXCEPTION: {str(e)}", flush=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
