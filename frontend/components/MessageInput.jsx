"use client";

import { useState } from "react";
import { Send } from "lucide-react";

export default function MessageInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState("");

  const submit = () => {
    if (!message.trim() || disabled) return;
    onSendMessage(message.trim());
    setMessage("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleChange = (e) => {
    setMessage(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  return (
    <div className="chat-input-wrap">
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div className="chat-input-box">
          <textarea
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Message Assistant…"
            rows={1}
            style={{ height: "24px" }}
            disabled={disabled}
          />
          <button
            className="send-btn"
            onClick={submit}
            disabled={!message.trim() || disabled}
            aria-label="Send message"
          >
            <Send size={16} strokeWidth={2.5} />
          </button>
        </div>
        <p style={{ textAlign: "center", fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 8 }}>
          AI can make mistakes. Always verify important information.
        </p>
      </div>
    </div>
  );
}
