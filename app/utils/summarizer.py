import requests, json

def generate(message, context, sys_prompt):
    print(message, context, sys_prompt,flush=True)
    with requests.post(
        "http://localhost:11434/api/chat",
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
                        # guard.validate(content)  # Optional validation hook
                        yield f"data: {json.dumps({'message': {'content': content}})}\n\n"
                    except Exception as e:
                        print("Blocked chunk:", repr(content), flush=True)
                        print("Validation error:", repr(e), flush=True)
                        yield f"data: {json.dumps({'message': {'content': ' [Response blocked due to content policy]'}})}\n\n"
                        break




def build_system_prompt(token_length=0, vocab_level=0, tone_level=0, display_name='unknown'):
    token_lengths = ['consise', 'medium', 'long']
    vocab_levels = ['child', 'teen', 'uni']
    tones = ['friendly', 'aggressive', 'formal']
    return (
        f"You are JuanBot. Use a {tones[tone_level]} tone and {vocab_levels[vocab_level]} vocabulary. "
        f"Keep it {token_lengths[token_length]}. Use {display_name}'s name."
    )
