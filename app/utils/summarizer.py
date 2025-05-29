import requests, json
import app.utils.custom_guards as cg
from app.utils.guard_logging import logger

llama_url = "54.153.130.139"

def generate_no_stream(message, context, sys_prompt):
    print(message, context, sys_prompt, flush=True)

    # Send a regular (non-streaming) POST request
    response = requests.post(
        f"http://{llama_url}:11434/api/chat",
        json={
            "model": "llama3.2",
            "messages": [{"role": "system", "content": sys_prompt}] +
                       context +
                       [{"role": "user", "content": message}],
            "stream": False  # No streaming
        }
    )

    if response.status_code != 200:
        print(f"Error from LLM API: {response.status_code} {response.text}", flush=True)
        return " [Error generating response]"

    data = response.json()

    # Assuming the response JSON structure is:
    # { "message": { "content": "<full text>" } }
    content = data.get("message", {}).get("content", "")

    # Check for banned content once on the full generated content
    if cg.contains_banned_content(content):
        print("Banned content detected in final response", flush=True)
        return " [Response redacted due to content policy]"

    return content



def generate(message, context, sys_prompt):
    print(message, context, sys_prompt,flush=True)
    with requests.post(
        f"http://{llama_url}:11434/api/chat",
        json={
            "model": "llama3.2",
            "messages": [{"role": "system", "content": sys_prompt}] +
                       context +
                       [{"role": "user", "content": message}],
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
                        # if cg.contains_banned_content(content):
                        #     raise ValueError("Banned Content Identified")
                        # # guard.validate(content)  # Optional validation hook
                        yield f"data: {json.dumps({'message': {'content': content}})}\n\n"
                    except Exception as e:
                        print("Blocked chunk:", repr(content), flush=True)
                        print("Validation error:", repr(e), flush=True)
                        yield f"data: {json.dumps({'message': {'content': ' [Response blocked due to content policy]'}})}\n\n"
                        break


#This one can track UID for who is generating responses that trigger guards
def generate_w_uid(message, context, sys_prompt, uid):
    buffer = ""
    with requests.post(
        f"http://{llama_url}:11434/api/chat",
        json={
            "model": "llama3.2",
            "messages": [{"role": "system", "content": sys_prompt}] +
                       context +
                       [{"role": "user", "content": message}],
            "stream": True
        },
        stream=True
    ) as r:
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                buffer += content

                # Only check filter on buffer once it's long enough (e.g., 20 chars)
                if len(buffer) >= 20 or content.endswith(('.', '!', '?')):
                    is_banned, trigger = cg.contains_banned_content(buffer)
                    if is_banned:
                        logger.info(f"User UID: {uid} Response Generated Triggered Guard: {trigger}")
                        # Yield a warning message and break the stream
                        yield f"data: {json.dumps({'message': {'content': f' [Response blocked due to Restricted Content: {trigger}]'}})}\n\n"
                        return
                    else:
                        # Yield the buffered content, then reset buffer
                        yield f"data: {json.dumps({'message': {'content': buffer}})}\n\n"
                        buffer = ""

        # If any leftover buffer after the stream ends yield it
        if buffer:
            yield f"data: {json.dumps({'message': {'content': buffer}})}\n\n"


def build_system_prompt(token_length=0, vocab_level=0, tone_level=0, display_name='unknown'):
    token_lengths = ['consise', 'medium', 'long']
    vocab_levels = ['child', 'teen', 'uni']
    tones = ['friendly', 'aggressive', 'formal']
    return (
        f"You are EduBot. Use a {tones[tone_level]} tone and {vocab_levels[vocab_level]} vocabulary. "
        f"Keep responses {token_lengths[token_length]}. The user's name is: {display_name}."
        f"Do not make up information under any circumstance. If you are unsure you can reply I am not sure."
    )
