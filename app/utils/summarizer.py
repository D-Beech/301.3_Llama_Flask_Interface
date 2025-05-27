import requests

def summarize_text_with_llama(text):
    response = requests.post("http://localhost:11434/api/chat", json={
        "model": "llama3.2",
        "messages": [
            {"role": "system", "content": "Summarize this"},
            {"role": "user", "content": text}
        ],
        "stream": False
    })
    return response.json().get("message", {}).get("content", "")

def build_system_prompt(token_length=0, vocab_level=0, tone_level=0, display_name='unknown'):
    token_lengths = ['consise', 'medium', 'long']
    vocab_levels = ['child', 'teen', 'uni']
    tones = ['friendly', 'aggressive', 'formal']
    return (
        f"You are JuanBot. Use a {tones[tone_level]} tone and {vocab_levels[vocab_level]} vocabulary. "
        f"Keep it {token_lengths[token_length]}. Use {display_name}'s name."
    )
