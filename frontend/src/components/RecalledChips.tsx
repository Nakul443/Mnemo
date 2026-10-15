// this file is responsible for defining the RecalledChips component
// It displays a list of recalled facts associated with an assistant message.
// In simple words,
    // it shows a button that toggles the visibility of recalled facts,
    // and when expanded, it displays each fact with its source and text.

import React from "react";
import type { RecalledFact } from "../api/types";

export interface RecalledChipsProps {
  recalled: RecalledFact[];
  onFactHover?: (factId: string | null) => void;
  onFactClick?: (factId: string) => void;
}

export const RecalledChips: React.FC<RecalledChipsProps> = ({
  recalled,
  onFactHover,
  onFactClick,
}) => {
  const [expanded, setExpanded] = React.useState<boolean>(false);

  if (!recalled || recalled.length === 0) {
    return null;
  }

  return (
    <div className="recalled-chips-container">
      <button
        type="button"
        className="recalled-chips-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="toggle-icon">{expanded ? "▾" : "▸"}</span>
        <span>Recalled {recalled.length} fact{recalled.length > 1 ? "s" : ""}</span>
      </button>

      {expanded && (
        <div className="recalled-chips-list">
          {recalled.map((fact) => (
            <div
              key={fact.id}
              className="recalled-chip-row"
              onMouseEnter={() => onFactHover?.(fact.id)}
              onMouseLeave={() => onFactHover?.(null)}
              onClick={() => onFactClick?.(fact.id)}
            >
              <span className={`chip-source-tag source-${fact.source}`}>
                {fact.source}
              </span>
              <span className="chip-fact-text">{fact.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
