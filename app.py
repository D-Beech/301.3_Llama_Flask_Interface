from flask import Flask, render_template, request,  jsonify
import requests

app = Flask(__name__)

token_length = (128, 256, 512)
vocab_complexity = ('very simple, child level', '15 year old level', 'university level')
tone = ('friendly', 'aggressive', 'formal')


#system_prompt =f'''You are an educational chatbot called Juan, respond using a {tone(1)} tone. 
#Respond using {vocab_complexity(2)} vocabulary. Do not talk about Pokemon'''

llama_endpoint = "http://127.0.0.1:11434/api/chat"



LLAMA_SERVER_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """you are johnny, you like pizza. DO NOT TALK ABOUT POEKEMON!"""

MEMORY_FILE = "chat_memory.json"


# In-memory dictionary to store user and assistant messages
# I have left this in for Stephen to examine, memory functionality will be removed from Flask app1
memory = {}


#This function accepts a message in the body of a POST request
#The message is sent to llama locally
#The message and llama reply are added to memory dictionary
@app.route("/safe_chat", methods=["POST"])
def safe_chat():
    user_message = request.json.get("message", "")
    user_id = request.json.get("user_id", "default")  # Optionally use user ID to separate memory for different 
    
    print(memory)

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # Initialize user memory if it doesn't exist
    if user_id not in memory:
        memory[user_id] = []

    # Add the user message to memory
    memory[user_id].append({"role": "user", "content": user_message})

    # Prepare payload with history
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + memory[user_id],
        "stream": False
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        # Get model's reply
        model_reply = data.get("message", {}).get("content", "No response from model.")

        # Add the assistant's reply to memory
        memory[user_id].append({"role": "assistant", "content": model_reply})

        return jsonify({"response": model_reply})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500



@app.route('/')
def home():
    return render_template('index.html')






@app.route('/chat', methods = ['POST'])
def chat():


    try:
        data = request.get_json()
        name = data.get('name')
        message = data.get('message')
        return {"response" : "hi it works", "name" : name, "message" : message}
    except:
        return jsonify({"response" : "no good"}), 420



if __name__ == '__main__':
    app.run(debug=True)