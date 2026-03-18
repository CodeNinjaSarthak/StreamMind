"""Load testing script."""

import asyncio
import os
import time
from typing import List

import aiohttp


async def make_request(session: aiohttp.ClientSession, url: str) -> dict:
    """Make a single HTTP request.

    Args:
        session: aiohttp session.
        url: URL to request.

    Returns:
        Response data.
    """
    async with session.get(url) as response:
        return await response.json()


async def run_load_test(url: str, num_requests: int, concurrency: int) -> None:
    """Run load test.

    Args:
        url: URL to test.
        num_requests: Number of requests to make.
        concurrency: Number of concurrent requests.
    """
    print(f"Starting load test: {num_requests} requests, {concurrency} concurrent")

    async with aiohttp.ClientSession() as session:
        tasks: List = []
        start_time = time.time()

        for i in range(0, num_requests, concurrency):
            batch = [make_request(session, url) for _ in range(min(concurrency, num_requests - i))]
            tasks.extend(batch)
            await asyncio.gather(*batch)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Load test completed: {num_requests} requests in {duration:.2f}s")
        print(f"Requests per second: {num_requests / duration:.2f}")


if __name__ == "__main__":
    url = os.getenv("TEST_URL", "http://localhost:8000/health")
    num_requests = int(os.getenv("NUM_REQUESTS", "100"))
    concurrency = int(os.getenv("CONCURRENCY", "10"))

    asyncio.run(run_load_test(url, num_requests, concurrency))
