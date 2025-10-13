# Quick Start Guide

Get your Ollama MCP Streaming Server up and running in 5 minutes.

## Prerequisites Check

```bash
# 1. Check Python version (need 3.13+)
python --version

# 2. Check if Ollama is running
curl http://localhost:11434/api/tags

# 3. Check if uv is installed
uv --version

# If uv is not installed:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation (30 seconds)

```bash
# 1. Install dependencies
uv sync

# 2. Copy environment file
cp .env.example .env

# 3. (Optional) Edit .env if you need different settings
# nano .env
```

## Start the Server (10 seconds)

```bash
# Start the WebSocket server
python server.py

# Or with uv:
uv run python server.py
```

You should see:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Initializing Streaming Ollama Agent...
INFO:     Agent initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Test the Server (1 minute)

### Option 1: Test Client (Easiest)

```bash
# In a new terminal, run the test client
python test_client.py

# Or test with a specific prompt:
python test_client.py --prompt "What is 2+2?" --mode simple
```

### Option 2: HTTP Health Check

```bash
# Check server health
curl http://localhost:8000/health

# Get server info
curl http://localhost:8000/info
```

### Option 3: WebSocket Test with wscat

```bash
# Install wscat (one time)
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws

# Send a message (paste this):
{"prompt": "Hello, how are you?", "mode": "simple"}

# You'll see streaming responses!
```

## Common Issues

### "Connection refused" on port 11434

**Problem**: Ollama is not running

**Solution**:
```bash
# Start Ollama
ollama serve

# Or on macOS with Ollama app:
# Just open the Ollama app
```

### "Model not found"

**Problem**: Ollama model not downloaded

**Solution**:
```bash
# Check available models
ollama list

# Pull your model
ollama pull llama2

# Update .env with the model name
echo "OLLAMA_MODEL=llama2" >> .env
```

### "MCP connection failed"

**Problem**: MCP server is not running (this is optional for simple mode)

**Solution**:
- Use `"mode": "simple"` in requests (doesn't need MCP)
- Or start your MCP server at the configured URL
- Or comment out MCP initialization in `streaming_agent.py` for testing

### Port 8000 already in use

**Solution**:
```bash
# Use a different port
SERVER_PORT=8001 python server.py

# Or kill the process using port 8000
lsof -ti:8000 | xargs kill
```

## Next Steps

### 1. Try Both Modes

**Simple Mode** (direct LLM streaming, no tools):
```bash
python test_client.py --prompt "Tell me a joke" --mode simple
```

**Agent Mode** (with MCP tools, if MCP server is running):
```bash
python test_client.py --prompt "Calculate MD5 of 'hello'" --mode agent
```

### 2. Integrate with Your React App

Copy `example_react_client.tsx` to your React project:

```tsx
import { ChatInterface } from './example_react_client';

function App() {
  return <ChatInterface serverUrl="ws://localhost:8000/ws" />;
}
```

### 3. Test the HTTP Endpoint

```bash
# Test non-streaming HTTP endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Python?"}'
```

### 4. Interactive Testing

```bash
# Start interactive mode
python test_client.py

# Then type your prompts:
You: What is the speed of light?
# (Wait for response)

You: /agent Calculate MD5 of 'test'
# (Uses agent mode)

You: /simple Tell me a joke
# (Uses simple mode)
```

## Development Workflow

```bash
# 1. Start the server in one terminal
python server.py

# 2. In another terminal, run the test client
python test_client.py

# 3. Make changes to server.py or streaming_agent.py

# 4. Server auto-reloads (using uvicorn --reload)

# 5. Test again with the client
```

## Production Deployment

```bash
# 1. Create .env for production
cp .env.example .env
nano .env  # Set production values

# 2. Run with production settings
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4

# 3. Or use gunicorn with uvicorn workers
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Testing Checklist

- [ ] Server starts without errors
- [ ] `/health` endpoint returns `{"status": "healthy"}`
- [ ] `/info` endpoint returns server configuration
- [ ] WebSocket connection succeeds
- [ ] Simple mode streaming works
- [ ] Agent mode works (if MCP server is running)
- [ ] Multiple requests work
- [ ] Disconnection/reconnection works
- [ ] Error handling works (try invalid JSON)

## Performance Tips

1. **Use Simple Mode for Basic Queries**: Faster, no MCP overhead
2. **Reduce MAX_STEPS**: Lower values = faster responses
3. **Use Smaller Models**: Try `llama2:7b` instead of `llama2:70b`
4. **Enable GPU**: If available, Ollama will use it automatically

## Getting Help

1. **Check Logs**: Server logs appear in the terminal
2. **Read README.md**: Full documentation
3. **Read IMPLEMENTATION_NOTES.md**: Technical details
4. **Test with wscat**: Isolate WebSocket issues
5. **Check Ollama**: `ollama list` and `ollama ps`

## Example Session

```bash
# Terminal 1: Start server
$ python server.py
INFO:     Started server process [12345]
INFO:     Initializing Streaming Ollama Agent...
INFO:     Agent initialized successfully
INFO:     Uvicorn running on http://0.0.0.0:8000

# Terminal 2: Test client
$ python test_client.py --prompt "Count to 5" --mode simple
Connecting to ws://localhost:8000/ws...
Connected! Sending prompt: 'Count to 5' (mode: simple)

Streaming response:
------------------------------------------------------------
1
2
3
4
5

[Response completed]
------------------------------------------------------------
```

## What's Next?

- ✅ Server is running
- ✅ WebSocket is working
- ✅ Streaming is functional

Now you can:
1. Build your React frontend using `example_react_client.tsx`
2. Customize the streaming behavior in `streaming_agent.py`
3. Add authentication and rate limiting for production
4. Deploy with Docker (see IMPLEMENTATION_NOTES.md)

Happy coding! 🚀
