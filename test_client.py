"""
Simple WebSocket test client for the Ollama MCP Streaming Server.

Usage:
    python test_client.py
    python test_client.py --url ws://localhost:8000/ws
    python test_client.py --prompt "Hello, world!" --mode simple
"""

import asyncio
import json
import sys

import websockets


async def test_websocket(
    url: str = "ws://localhost:8000/ws",
    prompt: str = "What is 2+2?",
    mode: str = "simple",
):
    """
    Test the WebSocket server with a simple prompt.

    Args:
        url: WebSocket server URL
        prompt: Prompt to send
        mode: "agent" or "simple"
    """
    print(f"Connecting to {url}...")

    try:
        async with websockets.connect(url) as websocket:
            print(f"Connected! Sending prompt: '{prompt}' (mode: {mode})")

            # Send prompt
            message = {"prompt": prompt, "mode": mode}
            await websocket.send(json.dumps(message))

            # Receive and display responses
            print("\nStreaming response:")
            print("-" * 60)

            accumulated_response = ""

            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)

                    msg_type = data.get("type")
                    msg_data = data.get("data")

                    if msg_type == "ollama":
                        # Print tokens as they arrive
                        print(msg_data, end="", flush=True)
                        accumulated_response += msg_data

                    elif msg_type == "mcp":
                        print(f"\n[MCP Response: {msg_data}]")

                    elif msg_type == "tool_call":
                        print(f"\n[Tool Call: {msg_data}]")

                    elif msg_type == "tool_result":
                        print(f"\n[Tool Result: {msg_data}]")

                    elif msg_type == "system":
                        print(f"\n[System: {msg_data}]")

                    elif msg_type == "error":
                        print(f"\n[Error: {msg_data}]")

                    elif msg_type == "done":
                        print(f"\n\n[{msg_data}]")
                        break

                except websockets.exceptions.ConnectionClosed:
                    print("\n\nConnection closed by server")
                    break

            print("-" * 60)
            print(f"\nFinal accumulated response:\n{accumulated_response}")

    except ConnectionRefusedError:
        print(f"Error: Could not connect to {url}")
        print("Make sure the server is running:")
        print("  python server.py")
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


async def interactive_mode(url: str = "ws://localhost:8000/ws"):
    """
    Interactive chat mode for testing.

    Args:
        url: WebSocket server URL
    """
    print(f"Connecting to {url}...")
    print("Interactive mode - type your prompts (Ctrl+C to exit)")
    print("-" * 60)

    try:
        async with websockets.connect(url) as websocket:
            print("Connected!\n")

            while True:
                # Get user input
                try:
                    prompt = input("You: ").strip()
                    if not prompt:
                        continue

                    # Determine mode
                    mode = "simple"
                    if prompt.startswith("/agent "):
                        mode = "agent"
                        prompt = prompt[7:]
                    elif prompt.startswith("/simple "):
                        prompt = prompt[8:]

                    # Send prompt
                    message = {"prompt": prompt, "mode": mode}
                    await websocket.send(json.dumps(message))

                    # Receive and display responses
                    print(f"Assistant ({mode}): ", end="", flush=True)

                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)

                        msg_type = data.get("type")
                        msg_data = data.get("data")

                        if msg_type == "ollama":
                            print(msg_data, end="", flush=True)
                        elif msg_type == "system":
                            print(f"\n[{msg_data}]", flush=True)
                        elif msg_type == "error":
                            print(f"\n[Error: {msg_data}]", flush=True)
                        elif msg_type == "done":
                            print("\n")
                            break

                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break

    except ConnectionRefusedError:
        print(f"Error: Could not connect to {url}")
        print("Make sure the server is running:")
        print("  python server.py")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test WebSocket client")
    parser.add_argument(
        "--url", default="ws://localhost:8000/ws", help="WebSocket server URL"
    )
    parser.add_argument(
        "--prompt", help="Prompt to send (if not specified, enters interactive mode)"
    )
    parser.add_argument(
        "--mode", choices=["agent", "simple"], default="simple", help="Agent mode"
    )

    args = parser.parse_args()

    if args.prompt:
        # Single prompt mode
        asyncio.run(test_websocket(args.url, args.prompt, args.mode))
    else:
        # Interactive mode
        asyncio.run(interactive_mode(args.url))
