import requests
import json
import time

url = "http://localhost:3000/api/chat/stream"
payload = {
    "message": "Search for the latest UK regulations on employment notice periods.",
    "model": "gemini-3.1-pro-preview"
}
headers = {
    "Content-Type": "application/json"
}

start_time = time.time()
with requests.post(url, json=payload, headers=headers, stream=True) as r:
    for line in r.iter_lines():
        if line:
            print(f"[{time.time() - start_time:.2f}s] {line.decode('utf-8')}")
