"""
HTTP endpoints router for server information and health checks.
"""

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from streaming_agent import StreamingOllamaAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Server configuration
HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

# Global agent instance (will be set by server.py)
agent: StreamingOllamaAgent | None = None


def set_agent(agent_instance: StreamingOllamaAgent):
    """Set the global agent instance."""
    global agent
    agent = agent_instance


@router.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "Ollama MCP Streaming Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {"websocket": "/ws", "health": "/health", "info": "/info"},
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent_initialized": agent is not None}


@router.get("/info")
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


@router.post("/chat")
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
