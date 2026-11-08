"""Read-only network smoke test; never submits user data."""
import asyncio
from app.integrations.providers import fetch_cpi


async def main():
    observations = await fetch_cpi()
    print(f"Statistics Canada: {len(observations)} observations; latest reference month {max(m for m, _ in observations)}")


if __name__ == "__main__":
    asyncio.run(main())
