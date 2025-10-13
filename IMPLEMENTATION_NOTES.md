# Implementation Notes

## Overview

This document provides technical details about the WebSocket streaming implementation for the Ollama MCP server.

## Architecture Decisions

### 1. Streaming Implementation

**Challenge**: LangChain's `MCPAgent` doesn't natively support streaming responses.

**Solution**: Hybrid approach with two streaming modes:
- **Simple Mode**: Direct streaming from `ChatOllama.astream()` without agent complexity
- **Agent Mode**: Attempts to stream LLM tokens while still supporting MCP tool calling

The agent mode works by:
1. Streaming tokens from the underlying LLM directly
2. Detecting tool calls in the streamed chunks
3. If tools are called, falling back to `agent.run()` to execute them
4. Sending additional MCP responses after tool execution

### 2. Message Protocol

All messages follow a consistent JSON structure:
```json
{
  "type": "ollama" | "mcp" | "tool_call" | "tool_result" | "system" | "error" | "done",
  "data": "<content>"
}
```

**Rationale**: This structure allows the frontend to:
- Distinguish between different response types
- Handle errors gracefully
- Provide visual feedback for tool execution
- Know when streaming is complete

### 3. WebSocket vs. HTTP

**Why WebSocket over Server-Sent Events (SSE)?**
- Full-duplex communication (client can send prompts without reconnecting)
- Better browser support for bidirectional streaming
- More flexible for future features (e.g., cancellation, multi-turn conversations)

### 4. Agent Lifecycle Management

The `StreamingOllamaAgent` is initialized once during server startup via FastAPI's lifespan events. This:
- Reduces latency for first requests
- Ensures the MCP client connection is established
- Shares the agent instance across all WebSocket connections

**Trade-offs**:
- ✅ Lower latency per request
- ✅ Persistent MCP connection
- ⚠️ All connections share the same agent (consider scaling for production)

## Key Components

### `streaming_agent.py`

```python
class StreamingOllamaAgent:
    async def stream_response(self, prompt: str) -> AsyncIterator[dict]:
        """Full agent mode with MCP tool support"""

    async def stream_simple(self, prompt: str) -> AsyncIterator[dict]:
        """Simple LLM streaming without tools"""
```

**Design Notes**:
- Uses `AsyncIterator[dict]` for streaming
- Handles errors gracefully with try/except at multiple levels
- Falls back to non-streaming mode if streaming fails

