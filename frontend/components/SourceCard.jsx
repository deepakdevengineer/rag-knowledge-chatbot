"use client";

import { FileText } from "lucide-react";

export default function SourceCard({ source }) {
  const score = Math.round((source.relevance_score || 0) * 100);

  return (
    <div className="source-chip" title={source.chunk_text}>
      <FileText size={12} />
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
        {source.filename}
      </span>
      <span className="score">{score}%</span>
    </div>
  );
}
