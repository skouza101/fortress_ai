import httpx
import asyncio
from app.core.config import settings

async def test():
    url = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
    headers = {'Authorization': f'Bearer {settings.llm_api_key}'}
    payload = {'model': 'gemini-3.1-pro-preview', 'messages': [{'role':'user','content':'hello'}]}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload)
        print(r.status_code)
        print(r.text)

asyncio.run(test())
