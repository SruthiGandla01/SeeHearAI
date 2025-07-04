# app/log_to_lambda.py
import requests
import os
LAMBDA_URL = os.getenv("LAMBDA_LOG_URL")

def log_to_dynamodb(session_id, question, response, scene_caption):
    payload = {
        "session_id": session_id,
        "question": question,
        "response": response,
        "scene": scene_caption
    }
    try:
        res = requests.post(LAMBDA_URL, json=payload)
        print("✅ Logged to Lambda:", res.status_code)
    except Exception as e:
        print(f"❌ Lambda log failed: {e}")