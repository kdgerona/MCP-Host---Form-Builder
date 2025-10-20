"""
WebSocket router for streaming chat interactions.
"""

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from streaming_agent import StreamingOllamaAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Global agent instance (will be set by server.py)
agent: StreamingOllamaAgent | None = None


def set_agent(agent_instance: StreamingOllamaAgent):
    """Set the global agent instance."""
    global agent
    agent = agent_instance


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat interactions.

    Expected message format from client:
    {
        "prompt": "Your question or prompt here",
        "mode": "agent" | "simple",  // optional, defaults to "agent"
        "message_id": "optional-client-generated-id"  // optional, server generates if not provided
    }

    Response message format:
    {
        "message_id": "unique-identifier-for-this-message",
        "type": "ollama" | "mcp" | "tool_call" | "tool_result" | "system" | "error" | "done",
        "data": "content or object"
    }
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    # Send greeting from LLM upon connection
    try:
        greeting_prompt = "Say a brief, friendly greeting to welcome a new user connecting to you. Keep it under 20 words."
        greeting_message_id = str(uuid.uuid4())
        logger.info(f"Sending greeting from LLM (message_id: {greeting_message_id})...")

        # Use simple mode with accumulate=True to send greeting as single message
        async for response_chunk in agent.stream_simple(
            greeting_prompt, accumulate=True, message_id=greeting_message_id
        ):
            await websocket.send_json(response_chunk)

        logger.info("Greeting sent successfully")
    except Exception as e:
        logger.error(f"Error sending greeting: {str(e)}", exc_info=True)
        # Don't fail the connection if greeting fails
        await websocket.send_json(
            {
                "message_id": str(uuid.uuid4()),
                "type": "system",
                "data": "Welcome! How can I help you today?",
            }
        )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received message: {data[:100]}...")

            try:
                # Parse incoming message
                message = json.loads(data)
                prompt = message.get("prompt")
                mode = message.get("mode", "agent")
                client_message_id = message.get("message_id")

                # Generate message ID if client didn't provide one
                message_id = client_message_id or str(uuid.uuid4())

                if not prompt:
                    await websocket.send_json(
                        {
                            "message_id": message_id,
                            "type": "error",
                            "data": "No prompt provided",
                        }
                    )
                    continue

                logger.info(
                    f"Processing prompt in '{mode}' mode (message_id: {message_id}): {prompt[:50]}..."
                )

                # Stream response based on mode
                if mode == "simple":
                    # Simple streaming without agent complexity
                    async for response_chunk in agent.stream_simple(
                        prompt, message_id=message_id
                    ):
                        await websocket.send_json(response_chunk)
                else:
                    # Full agent streaming with MCP support
                    async for response_chunk in agent.stream_response(
                        prompt, message_id=message_id
                    ):
                        await websocket.send_json(response_chunk)

                logger.info(f"Response streaming completed (message_id: {message_id})")

            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
                error_message_id = str(uuid.uuid4())
                await websocket.send_json(
                    {
                        "message_id": error_message_id,
                        "type": "error",
                        "data": "Invalid JSON format",
                    }
                )
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                error_message_id = str(uuid.uuid4())
                await websocket.send_json(
                    {
                        "message_id": error_message_id,
                        "type": "error",
                        "data": f"Server error: {str(e)}",
                    }
                )
                await websocket.send_json(
                    {
                        "message_id": error_message_id,
                        "type": "done",
                        "data": "Error occurred",
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.close()
        except Exception:
            pass
