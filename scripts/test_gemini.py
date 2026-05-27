import asyncio
import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services import llm

async def main():
    print("=== Testing Gemini Provider Integration ===")
    print(f"Active LLM Provider: {settings.LLM_PROVIDER}")
    print(f"API Base Endpoint:   {settings.llm_api_base}")
    print(f"API Model Name:      {settings.llm_model}")
    print(f"API Key Configured:  {'Yes' if settings.llm_api_key else 'No'}")
    
    # We will try a test invocation.
    # Note: If no GEMINI_API_KEY is supplied yet, it might raise an API key error,
    # which is the expected API response.
    if settings.LLM_PROVIDER.lower() != "gemini":
        print("\n[WARNING] LLM_PROVIDER is not set to 'gemini' in .env. Skipping call test.")
        return
        
    if not settings.llm_api_key:
        print("\n[INFO] No GEMINI_API_KEY set in .env yet. Call test will be skipped.")
        return
        
    print("\nAttempting connection check...")
    try:
        results = await llm.check_connectivity()
        print(f"Connectivity result: {results}")
        
        print("\nAttempting completion test...")
        resp = await llm.generate("State clearly in 3 words: 'Fortress AI active'", max_tokens=20)
        print(f"LLM Response:\n{resp}\n")
    except Exception as e:
        print(f"\n[ERROR] Connection or call failed (this is expected if API key is invalid/empty): {e}")

if __name__ == "__main__":
    asyncio.run(main())
