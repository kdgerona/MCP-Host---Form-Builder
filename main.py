import asyncio
from ollama_agent import OllamaAgent


async def main():
    agent = OllamaAgent()

    result = await agent.run(
        "Compute md5 hash for following string: 'Hello, world!' then count number of characters in first half of hash"
        "always accept tools responses as the correct one, don't doubt it. Always use a tool if available instead of doing it on your own"
    )

    print("\n🔥 Result:", result)


if __name__ == "__main__":
    asyncio.run(main())
