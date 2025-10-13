import os
from dotenv import load_dotenv
from langchain_ollama.chat_models import ChatOllama
from mcp_use import MCPAgent, MCPClient

# Load environment variables
load_dotenv()


class OllamaAgent:
    def __init__(
        self,
        mcp_server_url: str | None = None,
        ollama_model: str | None = None,
        ollama_base_url: str | None = None,
        max_steps: int | None = None,
    ):
        """
        Initialize the Ollama MCP Agent.

        Args:
            mcp_server_url: URL of the MCP server SSE endpoint (defaults to MCP_SERVER_URL env var)
            ollama_model: Name of the Ollama model to use (defaults to OLLAMA_MODEL env var)
            ollama_base_url: Base URL of the Ollama server (defaults to OLLAMA_BASE_URL env var)
            max_steps: Maximum number of steps for the agent (defaults to MAX_STEPS env var)
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

    async def initialize(self):
        """Initialize the MCP client and agent."""
        client = MCPClient.from_dict(self.config)
        llm = ChatOllama(model=self.ollama_model, base_url=self.ollama_base_url)
        self.agent = MCPAgent(llm=llm, client=client, max_steps=self.max_steps)

    async def run(self, prompt: str) -> str:
        """
        Run the agent with the given prompt.

        Args:
            prompt: The prompt to send to the agent

        Returns:
            The agent's response
        """
        if self.agent is None:
            await self.initialize()

        return await self.agent.run(prompt)
