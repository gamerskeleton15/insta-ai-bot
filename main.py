import os
import requests
from flask import Flask, request, jsonify
from anthropic import Anthropic

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secret_token_123")
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

anthropic_client = Anthropic(api_key=CLAUDE_API_KEY)

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def handle_messages():
    data = request.get_json()
    try:
        for entry in data.get('entry', []):
            for messaging_event in entry.get('messaging', []):
                sender_id = messaging_event['sender']['id']
                if 'message' in messaging_event and 'text' in messaging_event['message']:
                    user_text = messaging_event['message']['text']
                    
                    response = anthropic_client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=300,
                        messages=[{"role": "user", "content": user_text}]
                    )
                    ai_reply = response.content[0].text
                    send_instagram_dm(sender_id, ai_reply)
    except Exception as e:
        print("Error:", e)
    return 'EVENT_RECEIVED', 200

def send_instagram_dm(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
