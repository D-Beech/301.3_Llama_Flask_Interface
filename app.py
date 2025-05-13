from flask import Flask, render_template, request, jsonify, Response
import requests
import json
import docx
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Settings
LLAMA_SERVER_URL = "http://localhost:11434/api/chat"
SYSTEM_PROMPT = (
    "You are an educational chatbot called Juan, respond using a chill tone. "
    "Respond using simple vocabulary. Do not talk about Pokemon. Give very concise responses only."
)
token_lengths = [32, 256, 512]
vocab_levels = ['very simple, child level', '15 year old level', 'university level']
tones = ['friendly', 'extremely aggressive', 'formal']


# System prompt builder

def build_system_prompt(token_level=0, vocab_level=0, tone_level=0, display_name='unknown'):
    return (
        f"You are an educational chatbot called Juan, respond using a {tones[tone_level]} tone. "
        f"Respond using {vocab_levels[vocab_level]} vocabulary. Do not talk about Pokemon. "
        f"Give very concise responses only. The name of the user is {display_name}."
    )


# Stream chat endpoint
@app.route('/stream_chat', methods=['POST'])
def stream_chat():
    user_msg = request.json.get("message", "")

    def generate():
        with requests.post(
            LLAMA_SERVER_URL,
            json={
                "model": "llama3.2",
                "messages": [{"role": "user", "content": user_msg}],
                "stream": True
            },
            stream=True
        ) as r:
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content

    return Response(generate(), content_type='text/plain')


# Basic message endpoint (non-streaming)
@app.route("/message", methods=['POST'])
def message():
    user_message = request.json.get("message")
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": user_message}],
        "stream": False
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        reply = data.get("message", {}).get("content", "No response from model.")
        return jsonify({"message": reply}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


# Debugging/test endpoint
@app.route("/test", methods=['POST'])
def test():
    name = request.json.get('displayName')
    tone = request.json.get('tone')
    prompt = build_system_prompt(display_name=name, tone_level=int(tone))
    return jsonify({"system_prompt": prompt})


# Safe chat with optional context
@app.route("/safe_chat", methods=["POST"])
def safe_chat():
    user_message = request.json.get("message", "")
    context = request.json.get("context", [])

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    context.append({"role": "user", "content": user_message})
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + context,
        "stream": False,
        "temperature": 0.0,
        "top_p": 1.0,
        "num_predict": token_lengths[0],
        "stop": ["</s>"]
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        reply = data.get("message", {}).get("content", "No response from model.")
        return jsonify({"response": reply}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def home():
    return render_template('index.html')


# Extract text from docx file

def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def extract_text_from_docx_limited(docx_file, max_words=1000):
    doc = docx.Document(docx_file)
    words = []
    for paragraph in doc.paragraphs:
        p_words = paragraph.text.split()
        if len(words) + len(p_words) > max_words:
            words.extend(p_words[:max_words - len(words)])
            break
        words.extend(p_words)
    return ' '.join(words)


@app.route('/fileTest', methods=['GET'])
def file_test():
    with open('CS301.2_IDD_Datu_Beech_Submission.docx', 'rb') as file:
        text = extract_text_from_docx(file)
    message = f"please summarize the following: {text}"

    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}],
        "stream": False,
        "temperature": 0.0,
        "top_p": 1.0,
        "num_predict": token_lengths[0],
        "stop": ["</s>"]
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        reply = data.get("message", {}).get("content", "No response from model.")
        return jsonify({"response": reply}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5001, debug=True)
