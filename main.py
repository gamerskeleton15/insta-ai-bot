import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment Variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secure_verify_token")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

INSTAGRAM_ACCOUNT_ID = "17841415584226490"

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
        entries = data.get("entry", [])
        if not entries and isinstance(data, list):
            entries = data

        for entry in entries:
            events = entry.get("messaging", [])
            
            if not events and "changes" in entry:
                for change in entry.get("changes", []):
                    val = change.get("value", {})
                    if "messages" in val:
                        events.extend(val.get("messages", []))
                    elif "text" in val or "message" in val:
                        events.append(val)

            for event in events:
                sender_id = None
                user_text = None

                if "sender" in event and "id" in event["sender"]:
                    sender_id = event["sender"]["id"]
                elif "from" in event and "id" in event["from"]:
                    sender_id = event["from"]["id"]

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

                if sender_id and user_text:
                    print(f"[+] Processing message from {sender_id}: {user_text}", flush=True)
                    ai_reply = get_gemini_response(user_text)
                    send_instagram_message(sender_id, ai_reply)

    except Exception as e:
        print(f"[-] ERROR IN WEBHOOK EXECUTION: {str(e)}", flush=True)

    return "EVENT_RECEIVED", 200

def get_gemini_response(user_message):
    if not GEMINI_API_KEY:
        print("[-] GEMINI_API_KEY missing", flush=True)
        return "AI service unconfigured."
    
    clean_key = GEMINI_API_KEY.strip().replace('"', '').replace("'", "")
    
    # Updated to stable v1 endpoint with gemini-1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={clean_key}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"You are a helpful and concise Instagram chat assistant. Reply briefly to: {user_message}"
            }]
        }]
    }

    try:
        res = requests.post(url, json=payload, headers=headers)
        res_data = res.json()
        
        if res.status_code == 200:
            return res_data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"[-] GEMINI REST ERROR: {res.status_code} - {res.text}", flush=True)
            
            # Fallback to gemini-1.5-flash-latest on v1beta
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={clean_key}"
            fb_res = requests.post(fallback_url, json=payload, headers=headers)
            if fb_res.status_code == 200:
                return fb_res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                
            return "Sorry, I couldn't process that right now."
    except Exception as e:
        print(f"[-] GEMINI EXCEPTION: {str(e)}", flush=True)
        return "Error generating response."

def send_instagram_message(recipient_id, text_message):
    if not PAGE_ACCESS_TOKEN:
        print("[-] PAGE_ACCESS_TOKEN missing", flush=True)
        return

    clean_token = str(PAGE_ACCESS_TOKEN).strip().replace('"', '').replace("'", "")

    url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ACCOUNT_ID}/messages"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {clean_token}"
    }
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text_message},
        "messaging_type": "RESPONSE"
    }

    try:
        res = requests.post(url, json=payload, headers=headers)
        print(f"[+] META GRAPH API HTTP STATUS: {res.status_code}", flush=True)
        print(f"[+] META GRAPH API RESPONSE: {res.text}", flush=True)
    except Exception as e:
        print(f"[-] META REQUEST EXCEPTION: {str(e)}", flush=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
