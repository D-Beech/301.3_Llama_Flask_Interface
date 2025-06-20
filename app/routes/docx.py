from flask import Blueprint, request, jsonify, Response
from app.utils.s3helpers import extract_text_auto, s3_client
from app.utils.summarizer import generate, generate_no_stream
from botocore.exceptions import NoCredentialsError
import os
import app.utils.custom_guards as cg
from app.firebase_auth import require_firebase_auth, g

docx_bp = Blueprint('docx', __name__)

   
#Reads file from S3 using file_key
#Summarises document and returns, summary + original text    
@docx_bp.route('/process-file', methods=['POST'])
@require_firebase_auth
def process_file():
    file_key = request.json.get('file_key')
    print("file_key:", file_key)
    
    if not file_key:
        return jsonify({"error": "File key is required"}), 400

    try:
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        print("Using bucket:", bucket_name)
        text = extract_text_auto(bucket_name, file_key)
        print("Extracted text length:", len(text))

        # Optional safety truncation, SRS document specified 2 page limit for file upload/summary. 
        # Documents which are too long will trigger
        MAX_INPUT_LENGTH = 12000 # approx 2000 words
        text = "Summarize this text: " + text[:MAX_INPUT_LENGTH]

        if cg.contains_banned_content(text):
            text = "Text contained banned content and has been removed"

        sys_prompt = "Summarize the following document text clearly and helpfully. Do not make up information under any circumstance"

        return jsonify({"summary" : generate_no_stream(text, [], sys_prompt), "og_text" : text})
    except Exception as e:
        print("Error during /process-docx:", str(e))
        return jsonify({"error": str(e)}), 500
    
#Generates pre-signed url for document upload from client app
#This method was chosen to minimize load on server
@docx_bp.route('/generate-upload-url', methods=['POST'])
@require_firebase_auth
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
                'Bucket': os.getenv("AWS_S3_BUCKET_NAME"),
                'Key': filename,
                'ContentType': content_type
            },
            ExpiresIn=3600,
        )
        return jsonify({'upload_url': signed_url})
    except NoCredentialsError:
        return jsonify({'error': 'Invalid AWS credentials'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
