from flask import Blueprint, request, jsonify, Response
import requests

# from app.utils.guards import guard
from app.utils.summarizer import build_system_prompt, generate, generate_w_uid
from app.models import ChatPayload
import app.utils.custom_guards as cg
from app.firebase_auth import require_firebase_auth, g
from app.utils.guard_logging import logger


chat_bp = Blueprint('chat', __name__)

#This function accepts message from client app and returns SSE, stream response
@chat_bp.route("/stream_chat", methods=["POST"])
@require_firebase_auth
def stream_chat():
    data = request.get_json()
    uid = getattr(g, "user", {}).get("uid", "unknown") #for logging users privately


    payload = ChatPayload(
        message=data.get("message", ""),
        context=data.get("context", []), #If no context, passes in empty array
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

    #Track if banned content was triggered by this UID
    is_banned, trigger = cg.contains_banned_content(payload.message)
    if is_banned:
        sys_prompt = "User attempted to talk about that content, create error message warning them not to"
        sys_prompt = f"User attempted to talk about restricted content: {trigger}, create short friendly error message warning them not to"
        payload.message = ""
        payload.context = []
        logger.info(f"User UID: {uid} Prompt Triggered Guard: {trigger}")

    print(payload.message, 'look here')
    return Response(generate_w_uid(payload.message, payload.context, sys_prompt, uid), content_type='text/event-stream')



#This function generates a title based on context
@chat_bp.route('/make_title', methods=['POST'])
@require_firebase_auth
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


#Test route for checking firebase auth is working correctly
@chat_bp.route('/protected')
@require_firebase_auth
def protected():
    return jsonify({
        "message": f"Hello, {request.user['uid']}!",
        "user_info": request.user
    })


