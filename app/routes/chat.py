from flask import Blueprint, request, jsonify, Response
import requests

# from app.utils.guards import guard
from app.utils.summarizer import build_system_prompt, generate
from app.models import ChatPayload

import app.utils.custom_guards as cg

from app.firebase_auth import require_firebase_auth

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

    # if cg.contains_banned_content(payload.message):
    #     sys_prompt = "User attempted to talk about NSFW content, create error message warning them not to"
    #     payload.message = ""
    #     payload.context = []

    


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

    return Response(generate(payload.message, payload.context, sys_prompt), content_type='text/event-stream')


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

@chat_bp.route('/protected')
@require_firebase_auth
def protected():
    return jsonify({
        "message": f"Hello, {request.user['uid']}!",
        "user_info": request.user
    })
