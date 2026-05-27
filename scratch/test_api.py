import httpx
import asyncio
from app.core.config import settings

async def test():
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:streamGenerateContent?alt=sse'
    headers = {'x-goog-api-key': settings.llm_api_key, 'Content-Type': 'application/json'}
    payload = {
        'contents': [{'role':'user', 'parts':[{'text':'Solve 25 * 25 and explain your thought process.'}]}],
        'generationConfig': {'temperature': 0.7, 'thinkingConfig': {'thinkingLevel': 'high'}}
    }
    async with httpx.AsyncClient() as client:
        async with client.stream('POST', url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    print(line)

asyncio.run(test())
