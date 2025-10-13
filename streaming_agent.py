import os
import uuid
from typing import AsyncIterator

from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_ollama.chat_models import ChatOllama
from mcp_use import MCPAgent, MCPClient

# Load environment variables
load_dotenv()


class StreamingOllamaAgent:
    """
    A streaming-capable Ollama MCP Agent that yields real-time responses.

    This agent extends the basic OllamaAgent to support streaming responses
    from both the Ollama model and MCP server interactions.
    """

    def __init__(
        self,
        mcp_server_url: str | None = None,
        ollama_model: str | None = None,
        ollama_base_url: str | None = None,
        max_steps: int | None = None,
    ):
        """
        Initialize the Streaming Ollama MCP Agent.

        Args:
            mcp_server_url: URL of the MCP server SSE endpoint
            ollama_model: Name of the Ollama model to use
            ollama_base_url: Base URL of the Ollama server
            max_steps: Maximum number of steps for the agent
        """
        self.mcp_server_url = mcp_server_url or os.getenv(
            "MCP_SERVER_URL", "http://localhost:8006/sse"
        )
        self.ollama_model = ollama_model or os.getenv(
            "OLLAMA_MODEL", "skaiform-assistant:gpt-oss"
        )
        self.ollama_base_url = ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.max_steps = max_steps or int(os.getenv("MAX_STEPS", "30"))

        self.config = {"mcpServers": {"http": {"url": self.mcp_server_url}}}
        self.agent = None
        self.mcp_client = None
        self.llm = None

    async def initialize(self):
        """Initialize the MCP client, LLM, and agent."""
        self.mcp_client = MCPClient.from_dict(self.config)
        self.llm = ChatOllama(model=self.ollama_model, base_url=self.ollama_base_url)
        self.agent = MCPAgent(
            llm=self.llm, client=self.mcp_client, max_steps=self.max_steps
        )

    async def stream_response(self, prompt: str, message_id: str | None = None) -> AsyncIterator[dict]:
        """
        Stream the agent's response token by token.

        Args:
            prompt: The prompt to send to the agent
            message_id: Optional message ID to group related chunks (generated if not provided)

        Yields:
            Dictionary messages in the format:
            {"message_id": "...", "type": "ollama" | "mcp" | "tool_call" | "tool_result" | "done", "data": "..."}
        """
        if self.agent is None:
            await self.initialize()

        # Generate message ID if not provided
        if message_id is None:
            message_id = str(uuid.uuid4())

        # Send initial processing message
        yield {"message_id": message_id, "type": "system", "data": "Processing your request..."}

        try:
            # IMPORTANT: We must use self.agent.run() to enable tool calling
            # Streaming directly from self.llm bypasses the MCPAgent's tool execution logic

            # Run the agent (this handles tool calls properly)
            result = await self.agent.run(prompt)

            # Stream the result in chunks for better UX
            chunk_size = 50
            for i in range(0, len(result), chunk_size):
                chunk = result[i : i + chunk_size]
                yield {"message_id": message_id, "type": "ollama", "data": chunk}

            # Send completion message
            yield {"message_id": message_id, "type": "done", "data": "Response completed"}

        except Exception as e:
            yield {"message_id": message_id, "type": "error", "data": f"Error processing request: {str(e)}"}
            yield {"message_id": message_id, "type": "done", "data": "Response completed with errors"}

    async def stream_simple(
        self, prompt: str, buffer_size: int = 5, accumulate: bool = False, message_id: str | None = None
    ) -> AsyncIterator[dict]:
        """
        Stream responses from Ollama without MCP agent complexity.

        This is a simpler streaming method that focuses on raw LLM streaming
        without the agent loop and tool calling.

        Args:
            prompt: The prompt to send to the model
            buffer_size: Number of chunks to buffer before yielding (default: 5)
            accumulate: If True, accumulate all chunks and send as one message (default: False)
            message_id: Optional message ID to group related chunks (generated if not provided)

        Yields:
            Dictionary messages with streaming tokens
        """
        if self.llm is None:
            await self.initialize()

        # Generate message ID if not provided
        if message_id is None:
            message_id = str(uuid.uuid4())

        try:
            messages = [HumanMessage(content=prompt)]
            buffer = []

            async for chunk in self.llm.astream(messages):
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    buffer.append(chunk.content)

                    # If not accumulating, yield when buffer reaches size
                    if not accumulate and len(buffer) >= buffer_size:
                        yield {"message_id": message_id, "type": "ollama", "data": "".join(buffer)}
                        buffer = []

            # Yield remaining buffered content (or all content if accumulating)
            if buffer:
                yield {"message_id": message_id, "type": "ollama", "data": "".join(buffer)}

            yield {"message_id": message_id, "type": "done", "data": "Response completed"}

        except Exception as e:
            yield {"message_id": message_id, "type": "error", "data": f"Error: {str(e)}"}
            yield {"message_id": message_id, "type": "done", "data": "Response completed with errors"}
