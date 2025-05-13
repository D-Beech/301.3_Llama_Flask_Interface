from flask import Flask, render_template, request, jsonify, Response
import requests
import json
import docx
from flask_cors import CORS

#These are simpler than serilizaers i reckon
from dataclasses import dataclass, field
from typing import List

@dataclass
class ContextItem:
    role: str  # "user" or "assistant"
    content: str

@dataclass
class ChatPayload:
    message: str = ''
    context: List[ContextItem] = field(default_factory=list)
    displayName: str = "unknown"
    token_length: int = 0
    vocab_complexity: int = 0
    tone: int = 0



app = Flask(__name__)
CORS(app)

# Settings
LLAMA_SERVER_URL = "http://localhost:11434/api/chat"
SYSTEM_PROMPT = (
    "You are an educational chatbot called Juan, respond using a chill tone. "
    "Respond using simple vocabulary. Do not talk about Pokemon. Give very concise responses only."
)



# System prompt builder

def build_system_prompt(token_length=0, vocab_level=0, tone_level=0, display_name='unknown'):
    token_lengths = ['consise', 'medium length', 'thought out, long if needed']
    vocab_levels = ['very simple, child level', '15 year old level', 'university level']
    tones = ['friendly', 'extremely aggressive', 'formal']

    return (
        f"You are an educational chatbot called Juan, respond using a {tones[tone_level]} tone. "
        f"Respond using {vocab_levels[vocab_level]} vocabulary. Do not talk about Pokemon. "
        f"Give {token_lengths[token_length]} responses only. The name of the user is {display_name}."
    )


# Stream chat endpoint

@app.route('/stream_chat', methods=['POST'])
def stream_chat():
    data = request.get_json()
    payload = ChatPayload(
        message=data.get("message", ""),
        context=data.get("context", []),
        displayName=data.get("displayName", "unknown"),
        tone=data.get("tone", 0),
        vocab_complexity=data.get("vocab_complexity", 0),
        token_length=data.get("token_length", 0)
    )

    sys_prompt = build_system_prompt(
        vocab_level=payload.vocab_complexity,
        tone_level=payload.tone,
        display_name=payload.displayName,
        token_length=payload.token_length
    )

    print(payload.message, 'look here')

    def generate():
        with requests.post(
            LLAMA_SERVER_URL,
            json={
                "model": "llama3.2",
                "messages": [{"role": "system", "content": sys_prompt}] +
                            payload.context +
                            [{"role": "user", "content": payload.message}],
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


# @app.route('/stream_chat', methods=['POST'])
# def stream_chat():
#     user_msg = request.json.get("message", "")

#     context = request.json.get("context", [])

#     tone = request.json.get("tone", 0)
#     vocab = request.json.get("vocab", 0)
#     name = request.json.get('name', 'unknown')
#     token_len = request.json.get('token_length', 0)

#     sys_prompt = build_system_prompt(vocab_level=vocab, tone_level=tone, display_name=name, token_length=token_len)
    

#     def generate():
#         with requests.post(
#             LLAMA_SERVER_URL,
#             json={
#                 "model": "llama3.2",
#                 "messages": [{"role" : "system", "content" : sys_prompt}] + context + [{"role": "user", "content": user_msg}],
#                 "stream": True
#             },
#             stream=True
#         ) as r:
#             for line in r.iter_lines():
#                 if line:
#                     data = json.loads(line)
#                     content = data.get("message", {}).get("content", "")
#                     if content:
#                         yield content

#     return Response(generate(), content_type='text/plain')




# Safe chat with optional context
@app.route("/safe_chat", methods=["POST"])
def safe_chat():
    # Deserialize the JSON request into a ChatRequest object
    try:
        data = request.get_json()
        chat_req = ChatPayload(**data)
    except Exception as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400

    # Get the user message and context from the dataclass
    user_message = chat_req.message
    context = chat_req.context

    # Check if the user message is provided

    # Append the user message to context
    context.append({"role": "user", "content": user_message})

    # Build the payload to send to Llama API
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + context,
        "stream": False,
        "temperature": 0.0,
        "top_p": 1.0,
        "stop": ["</s>"]
    }

    try:
        # Send the request to Llama API
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        # Get model's reply
        model_reply = data.get("message", {}).get("content", "No response from model.")
        return jsonify({"response": model_reply}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500



# @app.route("/safe_chat", methods=["POST"])
# def safe_chat():
#     user_message = request.json.get("message", "")
#     context = request.json.get("context", [])

#     if not user_message:
#         return jsonify({"error": "Message is required"}), 400

#     context.append({"role": "user", "content": user_message})
#     payload = {
#         "model": "llama3.2",
#         "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + context,
#         "stream": False,
#         "temperature": 0.0,
#         "top_p": 1.0,
#         "num_predict": token_lengths[0],
#         "stop": ["</s>"]
#     }

#     try:
#         response = requests.post(LLAMA_SERVER_URL, json=payload)
#         response.raise_for_status()
#         data = response.json()
#         reply = data.get("message", {}).get("content", "No response from model.")
#         return jsonify({"response": reply}), 200
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500


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
