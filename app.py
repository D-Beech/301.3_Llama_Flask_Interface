from flask import Flask, render_template, request, jsonify, Response
import requests
import json
#import docx_summary
import docx
from flask_cors import CORS

#These are simpler than serilizaers i reckon
from dataclasses import dataclass, field
from typing import List

#AWS SW things for Presigned URL generation and File read
import boto3
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError
import os

import tempfile

from validators import contains_banned_pokemon

import logging

# test_guardrails_validation.py

from guardrails import Guard
from guardrails.hub import DetectJailbreak, NSFWText

# Setup Guard with DetectJailbreak
# guard = Guard().use(DetectJailbreak)
guard = Guard().use(
    NSFWText, threshold=0.8, validation_method="sentence", on_fail="exception"
)





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


LLAMA_EC2_IP = os.getenv("LLAMA_EC2_IP")

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
LLAMA_SERVER_URL = f"http://localhost:11434/api/chat"
SYSTEM_PROMPT = (
    "You are an educational chatbot called EduBot, respond using a chill tone. "
    "Respond using simple vocabulary. Give very concise responses only. "
)


#The below functions get the document from S3 based on file_key (passed in body)
#Extract the text
#Ask Llama to summarize
#Return Response

#The next steps are implementing queueing and i think flutter should generate unique strings for key not use file name

def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

def extract_text_from_s3(bucket_name, file_key):
    try:
        # Download file from S3
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = file_obj['Body'].read()
        
        # Save file to a temporary location to read the text
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        return extract_text_from_docx(temp_file_path)
    
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

@app.route('/process-docx', methods=['POST'])
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
        f"You are JuanBot, a helpful and friendly chatbot for helping school students. "
        f"Do not make up facts or guess, only reply with information you are sure is accurate."
        f"Respond using a {tones[tone_level]} tone and {vocab_levels[vocab_level]} vocabulary. "
        f"Keep responses concise, about {token_lengths[token_length]} responses only. "
        f"Address the user by their name, {display_name}, to keep it personal and engaging."
    )


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
 
    def generate():
        buffer = ""  # Store full or partial response for context

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

                        # Validate the growing output (can adjust frequency or size)
                        try:
                            guard.validate(buffer)  # this might be slow for large buffers
                        except Exception as e:
                            # If validation fails, stream a warning then break
                            yield f"data: {json.dumps({'message': {'content': ' [Response blocked due to content policy]'}})}\n\n"
                            break

                        # If passed, stream this chunk
                        yield f"data: {json.dumps({'message': {'content': content}})}\n\n"

 
    return Response(generate(), content_type='text/event-stream')
 

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





@app.route('/')
def home():
    return render_template('index.html')


if __name__ == '__main__':
    app.run( port=5001, debug=True)
