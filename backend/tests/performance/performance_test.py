import asyncio
import httpx
import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

ENDPOINTS = [
    "/api/rag/ask",
    "/api/academic_agent",
    "/api/director/academic",
]

TOTAL_REQUESTS = 500

async def run_requests(client: httpx.AsyncClient, endpoint: str):
    for _ in range(TOTAL_REQUESTS // len(ENDPOINTS)):
        try:
            await client.get(f"{BASE_URL}{endpoint}")
        except Exception:
            pass

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [run_requests(client, ep) for ep in ENDPOINTS]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
