from flask import Blueprint, request, jsonify, Response
import requests
import json

from app.utils.guards import guard
from app.utils.summarizer import build_system_prompt
from app.models import ChatPayload

import re

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/stream_chat', methods=['POST'])
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

    # try:
    #     validated = guard.validate(payload.message)
    #     print('Prompt passed guardrails')
    # except Exception as e:
    #     print(" Failed Validation")
    #     print(f'Error: {e}')
    #     sys_prompt = "User attempted to talk about NSFW content, create error message warning them not to"
    #     payload.message = ""
    #     payload.context = []

 
    print(payload.message, 'look here')
 
    # def generate():
    #     import re
    #     buffer = ""     # Partial sentence buffer
    #     full_output = ""  # Accumulates validated output

    #     def ends_with_punctuation(text):
    #         return bool(re.search(r"[.!?]['\"]?\s*$", text))

    #     with requests.post(
    #         "http://localhost:11434/api/chat",
    #         json={
    #             "model": "llama3.2",
    #             "messages": [{"role": "system", "content": sys_prompt}] +
    #                         payload.context +
    #                         [{"role": "user", "content": payload.message}],
    #             "stream": True
    #         },
    #         stream=True
    #     ) as r:
    #         for line in r.iter_lines():
    #             if line:
    #                 data = json.loads(line)
    #                 content = data.get("message", {}).get("content", "")

    #                 if content:
    #                     buffer += content

    #                     if ends_with_punctuation(buffer):
    #                         # Sentence complete — validate
    #                         try:
    #                             guard.validate(buffer)
    #                             full_output += buffer
    #                             yield f"data: {json.dumps({'message': {'content': buffer}})}\n\n"
    #                         except Exception as e:
    #                             print("Blocked buffer:", repr(buffer), flush=True)
    #                             print("Validation error:", repr(e), flush=True)
    #                             yield f"data: {json.dumps({'message': {'content': ' [Response blocked due to content policy]'}})}\n\n"
    #                             break

    #                         buffer = ""  # Clear the buffer after validation

    def generate():
        with requests.post(
            "http://localhost:11434/api/chat",
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
                        try:
                            guard.validate(content)
                            yield f"data: {json.dumps({'message': {'content': content}})}\n\n"
                        except Exception as e:
                            print("Blocked chunk:", repr(content), flush=True)
                            print("Validation error:", repr(e), flush=True)
                            yield f"data: {json.dumps({'message': {'content': ' [Response blocked due to content policy]'}})}\n\n"
                            break

    return Response(generate(), content_type='text/event-stream')


@chat_bp.route('/make_title', methods=['POST'])
def make_title():
    context = request.json.get("context", [])
    prompt = "You are to return a single concise title summarizing the conversation..."
    payload = {
        "model": "llama3.2",
        "messages": context + [{"role": "user", "content": prompt}],
        "stream": False
    }
    response = requests.post("http://localhost:11434/api/chat", json=payload)
    content = response.json().get("message", {}).get("content", "No response.")
    return jsonify({"title": content})
