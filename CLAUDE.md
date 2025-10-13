# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complete Python backend that integrates **Ollama LLMs** with **Model Context Protocol (MCP)** servers, providing real-time streaming responses via WebSocket to React frontends. The project uses FastAPI for the WebSocket server, LangChain for LLM integration, and mcp-use for MCP protocol support.

## Architecture

**Core Components:**

### 1. WebSocket Server (server.py)
- **FastAPI application** with WebSocket endpoint at `/ws`
- **HTTP endpoints**: `/health`, `/info`, `/chat` for monitoring and testing
- **CORS middleware** configured for React frontend integration
- **Lifespan management** for agent initialization on startup
- **Real-time streaming** of LLM responses to connected clients

### 2. Streaming Agent (streaming_agent.py)
- **StreamingOllamaAgent class**: Core agent that handles streaming responses
  - `stream_response()`: Full agent mode with MCP tool calling support
  - `stream_simple()`: Simple LLM streaming without agent complexity
- **Hybrid streaming approach**: Attempts to stream tokens while supporting tool calls
- **Error handling**: Multiple fallback strategies for robustness

### 3. Original Agent (ollama_agent.py)
- **OllamaAgent class**: Non-streaming agent implementation
- Used as reference and for CLI testing
- Simpler interface: just `run(prompt)` method

### 4. Test Utilities
- **test_client.py**: Python WebSocket test client with interactive mode
- **example_react_client.tsx**: Complete React/TypeScript implementation example
- **main.py**: CLI test script for basic agent testing

**Message Flow:**

```
React Frontend
     ↓ (WebSocket)
FastAPI Server (/ws endpoint)
     ↓
StreamingOllamaAgent
     ↓
ChatOllama (LangChain) ← → Ollama Server
     ↓
MCPClient (mcp-use) ← → MCP Server
```

**Key Dependencies:**

- `fastapi`: Web framework and WebSocket server
- `uvicorn`: ASGI server with auto-reload
- `websockets`: WebSocket client library (for testing)
- `langchain-ollama`: LangChain integration for Ollama models
- `langchain-core`: Core LangChain functionality
- `mcp-use`: Client library for MCP protocol
- `python-dotenv`: Environment variable management
- `httpx`: Async HTTP client
- `ruff`: Python linter/formatter

## Development Commands

**Environment Setup:**
```bash
# Install dependencies (requires Python 3.13+)
uv sync

# Create .env file
cp .env.example .env
```

**Running the WebSocket server:**
```bash
# Development mode (auto-reload)
python server.py

# Or with uv
uv run python server.py

# Production mode
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

**Testing:**
```bash
# Interactive WebSocket test client
python test_client.py

# Test with specific prompt
python test_client.py --prompt "Hello!" --mode simple

# Test original agent (non-streaming)
python main.py

# Health check
curl http://localhost:8000/health
```

**Linting:**
```bash
ruff check .
ruff format .
```

## Configuration

All configuration is via environment variables (`.env` file):

```bash
# MCP Server Configuration
MCP_SERVER_URL=http://localhost:8006/sse

# Ollama Configuration
OLLAMA_MODEL=skaiform-assistant:gpt-oss  # Any Ollama model
OLLAMA_BASE_URL=http://localhost:11434

# Agent Configuration
MAX_STEPS=30  # Maximum reasoning steps for agent

