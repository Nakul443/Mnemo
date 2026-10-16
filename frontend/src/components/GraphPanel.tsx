// this file is responsible for defining the GraphPanel component
// It visualizes the memory graph using a force-directed layout and provides interactive features.
// In simple words,
    // it shows the memory graph as a network of nodes and links,
    // allows users to interact with the graph by clicking on nodes or links,
    // and provides controls to fit the graph to view, toggle history visibility, and view node details.

import React, { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";
import type { GraphSnapshot } from "../api/types";
import { COLORS } from "../lib/colors";
import { drawNode } from "../lib/draw";
import {
  type ExtendedLink,
  type ExtendedNode,
  filterHistory,
  mergeSnapshot,
  snapshotChanged,
} from "../lib/graphData";
import { Legend } from "./Legend";
import { NodeDetail } from "./NodeDetail";

export interface GraphPanelProps {
  snapshot: GraphSnapshot | null;
  recalledFactIds?: string[];
  matchedEntityIds?: string[];
  highlightedFactId?: string | null;
  selectedNodeId?: string | null;
  onSelectNode?: (nodeId: string | null) => void;
  onFactSelect?: (factId: string) => void;
}

export const GraphPanel: React.FC<GraphPanelProps> = ({
  snapshot,
  recalledFactIds = [],
  matchedEntityIds = [],
  highlightedFactId = null,
  selectedNodeId: controlledSelectedNodeId = null,
  onSelectNode,
  onFactSelect,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);

  const [dimensions, setDimensions] = useState({ width: 600, height: 600 });
  const [showHistory, setShowHistory] = useState<boolean>(true);
  const [internalSelectedNodeId, setInternalSelectedNodeId] = useState<string | null>(null);
  const [nodes, setNodes] = useState<ExtendedNode[]>([]);
  const [links, setLinks] = useState<ExtendedLink[]>([]);
  const [isAnimating, setIsAnimating] = useState<boolean>(false);

  const selectedNodeId = controlledSelectedNodeId ?? internalSelectedNodeId;

  const setSelectedNode = (nodeId: string | null) => {
    setInternalSelectedNodeId(nodeId);
    onSelectNode?.(nodeId);
  };

  const prevSnapshotRef = useRef<GraphSnapshot | null>(null);
  const recalledSet = useRef<Set<string>>(new Set());
  const animTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const triggerAnimationWindow = (durationMs: number = 4000) => {
    setIsAnimating(true);
    if (animTimerRef.current) {
      clearTimeout(animTimerRef.current);
    }
    animTimerRef.current = setTimeout(() => {
      setIsAnimating(false);
    }, durationMs);
  };

  // Update recalled set & trigger animation window
  useEffect(() => {
    const combined = [...recalledFactIds, ...matchedEntityIds];
    recalledSet.current = new Set(combined);
    if (combined.length > 0) {
      triggerAnimationWindow(4000);
    }
  }, [recalledFactIds, matchedEntityIds]);

  // Handle ResizeObserver for canvas dimensions
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: Math.floor(entry.contentRect.width),
          height: Math.floor(entry.contentRect.height),
        });
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Handle Graph Snapshot Updates
  useEffect(() => {
    if (!snapshot) return;

    if (snapshotChanged(prevSnapshotRef.current, snapshot)) {
      const prevCount = nodes.length;
      const currentNow = Date.now();
      const updatedData = mergeSnapshot(nodes, snapshot, currentNow);
      setNodes(updatedData.nodes);
      setLinks(updatedData.links);

      triggerAnimationWindow(1500);

      // Reheat simulation if new nodes arrived
      if (updatedData.nodes.length > prevCount && fgRef.current) {
        fgRef.current.d3ReheatSimulation();
        setTimeout(() => {
          fgRef.current?.zoomToFit(500, 60);
        }, 300);
      }

      prevSnapshotRef.current = snapshot;
    }
  }, [snapshot, nodes]);

  const hasNodes = nodes.length > 0;

  // Configure D3 Force Parameters once graph component is mounted
  useEffect(() => {
    if (fgRef.current && hasNodes) {
      fgRef.current.d3Force("charge")?.strength(-140);
      fgRef.current.d3Force("link")?.distance((link: any) => {
        return link.type === "REPLACES" ? 40 : 55;
      });
    }
  }, [hasNodes]);

  // Keyboard shortcut Esc to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedNode(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleFitClick = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(500, 60);
    }
  };

  const handleNodeClick = (node: any) => {
    setSelectedNode(node.id);
    if (onFactSelect && node.kind === "fact") {
      onFactSelect(node.id);
    }
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
  };

  const handleSelectNodeById = (nodeId: string) => {
    setSelectedNode(nodeId);
    const targetNode = nodes.find((n) => n.id === nodeId);
    if (targetNode && fgRef.current && targetNode.x !== undefined && targetNode.y !== undefined) {
      fgRef.current.centerAt(targetNode.x, targetNode.y, 500);
    }
  };

  // Memoize graphData so reference remains stable and doesn't trigger layout reheat on every render
  const graphData = useMemo(() => {
    const filtered = filterHistory({ nodes, links }, showHistory);
    return { nodes: filtered.nodes, links: filtered.links };
  }, [nodes, links, showHistory]);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  return (
    <div className="graph-panel" ref={containerRef}>
      {nodes.length === 0 ? (
        <div className="graph-empty-state">
          <p className="empty-text">Memory is empty. Say something to Mnemo.</p>
        </div>
      ) : (
        <ForceGraph2D
          ref={fgRef as any}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData as any}
          backgroundColor={COLORS.bg}
          cooldownTicks={120}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.35}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            drawNode(
              node as ExtendedNode,
              ctx,
              globalScale,
              Date.now(),
              selectedNodeId,
              highlightedFactId,
              recalledSet.current
            );
          }}
          nodeCanvasObjectMode={() => "replace"}
          nodeLabel={(node: any) => node.label}
          linkDirectionalArrowLength={(link: any) => (link.type === "REPLACES" ? 6 : 0)}
          linkDirectionalArrowRelPos={1}
          linkDirectionalArrowColor={() => COLORS.danger}
          linkColor={(link: any) => (link.type === "REPLACES" ? COLORS.danger : "#3A4770")}
          linkWidth={(link: any) => (link.type === "REPLACES" ? 1.5 : 1)}
          linkCurvature={(link: any) => (link.type === "REPLACES" ? 0.2 : 0)}
          onNodeClick={handleNodeClick}
          onBackgroundClick={handleBackgroundClick}
          autoPauseRedraw={!isAnimating}
        />
      )}

      {/* Top Left Legend */}
      <Legend />

      {/* Top Right Controls */}
      <div className="graph-overlay controls-overlay">
        <label className="history-checkbox-label">
          <input
            type="checkbox"
            checked={showHistory}
            onChange={(e) => setShowHistory(e.target.checked)}
          />
          <span>Show history</span>
        </label>
        <button
          type="button"
          className="btn-fit"
          onClick={handleFitClick}
          title="Fit graph to view"
        >
          Fit
        </button>
      </div>

      {/* Bottom Left Stats */}
      {snapshot && (
        <div className="graph-overlay stats-overlay">
          <span>
            {snapshot.stats.entities} entities · {snapshot.stats.current_facts}{" "}
            current · {snapshot.stats.replaced_facts} replaced
          </span>
        </div>
      )}

      {/* Slide-in Node Detail Drawer */}
      <NodeDetail
        node={selectedNode}
        snapshot={snapshot}
        now={Date.now()}
        onClose={() => setSelectedNode(null)}
        onSelectNodeById={handleSelectNodeById}
      />
    </div>
  );
};
