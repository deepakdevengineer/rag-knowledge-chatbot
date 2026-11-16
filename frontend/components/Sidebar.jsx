"use client";

import { MessageSquare, Plus, Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import { useState, useEffect } from "react";
import { historyApi } from "@/lib/api";

export default function Sidebar({
  activeSessionId,
  onSelectSession,
  onNewChat,
  isMobile,
  isOpen,
  setIsOpen,
  refreshTrigger,
}) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchSessions = async () => {
    try {
      const res = await historyApi.listSessions();
      setSessions(res.data);
    } catch (e) {
      console.error("Failed to fetch sessions", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [activeSessionId, refreshTrigger]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    try {
      await historyApi.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) onNewChat();
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  const sidebarWidth = isOpen ? 260 : 56;

  return (
    <>
      <div
        style={{
          width: isMobile ? (isOpen ? "100%" : 0) : sidebarWidth,
          minWidth: isMobile ? undefined : sidebarWidth,
          background: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          transition: "width 0.25s ease, min-width 0.25s ease",
          position: isMobile ? "fixed" : "relative",
          inset: isMobile ? "0 auto 0 0" : undefined,
          zIndex: isMobile ? 40 : undefined,
          flexShrink: 0,
        }}
      >
        {/* Header row */}
        <div
          style={{
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: isOpen ? "space-between" : "center",
            padding: isOpen ? "0 12px 0 16px" : "0",
            borderBottom: "1px solid var(--border)",
            flexShrink: 0,
          }}
        >
          {isOpen && (
            <span style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--text-primary)", whiteSpace: "nowrap" }}>
              Assistant
            </span>
          )}
          <button
            className="icon-btn"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle sidebar"
            style={{ marginLeft: isOpen ? 0 : "auto", marginRight: isOpen ? 0 : "auto" }}
          >
            {isOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>
        </div>

        {/* New Chat */}
        <div style={{ padding: "12px 8px 8px" }}>
          {isOpen ? (
            <button className="new-chat-btn" onClick={onNewChat}>
              <Plus size={16} />
              <span>New chat</span>
            </button>
          ) : (
            <button
              className="icon-btn"
              onClick={onNewChat}
              style={{ width: "100%", justifyContent: "center", padding: "8px 0" }}
              title="New chat"
            >
              <Plus size={18} />
            </button>
          )}
        </div>

        {/* Sessions */}
        <div style={{ flex: 1, overflowY: "auto", padding: "4px 8px" }} className="custom-scrollbar">
          {isOpen && (
            <p
              style={{
                fontSize: "0.7rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                padding: "8px 4px 6px",
              }}
            >
              Recent
            </p>
          )}

          {loading
            ? Array(5)
                .fill(0)
                .map((_, i) => (
                  <div
                    key={i}
                    style={{
                      height: 36,
                      borderRadius: 8,
                      background: "var(--bg-panel)",
                      marginBottom: 4,
                      opacity: 0.4,
                    }}
                  />
                ))
            : sessions.map((session) => (
                <div
                  key={session.id}
                  className={`sidebar-item${activeSessionId === session.id ? " active" : ""}`}
                  onClick={() => onSelectSession(session.id)}
                  style={{ justifyContent: isOpen ? undefined : "center" }}
                  title={!isOpen ? session.title : undefined}
                >
                  <MessageSquare size={15} style={{ flexShrink: 0 }} />
                  {isOpen && (
                    <>
                      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                        {session.title}
                      </span>
                      <button
                        className="icon-btn"
                        style={{ opacity: 0, pointerEvents: "none" }}
                        onClick={(e) => handleDelete(e, session.id)}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.opacity = "1";
                          e.currentTarget.style.pointerEvents = "auto";
                        }}
                        title="Delete chat"
                      >
                        <Trash2 size={13} />
                      </button>
                    </>
                  )}
                </div>
              ))}

          {!loading && sessions.length === 0 && isOpen && (
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", padding: "16px 4px", textAlign: "center" }}>
              No chats yet
            </p>
          )}
        </div>
      </div>

      {/* Mobile backdrop */}
      {isMobile && isOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            zIndex: 30,
            backdropFilter: "blur(4px)",
          }}
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
