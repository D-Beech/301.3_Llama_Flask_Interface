from flask import Blueprint, request, jsonify
from app.utils.s3helpers import extract_text_from_s3, s3_client
from app.utils.summarizer import summarize_text_with_llama
from botocore.exceptions import NoCredentialsError
import os

docx_bp = Blueprint('docx', __name__)

@docx_bp.route('/process-docx', methods=['POST'])
def process_docx():
    file_key = request.json.get('file_key')
    if not file_key:
        return jsonify({"error": "File key is required"}), 400

    try:
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        text = extract_text_from_s3(bucket_name, file_key)
        summary = summarize_text_with_llama(text)
        return jsonify({"summary": summary})
    except Exception as e:
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
