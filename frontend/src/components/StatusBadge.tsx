// this file is responsible for defining the StatusBadge component
// It displays the connection status and pending message count in the header.
// In simple words,
    // it shows if the app is connected to the backend,
    // indicates if there are any pending extraction jobs,
    // and provides visual feedback on the current state of the memory graph.

import React from "react";

export interface StatusBadgeProps {
  connected: boolean;
  pendingCount: number;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  connected,
  pendingCount,
}) => {
  if (!connected) {
    return (
      <div className="status-badge status-badge-disconnected" title="API or FalkorDB unreachable">
        <span className="status-dot status-dot-red" />
        <span>Disconnected</span>
      </div>
    );
  }

  if (pendingCount > 0) {
    return (
      <div className="status-badge status-badge-updating" title={`${pendingCount} extraction job(s) pending`}>
        <span className="status-spinner" />
        <span>Updating memory…</span>
      </div>
    );
  }

  return (
    <div className="status-badge status-badge-idle" title="Memory graph up to date">
      <span className="status-dot status-dot-green" />
      <span>Memory idle</span>
    </div>
  );
};
