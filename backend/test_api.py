"""
Quick manual check that the NVIDIA API key and model in .env work.

Usage:  venv/Scripts/python.exe test_api.py
The key is read from backend/.env — never hardcode it here.
"""
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("NVIDIA_API_KEY is not set in backend/.env")

base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
model = os.getenv("NVIDIA_LLM_MODEL", "meta/llama3-8b-instruct")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "text/event-stream"
}

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100,
    "stream": True,
}

try:
    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, stream=True, timeout=60)
    print(f"Model: {model}")
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        for line in response.iter_lines():
            if line:
                print(line.decode("utf-8"))
                break # just print first line and exit
except Exception as e:
    print(f"Exception: {e}")
