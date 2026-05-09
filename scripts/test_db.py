
import asyncio
from app.db.store import store

async def main():
    try:
        print("Connecting to store...")
        await store.connect()
        print("Connected!")
        
        # Try a simple query
        print("Listing conversations for user 'test'...")
        convs = await store.list_conversations("test")
        print(f"Found {len(convs)} conversations.")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await store.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    asyncio.run(main())