# WebSocket Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173  # React dev servers
```

## API Reference

### WebSocket Endpoint: `/ws`

**Client → Server:**
```json
{
  "prompt": "Your question here",
  "mode": "simple" | "agent"  // optional, default: "agent"
}
```

**Server → Client:**
```json
{
  "type": "ollama" | "mcp" | "tool_call" | "system" | "error" | "done",
  "data": "content or object"
}
```

**Streaming Modes:**
- `simple`: Direct LLM streaming, faster, no tool support
- `agent`: Full agent with MCP tools, slower but more capable

### HTTP Endpoints

- `GET /`: Server info and available endpoints
- `GET /health`: Health check (returns agent status)
- `GET /info`: Detailed server configuration
- `POST /chat`: Non-streaming test endpoint (accumulates all responses)

## Project Structure

```
mcp-ollama/
├── server.py              # FastAPI WebSocket server ⭐ MAIN ENTRY POINT
├── streaming_agent.py     # Streaming agent implementation ⭐ CORE LOGIC
├── ollama_agent.py        # Original non-streaming agent
├── main.py                # CLI test script
├── test_client.py         # Python WebSocket test client
├── example_react_client.tsx  # React integration example
├── pyproject.toml         # Python dependencies
├── .env.example           # Configuration template
├── .env                   # Your configuration (create this)
├── README.md              # User documentation
├── QUICKSTART.md          # Quick start guide
├── IMPLEMENTATION_NOTES.md  # Technical implementation details
└── CLAUDE.md              # This file
```

## Important Implementation Details

### Streaming Strategy

The `StreamingOllamaAgent` uses a hybrid approach because `MCPAgent` doesn't natively support streaming:

1. **Simple Mode**: Direct streaming from `ChatOllama.astream()` - fastest, no tools
2. **Agent Mode**:
   - Stream tokens from underlying LLM
   - Detect tool calls in streamed chunks
   - Fall back to `agent.run()` if tools are needed
   - Send MCP results after tool execution

### Error Handling

Multiple layers of error handling:
- WebSocket connection errors → close gracefully, log
- JSON parsing errors → send error message, continue
- Agent errors → send error message + done marker, continue
- Streaming errors → fall back to chunked non-streaming mode

### Agent Lifecycle

- Agent is initialized ONCE during server startup (FastAPI lifespan)
- Shared across all WebSocket connections (consider implications for scaling)
- MCP client connection is persistent

### Message Protocol

All messages follow consistent structure:
```json
{"type": "<message_type>", "data": "<content>"}
```

This allows frontend to:
- Distinguish between LLM tokens and MCP responses
- Display tool execution progress
- Handle errors gracefully
- Know when streaming completes

## Testing Strategy

1. **Server Health**: `curl http://localhost:8000/health`
2. **WebSocket Connection**: `python test_client.py`
3. **Simple Streaming**: `python test_client.py --mode simple --prompt "Hello"`
4. **Agent Mode**: `python test_client.py --mode agent --prompt "Calculate MD5 of 'test'"`
5. **Interactive**: `python test_client.py` (then type prompts)

## Common Issues

### "Connection refused" on WebSocket
- Server not running → `python server.py`
- Wrong port → check `SERVER_PORT` in `.env`

### "Agent not initialized"
- Wait for startup to complete
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Check MCP server is accessible (for agent mode)

### Slow streaming
- Use simple mode for faster responses
- Reduce `MAX_STEPS`
- Use smaller/faster Ollama model

### Tool calls not working
- Verify MCP server is running
- Use agent mode (not simple)
- Check `MCP_SERVER_URL` configuration

## React Integration

See `example_react_client.tsx` for complete implementation. Key points:

```tsx
// 1. Use custom hook for WebSocket management
const { messages, sendPrompt, isConnected } = useOllamaStream('ws://localhost:8000/ws');

// 2. Accumulate ollama tokens
const response = messages
  .filter(m => m.type === 'ollama')
  .map(m => m.data)
  .join('');

// 3. Send prompts
sendPrompt('Hello!', 'simple');
```

## Development Workflow

1. Start server: `python server.py` (auto-reloads on changes)
2. In another terminal: `python test_client.py` (for testing)
3. Make changes to `streaming_agent.py` or `server.py`
4. Server auto-reloads
5. Test again with client

## Production Considerations

- **Authentication**: Add token-based auth to WebSocket endpoint
- **Rate Limiting**: Prevent abuse (e.g., using slowapi)
- **Input Validation**: Limit prompt length, sanitize input
- **CORS**: Lock down to specific production domains
- **Scaling**: Consider agent pooling or separate agent service
- **Monitoring**: Add metrics for latency, errors, throughput
- **Logging**: Use structured logging (JSON logs)

See `IMPLEMENTATION_NOTES.md` for detailed production guidance.

## Documentation

- **README.md**: User-facing documentation, API reference, React examples
- **QUICKSTART.md**: Get started in 5 minutes
- **IMPLEMENTATION_NOTES.md**: Technical deep-dive, architecture decisions, scaling
- **CLAUDE.md**: This file - Claude Code guidance

## Important Context

- This is now a production-ready WebSocket server, not just a CLI tool
- Streaming is implemented with fallback strategies for robustness
- The codebase assumes Ollama is running (required) and MCP server (optional for simple mode)
- All code follows async/await patterns for proper concurrency
- Type hints are used throughout for better IDE support
- Error handling is comprehensive with multiple fallback strategies
