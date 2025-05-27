import requests
import json
from flask import jsonify

LLAMA_SERVER_URL = "http://localhost:11434/api/chat"

def stream_llama_response(payload, sys_prompt, guard):
    buffer = ""
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
                    buffer += content
                    try:
                        guard.validate(buffer)
                    except Exception:
                        yield f"data: {json.dumps({'message': {'content': ' [Response blocked due to content policy]'}})}\n\n"
                        break
                    yield f"data: {json.dumps({'message': {'content': content}})}\n\n"


