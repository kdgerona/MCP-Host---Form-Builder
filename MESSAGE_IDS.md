# Message IDs for Response Grouping

## Overview

All WebSocket messages now include a `message_id` field to help frontends group streaming chunks that belong to the same response.

## Message Format

### Client → Server

```json
{
  "prompt": "Your question here",
  "mode": "agent",  // optional, default: "agent"
  "message_id": "client-generated-uuid"  // optional
}
```

- **`message_id`** (optional): Client can provide their own UUID for tracking
- If not provided, the server will generate one automatically

### Server → Client

```json
{
  "message_id": "unique-identifier",
  "type": "ollama",
  "data": "response content"
}
```

- **`message_id`**: Unique identifier shared across all chunks of the same response
- All streaming chunks for a single response will have the **same** `message_id`
- The `done` message will also include the same `message_id`

## Example Flow

### Request
```json
{
  "prompt": "Explain quantum computing",
  "mode": "simple"
}
```

### Response Stream
```json
{"message_id": "abc-123", "type": "ollama", "data": "Quantum"}
{"message_id": "abc-123", "type": "ollama", "data": " computing"}
{"message_id": "abc-123", "type": "ollama", "data": " leverages"}
{"message_id": "abc-123", "type": "ollama", "data": " quantum"}
{"message_id": "abc-123", "type": "ollama", "data": " mechanics..."}
{"message_id": "abc-123", "type": "done", "data": "Response completed"}
```

All chunks share the same `message_id`: `"abc-123"`

## React/TypeScript Integration

### Updated Message Interface

```typescript
interface Message {
  message_id: string;
  type: 'ollama' | 'mcp' | 'tool_call' | 'system' | 'error' | 'done';
  data: string | object;
}
```

### Grouping Messages by ID

```typescript
import { useState, useEffect } from 'react';

interface GroupedMessage {
  message_id: string;
  content: string;
  type: 'assistant' | 'system';
  isComplete: boolean;
}

function useGroupedMessages(messages: Message[]) {
  const [grouped, setGrouped] = useState<Map<string, GroupedMessage>>(new Map());

  useEffect(() => {
    const newGrouped = new Map(grouped);

    messages.forEach((msg) => {
      const existing = newGrouped.get(msg.message_id) || {
        message_id: msg.message_id,
        content: '',
        type: msg.type === 'system' ? 'system' : 'assistant',
        isComplete: false,
      };

      if (msg.type === 'ollama') {
        existing.content += msg.data;
      } else if (msg.type === 'done') {
        existing.isComplete = true;
      }

      newGrouped.set(msg.message_id, existing);
    });

    setGrouped(newGrouped);
  }, [messages]);

  return Array.from(grouped.values());
}
```

### Usage Example

```typescript
function ChatComponent() {
  const { messages } = useOllamaStream();
  const groupedMessages = useGroupedMessages(messages);

  return (
    <div className="chat">
      {groupedMessages.map((msg) => (
        <div key={msg.message_id} className={`message ${msg.type}`}>
          <div className="content">{msg.content}</div>
          {!msg.isComplete && <span className="cursor">▋</span>}
        </div>
      ))}
    </div>
  );
}
```

## Benefits

1. **Proper Grouping**: Frontend can easily group all chunks belonging to the same response
2. **Separate Bubbles**: Greeting and user responses appear in separate message bubbles
3. **Client Tracking**: Clients can provide their own IDs for request/response correlation
4. **Concurrent Requests**: Support for multiple concurrent requests (each with unique ID)

## Implementation Details

### Server Behavior

1. **Greeting**: Server generates unique ID for greeting message on connection
2. **User Messages**:
   - Uses client-provided `message_id` if present
   - Generates UUID if client doesn't provide one
3. **All Chunks**: Every chunk in the response stream includes the same `message_id`
4. **Error Messages**: Errors get their own unique `message_id`

### Agent Methods

Both streaming methods support `message_id` parameter:

```python
# Streaming agent methods
await agent.stream_simple(prompt, message_id="optional-id")
await agent.stream_response(prompt, message_id="optional-id")
```

If `message_id` is not provided, the agent generates one using `uuid.uuid4()`.

## Migration Guide

### Old Format (No message_id)
```typescript
// Before: Accumulate all 'ollama' messages
const response = messages
  .filter((m) => m.type === 'ollama')
  .map((m) => m.data)
  .join('');
```

### New Format (With message_id)
```typescript
// After: Group by message_id first
const messagesById = new Map<string, string>();

messages.forEach((msg) => {
  if (msg.type === 'ollama') {
    const current = messagesById.get(msg.message_id) || '';
    messagesById.set(msg.message_id, current + msg.data);
  }
});

// Now you have separate messages
const messagesArray = Array.from(messagesById.entries()).map(
  ([id, content]) => ({ id, content })
);
```

## Testing

Test the message IDs using the Python test client:

```bash
python test_client.py
```

You'll see the `message_id` in the logs:
```
INFO:__main__:Sending greeting from LLM (message_id: abc-123-def-456)...
INFO:__main__:Processing prompt in 'simple' mode (message_id: xyz-789-ghi-012): Hello...
```

Each response will have all chunks sharing the same ID.
