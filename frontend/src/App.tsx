// this file is responsible for defining the main App component
// It serves as the entry point of the application, orchestrating the chat interface and graph visualization.
// In simple words,
    // it manages the overall layout of the app,
    // handles session management and state for chat messages and graph data,
    // and coordinates interactions between the chat panel and graph panel.


import React, { useRef, useState } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { GraphPanel } from "./components/GraphPanel";
import { Header } from "./components/Header";
import { useChat } from "./hooks/useChat";
import { useGraphPolling } from "./hooks/useGraphPolling";
import { useSession } from "./hooks/useSession";
import "./styles.css";

export const App: React.FC = () => {
  const { sessionId, newSession } = useSession();

  const [highlightedFactId, setHighlightedFactId] = useState<string | null>(
    null
  );
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [recalledFactIds, setRecalledFactIds] = useState<string[]>([]);
  const [matchedEntityIds, setMatchedEntityIds] = useState<string[]>([]);

  const recallTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleRecalled = (factIds: string[], entityIds: string[]) => {
    setRecalledFactIds(factIds);
    setMatchedEntityIds(entityIds);

    if (recallTimerRef.current) {
      clearTimeout(recallTimerRef.current);
    }
    recallTimerRef.current = setTimeout(() => {
      setRecalledFactIds([]);
      setMatchedEntityIds([]);
    }, 4000);
  };

  const { graph, pendingCount, connected, refreshNow, enterFastMode } =
    useGraphPolling();

  const {
    messages,
    pending,
    lastError,
    recalledBySeq,
    sendMessage,
    retryMessage,
    clearMessages,
  } = useChat(sessionId, handleRecalled, enterFastMode);

  const handleNewSession = async () => {
    const newId = await newSession();
    if (newId) {
      clearMessages();
      setRecalledFactIds([]);
      setMatchedEntityIds([]);
      setSelectedNodeId(null);
      refreshNow();
    }
  };

  return (
    <div className="app-container">
      <Header
        connected={connected}
        pendingCount={pendingCount}
        sessionId={sessionId}
        onNewSession={handleNewSession}
      />

      <main className="main-content">
        <ChatPanel
          messages={messages}
          pending={pending}
          lastError={lastError}
          recalledBySeq={recalledBySeq}
          onSend={sendMessage}
          onRetry={retryMessage}
          onFactHover={setHighlightedFactId}
          onFactClick={setSelectedNodeId}
        />

        <GraphPanel
          snapshot={graph}
          recalledFactIds={recalledFactIds}
          matchedEntityIds={matchedEntityIds}
          highlightedFactId={highlightedFactId}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
        />
      </main>
    </div>
  );
};

export default App;
