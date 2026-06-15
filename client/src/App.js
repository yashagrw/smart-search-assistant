import { useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const App = () => {
  const [messages, setMessages] = useState([
    { text: "Hello! How can I help you today?", sender: "bot" },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!inputText.trim()) return;

    // Add user message
    const userMessage = { text: inputText, sender: "user" };
    setMessages((prev) => [...prev, userMessage]);

    const currentInput = inputText;
    setInputText("");
    setIsLoading(true);

    try {
      // Call your /ask API
      // TEMP: Switched frontend API route from /ask/v1 to /ask during backend stabilization
      const response = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model_name: "gemini-2.5-flash",
          query: currentInput,
          system_prompt: `CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:
1. When you need data, make ONE tool call only
2. As soon as you get the tool result, IMMEDIATELY format it using the formatting rules below and respond
3. DO NOT analyze, interpret, or make additional tool calls
4. DO NOT ask follow-up questions or request more information
5. The tool result IS your final answer - just format it nicely

FORMATTING RULES:
- Use **bold** for important information like file numbers, names, statuses
- Use ### for main headers and sections
- Use bullet points (- ) for lists and organized information
- Use code blocks for IDs, technical details, and exact values
- Use > blockquotes for important notes or highlights
- Add appropriate spacing and structure for readability
- For any status or enum value (like 'order_processing', 'in_escrow', etc.), convert it to a human-readable format by replacing underscores with spaces and capitalizing each word (e.g., 'order_processing' → 'Order Processing').

STOP CONDITION: After formatting the tool result, you MUST stop and return the response. Do not continue processing..`,
          allow_search: false,
          thread_id: null,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();

      // Add bot response
      const botMessage = {
        text: data || "Sorry, I couldn't process that.",
        sender: "bot",
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error calling /ask API:", error);
      const errorMessage = {
        text: "Sorry, something went wrong. Please try again.",
        sender: "bot",
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

      {/* Messages Container */}
      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.sender}`}>
            <div className={`message-bubble ${message.sender}`}>
              {message.sender === "bot" ? (
                <div className="markdown-content">
                  <ReactMarkdown>{message.text}</ReactMarkdown>
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

      {/* Input Container */}
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