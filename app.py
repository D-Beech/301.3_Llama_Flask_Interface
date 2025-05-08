from flask import Flask, render_template, request,  jsonify
import requests
import docx


app = Flask(__name__)

token_length = (32, 256, 512)
vocab_complexity = ('very simple, child level', '15 year old level', 'university level')
tone = ('friendly', 'extremely aggressive', 'formal')


SYSTEM_PROMPT =f'''You are an educational chatbot called Juan, respond using a {tone[0]} tone. 
#Respond using {vocab_complexity[2]} vocabulary. Do not talk about Pokemon. Give very consise responses only'''

llama_endpoint = "http://127.0.0.1:11434/api/chat"

LLAMA_SERVER_URL = "http://localhost:11434/api/chat"

#SYSTEM_PROMPT = """you are johnny, you like pizza. DO NOT TALK ABOUT POEKEMON!"""

# In-memory dictionary to store user and assistant messages
# I have left this in for Stephen to examine, memory functionality will be removed from Flask app1
memory = {}



#This function accepts a message in the body of a POST request
#The message is sent to llama locally
#The message and llama reply are added to memory dictionary
@app.route("/safe_chat", methods=["POST"])
def safe_chat():
    user_message = request.json.get("message", "") #This is the user prompt
    context = request.json.get("context", "") #for context (memory) passed in via POST body
    
    #If message is not in payload error code is returned
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    context.append({"role":"user", "content" : user_message})

    # Prepare payload with history
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + context,
        "stream": False,
        "tempurature" : 0.0, #Very stict hallucintaion control
        "top_p" : 1.0, #Every token is considered, strict hallucintaion control
        "num_predict" : token_length[0],
        "stop" : ["</s>"] #This is Meta's recommendation to stop hallucinated user messages
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        # Get model's reply
        model_reply = data.get("message", {}).get("content", "No response from model.")

        return jsonify({"response": model_reply}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500



@app.route('/')
def home():
    return render_template('index.html')


##Below is filereading code for docx


#Extracts text and returns paragraphs seperated by newline
def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)
    return "\n".join(text)


#same as above function but limits to first 1000words
def extract_text_from_docx_limited(docx_file, max_words=1000):
    doc = docx.Document(docx_file)
    words = []

    for paragraph in doc.paragraphs:
        paragraph_words = paragraph.text.split()
        if len(words) + len(paragraph_words) > max_words:
            remaining = max_words - len(words)
            words.extend(paragraph_words[:remaining])
            break
        words.extend(paragraph_words)

    return ' '.join(words)

@app.route('/fileTest', methods=['GET'])
def fileTest():

    message = "please summarize the following: "

    with open('CS301.2_IDD_Datu_Beech_Submission.docx', 'rb') as file:
        text = extract_text_from_docx(file)  # Adjust 40 if needed
        message += text

    print(message)
    
     # Prepare payload with history
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role":"user", "content" : message}],
        "stream": False,
        "temperature" : 0.0, #Very stict hallucintaion control
        "top_p" : 1.0, #Every token is considered, strict hallucintaion control
        "num_predict" : token_length[0],
        "stop" : ["</s>"] #This is Meta's recommendation to stop hallucinated user messages
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        # Get model's reply
        model_reply = data.get("message", {}).get("content", "No response from model.")

        return jsonify({"response": model_reply}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

