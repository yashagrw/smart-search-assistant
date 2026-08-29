import React, { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const App = () => {
  const [messages, setMessages] = useState([
    { 
      text: "Hello! How can I help you today?", 
      sender: "bot",
      metrics: null 
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const sessionId = useRef(`session_${Math.random().toString(36).substring(2, 9)}`);

  const handleSend = async () => {
    if (!inputText.trim()) return;

    const userMessage = { text: inputText, sender: "user" };
    setMessages((prev) => [...prev, userMessage]);

    const currentInput = inputText;
    setInputText("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: "gemini-2.5-flash",
          query: currentInput,
          system_prompt: `You are an intelligent database assistant.
          
CRITICAL INSTRUCTIONS:
1. Analyze the user's request carefully. If they ask for multiple pieces of information (like projects AND orders), you CAN and SHOULD use multiple tools to gather all necessary data before answering.
2. Once you have all the data from the tools, combine it into a single, comprehensive final answer.

FORMATTING RULES:
- Use **bold** for important information like file numbers, names, statuses
- Use ### for main headers and sections
- Use bullet points (- ) for lists and organized information
- Use code blocks for IDs, technical details, and exact values
- Use > blockquotes for important notes or highlights
- Add appropriate spacing and structure for readability
- Convert statuses (like 'order_processing', 'in_escrow') to human-readable formats (e.g., 'Order Processing', 'In Escrow').`,
          allow_search: false,
          thread_id: sessionId.current,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();

      // Backend returns { answer: "...", metrics: {...} } or string fallback
      const botAnswer = typeof data === "object" && data.answer ? data.answer : (data || "No response received.");
      const botMetrics = typeof data === "object" && data.metrics ? data.metrics : null;

      const botMessage = {
        text: botAnswer,
        sender: "bot",
        metrics: botMetrics
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error calling /ask API:", error);
      const errorMessage = {
        text: "Sorry, something went wrong. Please try again.",
        sender: "bot",
        metrics: null
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <h1 className="chat-header">Agentic AI Search Assistant Demo</h1>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.sender}`}>
            <div className={`message-bubble ${message.sender}`}>
              {message.sender === "bot" ? (
                <div>
                  <div className="markdown-content">
                    <ReactMarkdown>{message.text}</ReactMarkdown>
                  </div>
                  
                  {/* Performance Telemetry Badges */}
                  {message.metrics && (
                    <div style={{
                      marginTop: "12px",
                      paddingTop: "8px",
                      borderTop: "1px dashed rgba(255,255,255,0.2)",
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "6px",
                      fontSize: "11px"
                    }}>
                      <span style={{ background: "#2d3748", color: "#63b3ed", padding: "2px 8px", borderRadius: "12px" }}>
                        ⏱️ Total: {(message.metrics.total_latency_ms / 1000).toFixed(2)}s
                      </span>
                      {message.metrics.total_accumulated_tokens > 0 && (
                        <span style={{ background: "#2d3748", color: "#f6e05e", padding: "2px 8px", borderRadius: "12px" }}>
                          🪙 Tokens: {message.metrics.total_accumulated_tokens}
                        </span>
                      )}
                      {message.metrics.node_latencies && message.metrics.node_latencies
                        .filter((item) => item.tool)
                        .map((t, idx) => (
                          <span key={idx} style={{ background: "#1a365d", color: "#90cdf4", padding: "2px 8px", borderRadius: "12px" }}>
                            ⚡ {t.tool}: {t.latency_ms}ms
                          </span>
                        ))
                      }
                    </div>
                  )}
                </div>
              ) : (
                message.text
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="loading-message">
            <div className="loading-bubble">Thinking...</div>
          </div>
        )}
      </div>

      <div className="input-container">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Type your message..."
          className="message-input"
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !inputText.trim()}
          className="send-button"
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
};

export default App;