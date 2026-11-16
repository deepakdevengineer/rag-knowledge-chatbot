"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Database } from "lucide-react";
import SourceCard from "./SourceCard";

const TypingDots = () => (
  <div style={{ display: "flex", gap: 4, padding: "4px 0", alignItems: "center" }}>
    <div className="typing-dot" />
    <div className="typing-dot" />
    <div className="typing-dot" />
  </div>
);

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 20px",
          gap: 16,
          color: "var(--text-muted)",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: "var(--bg-panel)",
            border: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Database size={22} color="var(--text-secondary)" />
        </div>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
            How can I help you today?
          </p>
          <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", maxWidth: 360 }}>
            Ask questions about your uploaded documents. Upload files via Knowledge Base.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ flex: 1, overflowY: "auto", padding: "24px 20px 8px" }}
      className="custom-scrollbar"
    >
      <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            {msg.role === "user" ? (
              <div className="message-user-bubble">{msg.content}</div>
            ) : (
              <div style={{ display: "flex", gap: 12, maxWidth: "100%", alignItems: "flex-start" }}>
                {/* AI Avatar */}
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 8,
                    background: "var(--bg-panel)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    marginTop: 2,
                  }}
                >
                  <Bot size={15} color="var(--text-secondary)" />
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* AI text */}
                  <div className="message-ai-content">
                    <ReactMarkdown
                      components={{
                        code({ node, inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || "");
                          if (!inline && match) {
                            return (
                              <pre>
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              </pre>
                            );
                          }
                          return (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          );
                        },
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {msg.sources.map((src, si) => (
                        <SourceCard key={si} source={src} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 8,
                background: "var(--bg-panel)",
                border: "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Bot size={15} color="var(--text-secondary)" />
            </div>
            <TypingDots />
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
