import { useState, useRef } from "react" ;
import ReactMarkdown from "react-markdown";
import "./App.css";

const App = () => {
  const [messages, setMessages] = useState([
    { text: "Hello! How can I help you today?", sender: "bot" },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  // Generate a random unique ID for this browser tab session (only runs once)
  const sessionId = useRef(`session_${Math.random().toString(36).substring(2, 9)}`);

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
          system_prompt:  `You are an intelligent database assistant.
          
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
          //Send the unique session ID instead of null
          thread_id: sessionId.current,
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