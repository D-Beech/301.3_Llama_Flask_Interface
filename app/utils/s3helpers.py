import boto3
import os
import tempfile
import docx
from botocore.exceptions import NoCredentialsError
from pdfminer.high_level import extract_text as extract_pdf_text

#S3 Setup Stuff from .env
s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

#DocX
def extract_text_from_docx(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

#Txt
def extract_text_from_txt_s3(bucket_name, file_key):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = file_obj['Body'].read()
        return file_content.decode('utf-8')  # assumes UTF-8 encoding
    except NoCredentialsError:
        raise Exception("AWS credentials are invalid or not configured.")
    except Exception as e:
        raise Exception(f"Failed to download or read the TXT file from S3: {str(e)}")

#In Use DocX
def extract_text_from_docx_s3(bucket_name, file_key):
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
        raise Exception(f"Failed to download or read the DOCX file from S3: {str(e)}")

#PDF
def extract_text_from_pdf_s3(bucket_name, file_key):
    try:
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = file_obj['Body'].read()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        return extract_pdf_text(temp_file_path)

    except NoCredentialsError:
        raise Exception("AWS credentials are invalid or not configured.")
    except Exception as e:
        raise Exception(f"Failed to download or read the PDF file from S3: {str(e)}")


#Master, have removed doc support for now
def extract_text_auto(bucket_name, file_key):
    if file_key.lower().endswith(".docx"):
        return extract_text_from_docx_s3(bucket_name, file_key)
    elif file_key.lower().endswith(".txt"):
        return extract_text_from_txt_s3(bucket_name, file_key)
    elif file_key.lower().endswith(".pdf"):
        return extract_text_from_pdf_s3(bucket_name, file_key)
    else:
        raise Exception("Unsupported file type")

