"""
FastAPI WebSocket server for streaming Ollama + MCP responses to React frontend.

This server provides:
- WebSocket endpoint for real-time streaming communication
- Health check endpoint
- Server info endpoint
- CORS support for React frontend integration
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from streaming_agent import StreamingOllamaAgent
from routers import http_router, websocket_router
from routers import http as http_module
from routers import websocket as websocket_module

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Initializing Streaming Ollama Agent...")
    agent = StreamingOllamaAgent()
    await agent.initialize()
    logger.info("Agent initialized successfully")

    # Set agent in routers
    http_module.set_agent(agent)
    websocket_module.set_agent(agent)

    yield

    # Shutdown
    logger.info("Shutting down server...")
    http_module.set_agent(None)
    websocket_module.set_agent(None)


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

# Include routers
app.include_router(http_router)
app.include_router(websocket_router)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True, log_level="info")
