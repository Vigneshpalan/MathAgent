import React, { useState } from "react";
import axios from "axios";

const DebugChat = () => {
  const [query, setQuery] = useState("");
  const [backendResponse, setBackendResponse] = useState(null);
  const [error, setError] = useState("");

  const handleSend = async () => {
    setError("");
    setBackendResponse(null);
    try {
      const res = await axios.post("http://localhost:8000/ask", { query });
      console.log("API response:", res.data);
      setBackendResponse(res.data);
    } catch (err) {
      setError(err.message || "Request failed");
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h3>Debug Chat</h3>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask math question"
        style={{ width: "300px" }}
      />
      <button onClick={handleSend} disabled={!query.trim()}>
        Send
      </button>
      <hr />
      {error && (
        <div style={{ color: "red" }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      {backendResponse && (
        <div>
          <h4>Full Backend Response</h4>
          <pre>{JSON.stringify(backendResponse, null, 2)}</pre>

          <h4>Reasoning</h4>
          <pre>{backendResponse.reasoning || "No reasoning"}</pre>

          <h4>Final Answer</h4>
          <pre>{backendResponse.answer || "No answer"}</pre>
        </div>
      )}
    </div>
  );
};

export default DebugChat;
