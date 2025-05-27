import boto3
import os
import tempfile
import docx
from botocore.exceptions import NoCredentialsError

s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

def extract_text_from_s3(bucket_name, file_key):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = file_obj['Body'].read()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        return extract_text_from_docx(temp_file_path)

    except NoCredentialsError:
        raise Exception("AWS credentials are invalid or not configured.")
    except Exception as e:
        raise Exception(f"Failed to download or read the file from S3: {str(e)}")
