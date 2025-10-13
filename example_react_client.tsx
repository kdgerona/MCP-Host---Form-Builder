/**
 * Example React component for connecting to the Ollama MCP Streaming Server
 *
 * This file demonstrates how to:
 * 1. Create a WebSocket connection
 * 2. Send prompts to the backend
 * 3. Receive and display streaming responses
 * 4. Handle different message types (ollama, mcp, tool_call, etc.)
 *
 * Usage:
 *   import { ChatInterface } from './example_react_client';
 *
 *   function App() {
 *     return <ChatInterface serverUrl="ws://localhost:8000/ws" />;
 *   }
 */

import { useEffect, useState, useRef, useCallback } from "react";

// Message type definitions
interface StreamMessage {
  type:
    | "ollama"
    | "mcp"
    | "tool_call"
    | "tool_result"
    | "system"
    | "error"
    | "done";
  data: string | object;
}

interface ToolCallData {
  name: string;
  args: Record<string, unknown>;
}

// Custom hook for managing WebSocket connection and streaming
export function useOllamaStream(serverUrl: string = "ws://localhost:8000/ws") {
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    console.log(`Connecting to ${serverUrl}...`);
    ws.current = new WebSocket(serverUrl);

    ws.current.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      setError(null);
    };

    ws.current.onmessage = (event) => {
      try {
        const message: StreamMessage = JSON.parse(event.data);

        setMessages((prev) => [...prev, message]);

        // Stop streaming indicator when done
        if (message.type === "done") {
          setIsStreaming(false);
        }

        // Handle errors
        if (message.type === "error") {
          setError(message.data as string);
        }
      } catch (err) {
        console.error("Error parsing message:", err);
        setError("Failed to parse server message");
      }
    };

    ws.current.onerror = (event) => {
      console.error("WebSocket error:", event);
      setError("WebSocket connection error");
      setIsConnected(false);
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      setIsStreaming(false);
    };

    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [serverUrl]);

  const sendPrompt = useCallback(
    (prompt: string, mode: "agent" | "simple" = "agent") => {
      if (!ws.current || !isConnected) {
        setError("Not connected to server");
        return;
      }

      // Clear previous messages and errors
      setMessages([]);
      setError(null);
      setIsStreaming(true);

      // Send prompt to server
      const message = { prompt, mode };
      ws.current.send(JSON.stringify(message));
    },
    [isConnected]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isConnected,
    isStreaming,
    error,
    sendPrompt,
    clearMessages,
  };
}

