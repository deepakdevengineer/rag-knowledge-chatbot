"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import MessageInput from "@/components/MessageInput";
import FileUpload from "@/components/FileUpload";
import { historyApi, chatApi } from "@/lib/api";
import { Database, LayoutPanelLeft } from "lucide-react";

const parseSources = (raw) => {
  try {
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [currentSources, setCurrentSources] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [sessionTitle, setSessionTitle] = useState("Assistant");

  useEffect(() => {
    const check = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) setIsSidebarOpen(false);
    };
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      historyApi
        .getSession(activeSessionId)
        .then((res) => {
          setSessionTitle(res.data.title || "Chat");
          setMessages(
            res.data.messages.map((m) => ({
              role: m.role,
              content: m.content,
              sources: parseSources(m.sources),
            }))
          );
        })
        .catch(console.error);
    } else {
      setMessages([]);
      setSessionTitle("Assistant");
    }
  }, [activeSessionId, refreshTrigger]);

  const handleSendMessage = async (query) => {
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);
    setStreamingAnswer("");
    setCurrentSources([]);

    chatApi.streamMessage(
      query,
      activeSessionId,
      (token) => {
        setLoading(false);
        setStreamingAnswer((prev) => prev + token);
      },
      (sources) => {
        setCurrentSources(sources);
      },
      (sessionId, finalAnswer, finalSources) => {
        setLoading(false);
        setActiveSessionId(sessionId);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: finalAnswer, sources: finalSources },
        ]);
        setStreamingAnswer("");
        setCurrentSources([]);
        setRefreshTrigger((n) => n + 1);
      },
      (error) => {
        console.error("Chat error", error);
        setLoading(false);
        setStreamingAnswer("");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ An error occurred while connecting to the AI: ${error.message}. Please make sure the backend is running and your API key is valid.`,
          },
        ]);
      }
    );
  };

  const chatMessages =
    streamingAnswer
      ? [...messages, { role: "assistant", content: streamingAnswer, sources: currentSources }]
      : messages;


  return (
    <main
      style={{
        display: "flex",
        height: "100vh",
        background: "var(--bg-main)",
        overflow: "hidden",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id);
          if (isMobile) setIsSidebarOpen(false);
        }}
        onNewChat={() => setActiveSessionId(null)}
        isMobile={isMobile}
        refreshTrigger={refreshTrigger}
      />

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* Top bar */}
        <header className="top-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {!isSidebarOpen && !isMobile && (
              <button
                className="icon-btn"
                onClick={() => setIsSidebarOpen(true)}
                title="Open sidebar"
              >
                <LayoutPanelLeft size={18} />
              </button>
            )}
            <span style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--text-primary)" }}>
              {activeSessionId ? sessionTitle : "Assistant"}
            </span>
          </div>

          <button className="kb-btn" onClick={() => setIsUploadOpen(true)}>
            <Database size={15} />
            <span>Knowledge Base</span>
          </button>
        </header>

        {/* Chat */}
        <ChatWindow messages={chatMessages} loading={loading && !streamingAnswer} />

        {/* Input */}
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={loading || !!streamingAnswer}
        />
      </div>

      {/* KB Modal */}
      <FileUpload isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
    </main>
  );
}
