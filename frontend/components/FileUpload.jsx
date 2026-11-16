"use client";

import { Upload, X, File, CheckCircle2, AlertCircle, Loader2, Database, Trash2, RotateCw } from "lucide-react";
import { useState, useEffect } from "react";
import { documentApi, getErrorMessage } from "@/lib/api";

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".docx"];
const MAX_FILE_SIZE_MB = 20;

// Catch obvious problems before spending an upload on them
const validateFile = (file) => {
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) return `Unsupported type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
  if (file.size === 0) return "File is empty";
  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) return `File too large (max ${MAX_FILE_SIZE_MB}MB)`;
  return null;
};

export default function FileUpload({ isOpen, onClose }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [docError, setDocError] = useState("");
  const [reindexingId, setReindexingId] = useState(null);

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const res = await documentApi.list();
      setDocuments(res.data);
    } catch (e) {
      console.error("Failed to fetch documents", e);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    if (isOpen) fetchDocuments();
  }, [isOpen]);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    setFiles((prev) => [
      ...prev,
      ...selected.map((file) => {
        const error = validateFile(file);
        return {
          file,
          id: Math.random().toString(36).slice(2, 11),
          status: error ? "error" : "pending",
          error,
        };
      }),
    ]);
    // reset input so same file can be re-selected
    e.target.value = "";
  };

  const removeFile = (id) => setFiles((prev) => prev.filter((f) => f.id !== id));

  const handleUpload = async () => {
    setUploading(true);
    const updated = [...files];

    for (let i = 0; i < updated.length; i++) {
      // Skip finished files and ones that failed client-side validation
      if (updated[i].status === "success" || validateFile(updated[i].file)) continue;
      try {
        updated[i] = { ...updated[i], status: "uploading", error: null };
        setFiles([...updated]);
        await documentApi.upload(updated[i].file);
        updated[i] = { ...updated[i], status: "success" };
        setFiles([...updated]);
      } catch (err) {
        updated[i] = { ...updated[i], status: "error", error: getErrorMessage(err, "Upload failed") };
        setFiles([...updated]);
        console.error("Upload failed", err);
      }
    }

    setUploading(false);
    fetchDocuments();
  };

  const handleDeleteDoc = async (doc) => {
    if (!confirm(`Delete "${doc.filename}" from the knowledge base?`)) return;
    setDocError("");
    try {
      await documentApi.delete(doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (e) {
      console.error("Failed to delete document", e);
      setDocError(getErrorMessage(e, "Failed to delete document"));
    }
  };

  const handleReindex = async (id) => {
    setDocError("");
    setReindexingId(id);
    try {
      const res = await documentApi.reindex(id);
      setDocuments((prev) => prev.map((d) => (d.id === id ? res.data : d)));
    } catch (e) {
      console.error("Failed to re-index document", e);
      setDocError(getErrorMessage(e, "Failed to re-index document"));
      fetchDocuments();
    } finally {
      setReindexingId(null);
    }
  };

  if (!isOpen) return null;

  const pendingFiles = files.filter((f) => f.status !== "success" && !validateFile(f.file));

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Database size={18} color="var(--text-secondary)" />
            <div>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Knowledge Base
              </h2>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 1 }}>
                Upload documents to chat with them
              </p>
            </div>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body custom-scrollbar">
          {/* Drop Zone */}
          <div>
            <div className="drop-zone">
              <input
                type="file"
                multiple
                onChange={handleFileChange}
                accept=".pdf,.txt,.docx"
              />
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, pointerEvents: "none" }}>
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 10,
                    background: "var(--bg-panel)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Upload size={20} color="var(--text-secondary)" />
                </div>
                <div>
                  <p style={{ fontSize: "0.9rem", fontWeight: 500, color: "var(--text-primary)" }}>
                    Click to upload
                  </p>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 3 }}>
                    PDF, TXT, DOCX — max 20 MB each
                  </p>
                </div>
              </div>
            </div>

            {/* Queued files */}
            {files.length > 0 && (
              <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                {files.map((f) => (
                  <div key={f.id}>
                  <div className="file-row">
                    <div style={{ display: "flex", alignItems: "center", gap: 10, overflow: "hidden" }}>
                      <File size={16} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--text-primary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {f.file.name}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", flexShrink: 0 }}>
                        {(f.file.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                      {f.status === "uploading" && <Loader2 size={15} color="var(--text-muted)" style={{ animation: "spin 1s linear infinite" }} />}
                      {f.status === "success" && <CheckCircle2 size={15} color="var(--green)" />}
                      {f.status === "error" && <AlertCircle size={15} color="var(--red)" />}
                      {f.status !== "uploading" && (
                        <button className="icon-btn" onClick={() => removeFile(f.id)} disabled={uploading}>
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                  {f.error && (
                    <p style={{ fontSize: "0.75rem", color: "var(--red)", margin: "4px 2px 0" }}>{f.error}</p>
                  )}
                  </div>
                ))}

                <button
                  className="upload-btn"
                  onClick={handleUpload}
                  disabled={uploading || pendingFiles.length === 0}
                  style={{ marginTop: 4 }}
                >
                  {uploading ? (
                    <>
                      <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
                      Uploading…
                    </>
                  ) : (
                    <>
                      <Database size={16} />
                      Upload {pendingFiles.length} file{pendingFiles.length !== 1 ? "s" : ""}
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Existing Documents */}
          <div>
            <p
              style={{
                fontSize: "0.78rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginBottom: 12,
              }}
            >
              Uploaded Documents ({documents.length})
            </p>

            {docError && (
              <p style={{ fontSize: "0.8rem", color: "var(--red)", marginBottom: 10 }}>{docError}</p>
            )}

            {loadingDocs ? (
              <div style={{ display: "flex", justifyContent: "center", padding: 32 }}>
                <Loader2 size={20} color="var(--text-muted)" style={{ animation: "spin 1s linear infinite" }} />
              </div>
            ) : documents.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {documents.map((doc) => (
                  <div key={doc.id} className="doc-card">
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        background: "var(--bg-hover)",
                        border: "1px solid var(--border)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <File size={16} color="var(--text-secondary)" />
                    </div>

                    <div style={{ flex: 1, overflow: "hidden" }}>
                      <p
                        style={{
                          fontSize: "0.875rem",
                          fontWeight: 500,
                          color: "var(--text-primary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {doc.filename}
                      </p>
                      <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                        {doc.chunk_count} chunks · {doc.file_type?.toUpperCase()}
                      </p>
                      {doc.status === "failed" && doc.error && (
                        <p
                          title={doc.error}
                          style={{ fontSize: "0.72rem", color: "var(--red)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                        >
                          {doc.error}
                        </p>
                      )}
                    </div>

                    <span className={doc.status === "ready" ? "badge-ready" : doc.status === "failed" ? "badge-failed" : "badge-pending"}>
                      {doc.status}
                    </span>

                    {doc.status === "failed" && (
                      <button
                        className="icon-btn"
                        onClick={() => handleReindex(doc.id)}
                        disabled={reindexingId === doc.id}
                        title="Retry processing"
                      >
                        <RotateCw size={15} style={reindexingId === doc.id ? { animation: "spin 1s linear infinite" } : undefined} />
                      </button>
                    )}

                    <button className="icon-btn" onClick={() => handleDeleteDoc(doc)} title="Delete document">
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <File size={28} color="var(--border-hover)" />
                <p style={{ fontSize: "0.875rem", fontWeight: 500 }}>No documents uploaded</p>
                <p style={{ fontSize: "0.8rem" }}>Upload files above to build your knowledge base</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
