from flask import Flask, render_template, request, jsonify, Response
import requests
import json

#import docx_summary
import docx
from flask_cors import CORS

# pdf summary support
from PyPDF2 import PdfReader

import win32com.client

#These are simpler than serilizaers i reckon
from dataclasses import dataclass, field
from typing import List

#AWS SW things for Presigned URL generation and File read
import boto3
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError
import os

import tempfile

from guardrails import Guard
from validators import contains_banned_pokemon

import logging

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,  # Use DEBUG for more verbose output
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)


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

load_dotenv()

# AWS config from .env
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")


# Create boto3 client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Create a session using boto3
s3_client = boto3.client('s3', region_name=AWS_REGION)

# Settings
LLAMA_SERVER_URL = "http://localhost:11434/api/chat"
SYSTEM_PROMPT = (
    "You are an educational chatbot called Juan, respond using a chill tone. "
    "Respond using simple vocabulary. Do not talk about Pokemon. Give very concise responses only."
)


#The below functions get the document from S3 based on file_key (passed in body)
#Extract the text
#Ask Llama to summarize
#Return Response

#The next steps are implementing queueing and i think flutter should generate unique strings for key not use file name

# Extract files with ".docx" extension
def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

# Extract files with ".pdf" extension
def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''
        return text
    except Exception as e:
        raise Exception(f"Error reading PDF file: {str(e)}")
    
# Extract files with ".txt" extension
def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Convert ".doc" files to ".txt" files
def convert_doc_to_txt_windows(doc_path):
    word = win32com.client.Dispatch("Word.Application")
    doc = word.Documents.Open(doc_path)
    txt_path = doc_path.replace('.doc', '.txt')
    doc.SaveAs(txt_path, FileFormat=2) # 2 is for .txt
    doc.Close()
    word.Close()
    word.Quit()
    return txt_path

# Delete file from S3
def delete_file_from_s3(bucket_name, key):
    s3 = boto3.client('s3')
    s3.delete_object(Bucket=bucket_name, Key=key)
    print(f"File {key} deleted from bucket {bucket_name}.")

def extract_text_from_s3(bucket_name, file_key):
    try:
        # Download file from S3
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = file_obj['Body'].read()

        # Get the file extension
        ext = os.path.splitext(file_key)[1].lower()
        
        # Save file to a temporary location to read the text
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
    
        # Determine extract tool based on file extension
        if ext == '.docx':
            return extract_text_from_docx(temp_file_path)
        elif ext == '.pdf':
            return extract_text_from_pdf(temp_file_path)
        elif ext == '.txt':
            return extract_text_from_txt(temp_file_path)
        elif ext == '.doc':
            txt_path = convert_doc_to_txt_windows(temp_file_path)
            return extract_text_from_txt(txt_path)
        else:
            raise Exception(f"Unsupported file format: {ext}")
    
    except NoCredentialsError:
        raise Exception("AWS credentials are invalid or not configured.")
    except Exception as e:
        raise Exception(f"Failed to download or read the file from S3: {str(e)}")

def summarize_text_with_llama(text):
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Please summarize the following: {text}"}],
        "stream": False,
        "temperature": 0.0,
        "top_p": 1.0,
        "stop": ["</s>"]
    }

    try:
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "No summary response.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get a response from Llama API: {str(e)}")