// Main chat interface component
export function ChatInterface({ serverUrl = "ws://localhost:8000/ws" }) {
  const {
    messages,
    isConnected,
    isStreaming,
    error,
    sendPrompt,
    clearMessages,
  } = useOllamaStream(serverUrl);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<"agent" | "simple">("simple");
  const [showDebug, setShowDebug] = useState(false);
  const responseRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [messages]);

  // Accumulate ollama and mcp tokens into response text
  const responseText = messages
    .filter((m) => m.type === "ollama" || m.type === "mcp")
    .map((m) => m.data)
    .join("");

  // Extract system messages
  const systemMessages = messages.filter((m) => m.type === "system");

  // Extract tool calls
  const toolCalls = messages
    .filter((m) => m.type === "tool_call")
    .map((m) => m.data as ToolCallData);

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedInput = input.trim();
    if (trimmedInput && isConnected && !isStreaming) {
      sendPrompt(trimmedInput, mode);
      setInput("");
    }
  };

  return (
    <div
      className="chat-interface"
      style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}
    >
      <h1>Ollama MCP Streaming Chat</h1>

      {/* Connection status */}
      <div
        className="status-bar"
        style={{
          marginBottom: "20px",
          padding: "10px",
          background: "#f5f5f5",
          borderRadius: "4px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "20px" }}>{isConnected ? "🟢" : "🔴"}</span>
          <span>{isConnected ? "Connected" : "Disconnected"}</span>
          {isStreaming && <span>⏳ Streaming...</span>}
        </div>
        <div style={{ fontSize: "12px", color: "#666", marginTop: "5px" }}>
          Server: {serverUrl}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div
          className="error"
          style={{
            padding: "10px",
            background: "#fee",
            color: "#c00",
            borderRadius: "4px",
            marginBottom: "20px",
          }}
        >
          ⚠️ Error: {error}
        </div>
      )}

      {/* Response display */}
      <div
        ref={responseRef}
        className="response"
        style={{
          minHeight: "300px",
          maxHeight: "500px",
          overflow: "auto",
          padding: "15px",
          background: "#fff",
          border: "1px solid #ddd",
          borderRadius: "4px",
          marginBottom: "20px",
          fontFamily: "monospace",
          whiteSpace: "pre-wrap",
          wordWrap: "break-word",
        }}
      >
        {responseText || (
          <span style={{ color: "#999" }}>
            {isConnected
              ? "Enter a prompt to get started..."
              : "Waiting for connection..."}
          </span>
        )}
        {isStreaming && (
          <span className="cursor" style={{ animation: "blink 1s infinite" }}>
            ▊
          </span>
        )}
      </div>

      {/* Tool calls display (if any) */}
      {toolCalls.length > 0 && (
        <div
          className="tool-calls"
          style={{
            marginBottom: "20px",
            padding: "10px",
            background: "#f0f8ff",
            borderRadius: "4px",
          }}
        >
          <h3 style={{ margin: "0 0 10px 0", fontSize: "14px" }}>
            🔧 Tool Calls
          </h3>
          {toolCalls.map((tool, i) => (
            <div key={i} style={{ fontSize: "12px", marginBottom: "5px" }}>
              <strong>{tool.name}</strong>: {JSON.stringify(tool.args)}
            </div>
          ))}
        </div>
      )}

      {/* System messages (collapsible) */}
      {systemMessages.length > 0 && (
        <div className="system-messages" style={{ marginBottom: "20px" }}>
          <button
            onClick={() => setShowDebug(!showDebug)}
            style={{
              padding: "5px 10px",
              background: "#e0e0e0",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            {showDebug ? "▼" : "▶"} System Messages ({systemMessages.length})
          </button>
          {showDebug && (
            <div
              style={{
                marginTop: "10px",
                padding: "10px",
                background: "#f5f5f5",
                borderRadius: "4px",
                fontSize: "12px",
              }}
            >
              {systemMessages.map((msg, i) => (
                <div key={i} style={{ marginBottom: "5px" }}>
                  {msg.data as string}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "10px" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={!isConnected || isStreaming}
          style={{
            flex: 1,
            padding: "10px",
            fontSize: "14px",
            border: "1px solid #ddd",
            borderRadius: "4px",
          }}
        />

        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as "agent" | "simple")}
          disabled={isStreaming}
          style={{
            padding: "10px",
            fontSize: "14px",
            border: "1px solid #ddd",
            borderRadius: "4px",
          }}
        >
          <option value="simple">Simple</option>
          <option value="agent">Agent</option>
        </select>

        <button
          type="submit"
          disabled={!isConnected || isStreaming || !input.trim()}
          style={{
            padding: "10px 20px",
            fontSize: "14px",
            background: isConnected && !isStreaming ? "#007bff" : "#ccc",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: isConnected && !isStreaming ? "pointer" : "not-allowed",
          }}
        >
          Send
        </button>

        <button
          type="button"
          onClick={clearMessages}
          disabled={isStreaming}
          style={{
            padding: "10px 20px",
            fontSize: "14px",
            background: "#6c757d",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: isStreaming ? "not-allowed" : "pointer",
          }}
        >
          Clear
        </button>
      </form>

      {/* Mode description */}
      <div style={{ marginTop: "10px", fontSize: "12px", color: "#666" }}>
        <strong>Mode:</strong>{" "}
        {mode === "simple"
          ? "Simple streaming (direct LLM)"
          : "Agent mode (with MCP tools)"}
      </div>

      {/* CSS for blinking cursor animation */}
      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

// Example: Minimal usage
export function MinimalExample() {
  const { messages, sendPrompt, isConnected } = useOllamaStream();

  const response = messages
    .filter((m) => m.type === "ollama")
    .map((m) => m.data)
    .join("");

  return (
    <div>
      <div>{response}</div>
      <button onClick={() => sendPrompt("Hello!")} disabled={!isConnected}>
        Send
      </button>
    </div>
  );
}

// Export types for use in other components
export type { StreamMessage, ToolCallData };
