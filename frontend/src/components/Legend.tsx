// this file is responsible for defining the Legend component
// It provides a visual guide to the colors and symbols used in the memory graph visualization.
// In simple words,
    // it shows what each color and symbol represents in the graph,
    // helping users understand the meaning of different entities, facts, and edges.

import React from "react";
import type { EntityType } from "../api/types";
import { ENTITY_COLORS } from "../lib/colors";

const ENTITY_TYPES: EntityType[] = [
  "Project",
  "Tool",
  "Person",
  "Decision",
  "Preference",
];

export const Legend: React.FC = () => {
  return (
    <div className="graph-overlay legend-overlay">
      <div className="legend-section">
        <span className="legend-title">Entities</span>
        <div className="legend-items-row">
          {ENTITY_TYPES.map((type) => (
            <div key={type} className="legend-item">
              <span
                className="legend-dot"
                style={{ backgroundColor: ENTITY_COLORS[type] }}
              />
              <span className="legend-label">{type}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="legend-section">
        <span className="legend-title">Facts & Edges</span>
        <div className="legend-items-row">
          <div className="legend-item">
            <span className="sample-pill sample-current">current fact</span>
          </div>
          <div className="legend-item">
            <span className="sample-pill sample-replaced">~~replaced fact~~</span>
          </div>
          <div className="legend-item">
            <span className="sample-arrow">➔</span>
            <span className="legend-label">replaces</span>
          </div>
        </div>
      </div>
    </div>
  );
};
