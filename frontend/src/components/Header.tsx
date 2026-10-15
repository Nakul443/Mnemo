// this file is responsible for defining the Header component
// It displays the application title, connection status, pending message count,
// and provides a button to start a new chat session.
// In simple words,
    // it shows the app name and tagline,
    // indicates if the app is connected to the backend,
    // shows how many messages are pending to be sent,
    // and allows users to start a new chat session while keeping the graph memory intact.

import React from "react";
import { StatusBadge } from "./StatusBadge";

export interface HeaderProps {
  connected: boolean;
  pendingCount: number;
  sessionId: string | null;
  onNewSession: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  connected,
  pendingCount,
  sessionId,
  onNewSession,
}) => {
  const shortId = sessionId ? sessionId.slice(0, 8) : "--------";

  return (
    <header className="header">
      <div className="header-left">
        <span className="header-glyph">◆</span>
        <h1 className="header-title">Mnemo</h1>
        <span className="header-tagline">
          Graph memory for AI agents · powered by FalkorDB
        </span>
      </div>

      <div className="header-right">
        <StatusBadge connected={connected} pendingCount={pendingCount} />
        <button
          type="button"
          className="btn-new-session"
          onClick={onNewSession}
          title="Start a new chat session (keeps graph memory intact)"
        >
          New session
        </button>
        <span className="session-id-label" title={sessionId || "No session"}>
          {shortId}
        </span>
      </div>
    </header>
  );
};
