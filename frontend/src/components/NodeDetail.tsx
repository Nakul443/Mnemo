// this file is responsible for defining the NodeDetail component
// It displays detailed information about a selected node (fact or entity) in the memory graph.
// In simple words,
    // it shows all relevant details about a fact or entity when a user clicks on it in the graph,
    // including its status, associated facts or entities, and timestamps for creation and replacement.

import React from "react";
import type { GraphSnapshot } from "../api/types";
import {
  type ExtendedNode,
  entitiesForFact,
  factsForEntity,
  replacedBy,
  replaces,
} from "../lib/graphData";
import { relativeTime } from "../lib/time";

export interface NodeDetailProps {
  node: ExtendedNode | null;
  snapshot: GraphSnapshot | null;
  now: number;
  onClose: () => void;
  onSelectNodeById: (nodeId: string) => void;
}

export const NodeDetail: React.FC<NodeDetailProps> = ({
  node,
  snapshot,
  now,
  onClose,
  onSelectNodeById,
}) => {
  if (!node || !snapshot) return null;

  const isFact = node.kind === "fact";

  // Fact drawer details
  const replacingFact = isFact ? replacedBy(node.id, snapshot) : null;
  const replacedFactsList = isFact ? replaces(node.id, snapshot) : [];
  const connectedEntities = isFact ? entitiesForFact(node.id, snapshot) : [];

  // Entity drawer details
  const entityFacts = !isFact ? factsForEntity(node.id, snapshot) : [];
  const currentEntityFacts = entityFacts.filter((f) => f.status === "current");
  const replacedEntityFacts = entityFacts.filter((f) => f.status === "replaced");

  return (
    <div className="node-detail-drawer">
      <div className="drawer-header">
        <div className="drawer-badges">
          {isFact ? (
            <span
              className={`status-pill ${
                node.status === "current" ? "pill-green" : "pill-muted"
              }`}
            >
              {node.status === "current" ? "Current Fact" : "Replaced Fact"}
            </span>
          ) : (
            <span className="status-pill pill-accent">
              {node.entity_type || "Entity"}
            </span>
          )}
        </div>
        <button
          type="button"
          className="btn-close-drawer"
          onClick={onClose}
          title="Close (Esc)"
        >
          ✕
        </button>
      </div>

      <div className="drawer-body">
        <h2 className="drawer-node-title">{node.label}</h2>

        {isFact ? (
          <div className="drawer-section">
            <div className="detail-field">
              <span className="field-label">From your message</span>
              <div className="source-message-quote">
                {node.source_message
                  ? `“${node.source_message}”`
                  : "Source message unavailable"}
              </div>
            </div>

            <div className="detail-meta-row">
              <div className="meta-item">
                <span className="meta-label">Learned:</span>
                <span className="meta-value">
                  {relativeTime(node.created_at, now)}
                </span>
              </div>
              {node.replaced_at && (
                <div className="meta-item">
                  <span className="meta-label">Replaced:</span>
                  <span className="meta-value">
                    {relativeTime(node.replaced_at, now)}
                  </span>
                </div>
              )}
            </div>

            {replacingFact && (
              <div className="detail-field margin-top">
                <span className="field-label">Replaced by</span>
                <div
                  className="interactive-row-link"
                  onClick={() => onSelectNodeById(replacingFact.id)}
                >
                  <span className="link-bullet">➔</span>
                  <span className="link-text">{replacingFact.label}</span>
                </div>
              </div>
            )}

            {replacedFactsList.length > 0 && (
              <div className="detail-field margin-top">
                <span className="field-label">Replaces</span>
                <div className="interactive-list">
                  {replacedFactsList.map((f) => (
                    <div
                      key={f.id}
                      className="interactive-row-link"
                      onClick={() => onSelectNodeById(f.id)}
                    >
                      <span className="link-bullet">↩</span>
                      <span className="link-text strikethrough">{f.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {connectedEntities.length > 0 && (
              <div className="detail-field margin-top">
                <span className="field-label">About</span>
                <div className="about-entity-chips">
                  {connectedEntities.map((ent) => (
                    <button
                      key={ent.id}
                      type="button"
                      className="about-chip"
                      onClick={() => onSelectNodeById(ent.id)}
                    >
                      {ent.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="drawer-section">
            <div className="detail-field">
              <span className="field-label">Associated Facts ({entityFacts.length})</span>
              <div className="interactive-list">
                {currentEntityFacts.map((f) => (
                  <div
                    key={f.id}
                    className="interactive-row-link"
                    onClick={() => onSelectNodeById(f.id)}
                  >
                    <span className="link-bullet">•</span>
                    <span className="link-text">{f.label}</span>
                  </div>
                ))}
                {replacedEntityFacts.map((f) => (
                  <div
                    key={f.id}
                    className="interactive-row-link muted-row"
                    onClick={() => onSelectNodeById(f.id)}
                  >
                    <span className="link-bullet">•</span>
                    <span className="link-text strikethrough">{f.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
