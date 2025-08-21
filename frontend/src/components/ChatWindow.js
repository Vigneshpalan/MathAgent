import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import katex from "katex";
import "katex/dist/katex.min.css";
import "./ChatWindow.css";

// Render a line with headers and LaTeX
const renderMarkdownLine = (line, i) => {
  const cleanedLine = line.replace(/<<.*?>>/g, "").trim();
  if (!cleanedLine) return null;

  // Headers
  if (cleanedLine.startsWith("#### ")) return <h4 key={i}>{cleanedLine.replace("#### ", "")}</h4>;
  if (cleanedLine.startsWith("### ")) return <h3 key={i}>{cleanedLine.replace("### ", "")}</h3>;
  if (cleanedLine.startsWith("## ")) return <h2 key={i}>{cleanedLine.replace("## ", "")}</h2>;
  if (cleanedLine.startsWith("# ")) return <h1 key={i}>{cleanedLine.replace("# ", "")}</h1>;

  // LaTeX rendering
  const parts = cleanedLine.split(/(\$\$.*?\$\$)/g);
  return (
    <div key={i}>
      {parts.map((part, j) => {
        if (part.startsWith("$$") && part.endsWith("$$")) {
          try {
            const latexContent = part.slice(2, -2).trim();
            if (!latexContent) return null;
            return (
              <span
                key={j}
                dangerouslySetInnerHTML={{
                  __html: katex.renderToString(latexContent, { throwOnError: false }),
                }}
              />
            );
          } catch (e) {
            return <span key={j}>{part}</span>;
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
      const res = await axios.post("http://localhost:8000/ask", { query: input });
      const reasoningText = res.data.reasoning || "";
      const finalAnswer = res.data.answer || "";

      // Take first non-empty line
      const firstAnswerLine = finalAnswer.split("\n").find((line) => line.trim()) || "";

      const botMsg = {
        sender: "bot",
        reasoning: reasoningText,
        finalAnswer: firstAnswerLine,
        source: res.data.source,
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Error contacting server.", source: "Error" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (msgIndex, correct, correctedSolution = "") => {
    const botMsg = messages[msgIndex];
    const userMsg = messages[msgIndex - 1] || { text: "" };

    try {
      await axios.post("http://localhost:8000/feedback", {
        query: userMsg.text,
        response: botMsg.finalAnswer || botMsg.text,
        correct,
        corrected_solution: correctedSolution,
      });
      setToast("✅ Feedback submitted!");
    } catch (err) {
      console.error(err);
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
                    {renderMarkdownLine(
                      msg.reasoning.split("\n").find((line) => line.trim()) || "",
                      0
                    )}
                  </div>
                )}

                {msg.sender === "bot" && msg.finalAnswer && (
                  <div className="final-answer">
                    ✅ Final Answer:{" "}
                    {/^[-+0-9*/().\s]+$/.test(msg.finalAnswer.replace(/\$\$/g, "").trim()) ? (
                      // Render math with KaTeX
                      <span
                        dangerouslySetInnerHTML={{
                          __html: katex.renderToString(
                            msg.finalAnswer.replace(/\$\$/g, "").trim(),
                            { throwOnError: false }
                          ),
                        }}
                      />
                    ) : (
                      // Render text as-is
                      <span>{msg.finalAnswer.replace(/^\d+[:.]?\s*/, "").trim()}</span>
                    )}
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
