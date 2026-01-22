import os
import httpx
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found.")
    exit(1)

print(f"Testing key: {api_key[:5]}...")
url = "https://generativelanguage.googleapis.com/v1beta/models"
params = {"key": api_key}
try:
    response = httpx.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        models = response.json().get("models", [])
        for m in models:
            if "gemini" in m["name"]:
                print(m["name"])
    else:
        print(response.text)
except Exception as e:
    print(e)
