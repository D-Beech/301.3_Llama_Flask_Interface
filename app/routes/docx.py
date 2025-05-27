from flask import Blueprint, request, jsonify, Response
from app.utils.s3helpers import extract_text_auto, s3_client
from app.utils.summarizer import generate
from botocore.exceptions import NoCredentialsError
import os

docx_bp = Blueprint('docx', __name__)

@docx_bp.route('/process-docx', methods=['POST'])
def process_docx():
    file_key = request.json.get('file_key')
    print("file_key:", file_key)
    
    if not file_key:
        return jsonify({"error": "File key is required"}), 400

    try:
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        print("Using bucket:", bucket_name)
        text = extract_text_auto(bucket_name, file_key)
        print("Extracted text length:", len(text))

        # Optional safety truncation
        MAX_INPUT_LENGTH = 500
        text = "Summarize this text: " + text[:MAX_INPUT_LENGTH]

        sys_prompt = "You are JuanBot. Summarize the following document text clearly and helpfully."

        return Response(generate(text, [], sys_prompt), content_type='text/event-stream')
    except Exception as e:
        print("Error during /process-docx:", str(e))
        return jsonify({"error": str(e)}), 500

@docx_bp.route('/generate-upload-url', methods=['POST'])
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
