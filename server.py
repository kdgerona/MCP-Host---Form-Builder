"""
FastAPI WebSocket server for streaming Ollama + MCP responses to React frontend.

This server provides:
- WebSocket endpoint for real-time streaming communication
- Health check endpoint
- Server info endpoint
- CORS support for React frontend integration
"""

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from streaming_agent import StreamingOllamaAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Server configuration
HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")


# Global agent instance (initialized on startup)
agent: StreamingOllamaAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    global agent

    # Startup
    logger.info("Initializing Streaming Ollama Agent...")
    agent = StreamingOllamaAgent()
    await agent.initialize()
    logger.info("Agent initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down server...")
    agent = None


# Initialize FastAPI app
app = FastAPI(
    title="Ollama MCP Streaming Server",
    description="WebSocket server for streaming Ollama + MCP responses",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "Ollama MCP Streaming Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {"websocket": "/ws", "health": "/health", "info": "/info"},
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent_initialized": agent is not None}


@app.get("/info")
async def server_info():
    """Server configuration and status information."""
    if agent is None:
        return JSONResponse(status_code=503, content={"error": "Agent not initialized"})

    return {
        "ollama_model": agent.ollama_model,
        "ollama_base_url": agent.ollama_base_url,
        "mcp_server_url": agent.mcp_server_url,
        "max_steps": agent.max_steps,
        "server": {"host": HOST, "port": PORT, "cors_origins": CORS_ORIGINS},
    }


@app.websocket("/ws")
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


# Additional endpoint for testing without WebSocket
@app.post("/chat")
async def chat_endpoint(request: dict):
    """
    HTTP POST endpoint for testing (non-streaming).

    Request body:
    {
        "prompt": "Your question here"
    }

    Returns accumulated response as JSON.
    """
    if agent is None:
        return JSONResponse(status_code=503, content={"error": "Agent not initialized"})

    prompt = request.get("prompt")
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "No prompt provided"})

    # Collect all streaming responses
    responses = []
    async for chunk in agent.stream_response(prompt):
        responses.append(chunk)

    return {"responses": responses}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True, log_level="info")
