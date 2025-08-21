import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import katex from "katex";
import "katex/dist/katex.min.css";
import "./ChatWindow.css";

// Renders step reasoning, removes **, handles LaTeX expressions and headers.
const renderMarkdownLine = (line, i) => {
  let cleanedLine = line.trim();
  if (!cleanedLine) return null;

  // Remove ** bold markers from the line
  cleanedLine = cleanedLine.replace(/\*\*/g, "");

  // Convert <<...>> safely into LaTeX $$...$$
  cleanedLine = cleanedLine.replace(/<<([^>]+)>>/g, (match, content) => {
    const cleanContent = content
      .replace(/<<.*?>>/g, "")
      .trim()
      .replace(/[^0-9+\-*/().\s]/g, "");
    return cleanContent ? `$$${cleanContent}$$` : match;
  });

  // Headers
  if (cleanedLine.startsWith("#### ")) return <h4 key={i}>{cleanedLine.replace("#### ", "")}</h4>;
  if (cleanedLine.startsWith("### ")) return <h3 key={i}>{cleanedLine.replace("### ", "")}</h3>;
  if (cleanedLine.startsWith("## ")) return <h2 key={i}>{cleanedLine.replace("## ", "")}</h2>;
  if (cleanedLine.startsWith("# ")) return <h1 key={i}>{cleanedLine.replace("# ", "")}</h1>;

  // LaTeX rendering with fallback
  const parts = cleanedLine.split(/(\$\$.*?\$\$)/g);
  return (
    <div key={i}>
      {parts.map((part, j) => {
        if (part.startsWith("$$") && part.endsWith("$$")) {
          let latexContent = part.slice(2, -2).trim();
          if (!latexContent) return null;
          try {
            return (
              <span
                key={j}
                dangerouslySetInnerHTML={{
                  __html: katex.renderToString(latexContent, { throwOnError: false, displayMode: true }),
                }}
              />
            );
          } catch (e) {
            return <span key={j}>{latexContent}</span>;
          }
        }
        return <span key={j}>{part}</span>;
      })}
    </div>
  );
};

const ChatWindow = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [modal, setModal] = useState({ open: false, msgIndex: null });
  const [correctedText, setCorrectedText] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await Promise.race([
        axios.post("http://localhost:8000/ask", { query: input }),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Request timed out")), 10000)
        ),
      ]);

      const reasoningText = res.data.reasoning || "No reasoning available.";
      let finalAnswer = res.data.answer || "";

      // If final answer is purely numeric, show as plain text
      if (/^[-+]?[0-9]*\.?[0-9]+$/.test(finalAnswer.trim())) {
        finalAnswer = finalAnswer.trim();
      } else {
        // Extract number from reasoning if missing or not numeric
        const numMatch = reasoningText.match(/[-+]?[0-9]*\.?[0-9]+/g);
        if (numMatch && numMatch.length > 0) {
          finalAnswer = numMatch[numMatch.length - 1];
        }
      }

      const botMsg = {
        sender: "bot",
        reasoning: reasoningText,
        finalAnswer,
        source: res.data.source || "Unknown",
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `⚠️ Error: ${err.response?.data?.error || err.message || "Server issue"}`,
          source: "Error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (msgIndex, correct, correctedSolution = "") => {
    const botMsg = messages[msgIndex];
    const userMsg = messages[msgIndex - 1] || { text: "" };
    try {
      const res = await axios.post("http://localhost:8000/feedback", {
        query: userMsg.text,
        response: botMsg.finalAnswer || botMsg.text,
        correct,
        corrected_solution: correctedSolution,
      });
      setToast(res.data.success ? "✅ Feedback submitted!" : `⚠️ ${res.data.error || "Feedback failed"}`);
    } catch {
      setToast("⚠️ Error submitting feedback.");
    }
  };

  const openIncorrectModal = (msgIndex) => {
    setModal({ open: true, msgIndex });
    setCorrectedText("");
  };

  const submitIncorrect = () => {
    handleFeedback(modal.msgIndex, false, correctedText);
    setModal({ open: false, msgIndex: null });
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <div className="app-wrapper">
      {toast && <div className="toast-message">{toast}</div>}
      <div className="chat-wrapper">
        <div className="chat-header">MathAgent</div>
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.sender}`}>
              <div className="message-text">
                {msg.sender === "bot" && msg.reasoning && (
                  <div className="reasoning">
                    {msg.reasoning.split("\n").map((line, i) => renderMarkdownLine(line, i))}
                  </div>
                )}
                {msg.sender === "bot" && msg.finalAnswer && (
                  <div className="final-answer">
                    ✅ Final Answer:{" "}
                    {(() => {
                      const ans = msg.finalAnswer.trim();
                      if (/^[-+]?[0-9]*\.?[0-9]+$/.test(ans)) {
                        return <span>{ans}</span>;
                      }
                      try {
                        return (
                          <span
                            dangerouslySetInnerHTML={{
                              __html: katex.renderToString(ans, { throwOnError: false }),
                            }}
                          />
                        );
                      } catch {
                        return <span>{ans}</span>;
                      }
                    })()}
                  </div>
                )}
                {msg.sender === "user" && <div>{msg.text}</div>}
              </div>
              {msg.sender === "bot" && msg.source && (
                <span className={`source-badge source-${msg.source.replace("/", "-")}`}>
                  {msg.source}
                </span>
              )}
              {msg.sender === "bot" &&
                !["Guardrail", "Error"].includes(msg.source) && (
                  <div className="feedback-buttons">
                    <button onClick={() => handleFeedback(idx, true)}>Correct ✅</button>
                    <button onClick={() => openIncorrectModal(idx)}>Incorrect ❌</button>
                  </div>
                )}
            </div>
          ))}
          {loading && (
            <div className="message bot">
              <i>MathAgent is thinking...</i>
            </div>
          )}
          <div ref={messagesEndRef} style={{ height: 0, margin: 0, padding: 0 }} />
        </div>
        <div className="chat-input">
          <input
            type="text"
            placeholder="Ask a math question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <button onClick={handleSend} disabled={!input.trim() || loading}>
            Send
          </button>
        </div>
      </div>
      {modal.open && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>What went wrong?</h3>
            <textarea
              placeholder="Provide the correct solution..."
              value={correctedText}
              onChange={(e) => setCorrectedText(e.target.value)}
              rows={6}
            />
            <div className="modal-buttons">
              <button onClick={submitIncorrect} disabled={!correctedText.trim()}>
                Submit ✅
              </button>
              <button onClick={() => setModal({ open: false, msgIndex: null })}>
                Cancel ❌
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatWindow;
