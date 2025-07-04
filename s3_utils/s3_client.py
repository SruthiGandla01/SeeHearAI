# app/s3_utils/s3_client.py
import boto3
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def upload_file(local_path, s3_key):
    try:
        s3.upload_file(local_path, S3_BUCKET, s3_key)
        print(f"✅ Uploaded: {local_path} → s3://{S3_BUCKET}/{s3_key}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

def upload_text(content, s3_key):
    try:
        s3.put_object(Body=content.encode('utf-8'), Bucket=S3_BUCKET, Key=s3_key)
        print(f"✅ Uploaded text to: s3://{S3_BUCKET}/{s3_key}")
    except Exception as e:
        print(f"❌ Text upload failed: {e}")

def log_event(session_id, question, answer):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_key = f'sessions/{session_id}/log_{timestamp}.txt'
    log_content = f"Session: {session_id}\nTime: {timestamp}\nQ: {question}\nA: {answer}"
    upload_text(log_content, log_key)

def test_s3_connection():
    try:
        response = s3.list_buckets()
        print("🪣 Available Buckets:")
        for bucket in response['Buckets']:
            print(f" - {bucket['Name']}")
    except Exception as e:
        print(f"❌ S3 connection test failed: {e}")