### `server.py`

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket handler"""
```

**Design Notes**:
- Accepts client messages in a loop (allowing multiple prompts per connection)
- Streams responses using `websocket.send_json()`
- Handles disconnections gracefully
- Logs all operations for debugging

## Streaming Flow

```
Client                 Server                 Ollama                 MCP
  |                      |                      |                     |
  |---{"prompt":"..."}-->|                      |                     |
  |                      |---astream()--------->|                     |
  |                      |                      |                     |
  |<--{"type":"ollama"}--|<----token------------|                     |
  |<--{"type":"ollama"}--|<----token------------|                     |
  |<--{"type":"ollama"}--|<----token------------|                     |
  |                      |                      |                     |
  |                      |   (if tool call detected)                  |
  |                      |------------------------------------------>  |
  |<--{"type":"tool_call"}|                     |                     |
  |                      |<------------------------------------------  |
  |<--{"type":"mcp"}-----|                      |                     |
  |                      |                      |                     |
  |<--{"type":"done"}----|                      |                     |
  |                      |                      |                     |
```

## Error Handling Strategy

1. **Connection Errors**: Caught at WebSocket level, logged, connection closed gracefully
2. **JSON Parsing Errors**: Send error message to client, continue listening
3. **Agent Errors**: Send error message, send "done" marker, continue listening
4. **Streaming Errors**: Fall back to non-streaming mode

## Performance Considerations

### Current Implementation

- **Latency**: First token typically arrives in <500ms (depends on Ollama model)
- **Throughput**: Streams ~10-50 tokens/second (model-dependent)
- **Connection Limit**: Limited by FastAPI/Uvicorn defaults (~1000 concurrent connections)

### Optimization Opportunities

1. **Connection Pooling**: Reuse MCP client connections across requests
2. **Agent Pooling**: Maintain multiple agent instances for concurrent requests
3. **Caching**: Cache common prompts or tool results
4. **Batch Processing**: Process multiple prompts in parallel

### Scaling for Production

For production deployments, consider:

1. **Load Balancing**: Use multiple server instances behind a load balancer
2. **State Management**: Move agent state to Redis or similar
3. **Rate Limiting**: Add rate limits to prevent abuse
4. **Authentication**: Add token-based authentication
5. **Monitoring**: Add metrics for latency, throughput, errors

Example with multiple workers:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

⚠️ **Note**: Multiple workers won't share the in-memory agent. Consider:
- Using a shared agent service (separate process/container)
- Initializing agents per-worker (higher memory usage)
- Using sticky sessions at the load balancer level

## Testing Strategy

### 1. Unit Tests (Future Enhancement)

```python
# test_streaming_agent.py
async def test_stream_simple():
    agent = StreamingOllamaAgent()
    await agent.initialize()

    chunks = []
    async for chunk in agent.stream_simple("Hello"):
        chunks.append(chunk)

    assert any(c["type"] == "ollama" for c in chunks)
    assert chunks[-1]["type"] == "done"
```

### 2. Integration Tests

Use `test_client.py` for manual integration testing:

```bash
# Test simple mode
python test_client.py --prompt "Hello" --mode simple

# Test agent mode
python test_client.py --prompt "Calculate MD5 of 'test'" --mode agent

# Interactive testing
python test_client.py
```

### 3. Load Testing

Use `websockets` library or tools like `k6`:

```javascript
// k6 WebSocket test
import ws from 'k6/ws';

export default function () {
  const url = 'ws://localhost:8000/ws';

  ws.connect(url, function (socket) {
    socket.on('open', () => {
      socket.send(JSON.stringify({
        prompt: 'Hello',
        mode: 'simple'
      }));
    });

    socket.on('message', (data) => {
      const msg = JSON.parse(data);
      if (msg.type === 'done') {
        socket.close();
      }
    });
  });
}
```

## Frontend Integration Best Practices

### 1. Reconnection Logic

The example React client doesn't implement automatic reconnection. For production:

```typescript
function useOllamaStreamWithReconnect(serverUrl: string) {
  const reconnect = useCallback(() => {
    setTimeout(() => {
      // Reconnect logic
    }, 1000);
  }, []);

  useEffect(() => {
    ws.current.onclose = () => {
      if (shouldReconnect) {
        reconnect();
      }
    };
  }, [reconnect]);
}
```

### 2. Message Buffering

For very fast streaming, consider buffering tokens:

```typescript
const [buffer, setBuffer] = useState<string[]>([]);

useEffect(() => {
  const interval = setInterval(() => {
    if (buffer.length > 0) {
      setDisplayText(prev => prev + buffer.join(''));
      setBuffer([]);
    }
  }, 50); // Flush every 50ms

  return () => clearInterval(interval);
}, [buffer]);
```

### 3. Error Recovery

Always provide clear feedback for errors:

```tsx
{error && (
  <div className="error">
    <p>Error: {error}</p>
    <button onClick={clearError}>Dismiss</button>
    <button onClick={retry}>Retry</button>
  </div>
)}
```

## Security Considerations

### Current Implementation

⚠️ **WARNING**: The current implementation is for development only. For production:

1. **No Authentication**: Anyone can connect to the WebSocket
2. **No Rate Limiting**: Susceptible to DoS attacks
3. **No Input Validation**: Accepts any prompt length
4. **CORS Open**: Allows all origins in development

### Production Hardening

1. **Add Authentication**:
```python
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    if not verify_token(token):
        await websocket.close(code=1008)
        return
```

2. **Add Rate Limiting**:
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.websocket("/ws")
@limiter.limit("10/minute")
async def websocket_endpoint(websocket: WebSocket):
    ...
```

3. **Validate Input**:
```python
MAX_PROMPT_LENGTH = 4096

if len(prompt) > MAX_PROMPT_LENGTH:
    await websocket.send_json({
        "type": "error",
        "data": "Prompt too long"
    })
    continue
```

4. **Lock Down CORS**:
```python
CORS_ORIGINS = [
    "https://yourdomain.com",
    "https://app.yourdomain.com"
]
```

## Environment Variables

| Variable | Default | Production Recommendation |
|----------|---------|---------------------------|
| `SERVER_HOST` | `0.0.0.0` | `0.0.0.0` (if behind proxy) or specific IP |
| `SERVER_PORT` | `8000` | Use standard ports (80/443) with reverse proxy |
| `CORS_ORIGINS` | `localhost:*` | Specific production domains only |
| `MAX_STEPS` | `30` | Lower for faster responses, higher for complex tasks |

## Deployment

### Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uv", "run", "python", "server.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  ollama-mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - MCP_SERVER_URL=http://mcp-server:8006/sse
    depends_on:
      - ollama
      - mcp-server

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

  mcp-server:
    # Your MCP server configuration
    ...

volumes:
  ollama-data:
```

## Troubleshooting

### WebSocket Connection Fails

1. Check server is running: `curl http://localhost:8000/health`
2. Check CORS settings in `.env`
3. Verify WebSocket URL (use `ws://` not `http://`)
4. Check browser console for errors

### No Streaming Tokens

1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Test simple mode first: `{"mode": "simple"}`
3. Check server logs for errors
4. Verify model is downloaded: `ollama list`

### Tool Calls Not Working

1. Verify MCP server is running and accessible
2. Check `MCP_SERVER_URL` in `.env`
3. Use agent mode: `{"mode": "agent"}`
4. Check MCP server logs for errors

### Slow Response Times

1. Use smaller/faster Ollama model
2. Reduce `MAX_STEPS` for agent mode
3. Use simple mode for basic queries
4. Check system resources (CPU/RAM/GPU)

## Future Enhancements

1. **Multi-turn Conversations**: Maintain conversation history
2. **Streaming Cancellation**: Allow clients to cancel ongoing requests
3. **Multiple Models**: Support model selection per request
4. **Prompt Templates**: Pre-defined templates for common tasks
5. **Response Caching**: Cache frequent queries
6. **Analytics**: Track usage metrics and performance
7. **File Upload**: Support document/image uploads
8. **Voice Streaming**: Add audio input/output support

## Contributing

When contributing to this project:

1. Run linting: `ruff check . && ruff format .`
2. Test both streaming modes
3. Test WebSocket connection/disconnection
4. Update this document for significant changes
5. Add tests for new features

## Resources

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [LangChain Streaming](https://python.langchain.com/docs/expression_language/streaming)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)