@app.route('/process-file', methods=['POST'])
def process_docx():
    # Get the filename from the request
    data = request.get_json()
    file_key = data.get('file_key')

    if not file_key:
        return jsonify({"error": "File key is required"}), 400
    
    try:
        # Extract text from DOCX file stored in S3
        extracted_text = extract_text_from_s3(AWS_S3_BUCKET_NAME, file_key)
        
        # Summarize the text with Llama
        summary = summarize_text_with_llama(extracted_text)

        # Attempt to delete the file but don't fail if it doesn't work
        # try:
        #     delete_file_from_s3(AWS_S3_BUCKET_NAME, file_key)
        # except Exception as delete_error:
        #     print(f"Warning: Failed to delete file from S3: {delete_error}")
        
        return jsonify({"summary": summary}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



#This route generates presigned url for uploading documents to s3
#Currently any file type is accepted, flutter app needs to only allowe doc, docx, pdf, txt
@app.route('/generate-upload-url', methods=['POST'])
def generate_upload_url():
    data = request.get_json()
    filename = data.get('filename')
    content_type = data.get('content_type')

    if not filename or not content_type:
        return jsonify({'error': 'filename and content_type are required'}), 400

    try:
        signed_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': AWS_S3_BUCKET_NAME,
                'Key': filename,
                'ContentType': content_type
            },
            ExpiresIn=3600,
        )
        print(signed_url)
        return jsonify({'upload_url': signed_url})
    except NoCredentialsError:
        return jsonify({'error': 'Invalid AWS credentials'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


# # Stream chat endpoint
# # This post api has streaming enabled, streaming will also need to be enabled in Flutter
# @app.route('/stream_chat', methods=['POST'])
# def stream_chat():
#     data = request.get_json()
#     payload = ChatPayload(
#         message=data.get("message", ""),
#         context=data.get("context", []),
#         displayName=data.get("displayName", "unknown"),
#         tone=data.get("tone", 0),
#         vocab_complexity=data.get("vocab_complexity", 0),
#         token_length=data.get("token_length", 0)
#     )

#     result = guard.parse(payload.message)

#     if not result.validation_passed:
#         print("This should have been blocked")
#         # return appropriate HTTP response, e.g. 400 or 403, not 300
#         return jsonify({"response": "Blocked by Guardrails"}), 400

#     sys_prompt = build_system_prompt(
#         vocab_level=payload.vocab_complexity,
#         tone_level=payload.tone,
#         display_name=payload.displayName,
#         token_length=payload.token_length
#     )

#     print(payload.message, 'look here')

#     def generate():
#         with requests.post(
#             LLAMA_SERVER_URL,
#             json={
#                 "model": "llama3.2",
#                 "messages": [{"role": "system", "content": sys_prompt}] +
#                             payload.context +
#                             [{"role": "user", "content": payload.message}],
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

    # Custom validation instead of guardrails
    # if profanity.contains_profanity(payload.message):
    #     return jsonify({"response": "Blocked: profanity detected."}), 400

    if contains_banned_pokemon(payload.message):
        print("User Input Blocked: ", payload.message)
        app.logger.error("Llm Output Blocked: %s",  payload.message)
        payload.message = ""
        sys_prompt = "User attempted to talk about banned content, do not respond except for error message"
        payload.context = []


    else:
        sys_prompt = build_system_prompt(
            vocab_level=payload.vocab_complexity,
            tone_level=payload.tone,
            display_name=payload.displayName,
            token_length=payload.token_length
        )

    def generate():
        buffer = ""  # Store generated text so far

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
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            buffer += content # without this the check will only check against tokens which may be longer than a banned word
                            if contains_banned_pokemon(buffer):
                                yield "\n\n| Error, generated restricted content. |\n"
                                print("Llm Output Blocked: ", buffer)
                                app.logger.error("Llm Output Blocked: %s",  buffer)
                                return  # Stop streaming immediately
                            # Format as Server-Sent Event
                            yield f"data: {json.dumps({'message': {'content': content}})}\n\n"
                    except json.JSONDecodeError:
                        continue

    return Response(generate(), content_type='text/event-stream')







# This is the regular POST chat endpoint
# Sends a single message, no streaming. Easier to use.

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
    

#Generate Title API, in progress    
@app.route('/make_title', methods=['POST'])
def make_title():
    context = request.json.get("context",[])

    print(context)

    title_sys_prompt = """You are to return a single concise title summarizing the conversation. Keep it consise, if nothing here just say edubot chat or something"""
    
    # Build the payload to send to Llama API
    payload = {
        "model": "llama3.2",
        "messages": context +  [{"role": "user", "content": title_sys_prompt}], #I tried using System role message, but user message sent last works most reliably to generate title
        "stream": False,
    }

    try:
        # Send the request to Llama API
        response = requests.post(LLAMA_SERVER_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        print(data)

        # Get model's reply
        model_reply = data.get("message", {}).get("content", "No response from model.")
        return jsonify({"title": model_reply}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

    return



@app.route('/')
def home():
    return render_template('index.html')

# @app.route('/fileTest', methods=['GET'])
# def file_test():
#     with open('CS301.2_IDD_Datu_Beech_Submission.docx', 'rb') as file:
#         text = extract_text_from_docx(file)
#     message = f"please summarize the following: {text}"

#     payload = {
#         "model": "llama3.2",
#         "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}],
#         "stream": False,
#         "temperature": 0.0,
#         "top_p": 1.0,
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


if __name__ == '__main__':
    app.run(port=5001, debug=True)
