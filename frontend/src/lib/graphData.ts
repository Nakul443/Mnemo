// this file is responsible for defining the types and functions used to process graph data in the frontend
// It provides utilities to merge new graph snapshots with previous data,
// filter out historical facts, and determine if the graph has changed.

import type { ApiEdge, ApiNode, EntityNode, FactNode, GraphSnapshot } from "../api/types";

export interface ExtendedNode {
  id: string;
  kind: "entity" | "fact";
  label: string;
  created_at: number;
  // Entity properties
  entity_type?: "Project" | "Tool" | "Person" | "Decision" | "Preference";
  // Fact properties
  status?: "current" | "replaced";
  replaced_at?: number | null;
  source_message?: string | null;
  // Animation tracking
  bornAt: number;
  replacedSeenAt?: number;
  // D3 force graph properties preserve coordinates
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface ExtendedLink {
  source: string | ExtendedNode;
  target: string | ExtendedNode;
  type: "ABOUT" | "REPLACES";
}

export interface ProcessedGraphData {
  nodes: ExtendedNode[];
  links: ExtendedLink[];
}

/**
 * Reuses previous node objects by ID to preserve force simulation positions (x, y, vx, vy).
 * Rebuilds links as fresh objects from the snapshot.
 */
export function mergeSnapshot(
  prevNodes: ExtendedNode[],
  snapshot: GraphSnapshot,
  now: number
): ProcessedGraphData {
  const prevMap = new Map<string, ExtendedNode>(
    prevNodes.map((node) => [node.id, node])
  );
  const isFirstSnapshot = prevNodes.length === 0;

  const newNodes: ExtendedNode[] = snapshot.nodes.map((apiNode: ApiNode) => {
    const existing = prevMap.get(apiNode.id);

    if (existing) {
      // Preserve reference & coordinates, update dynamic snapshot properties
      existing.label = apiNode.label;
      if (apiNode.kind === "entity") {
        existing.entity_type = (apiNode as EntityNode).entity_type;
      } else {
        const factNode = apiNode as FactNode;
        // Track when status flipped from current -> replaced for fade transition
        if (existing.status === "current" && factNode.status === "replaced") {
          existing.replacedSeenAt = now;
        }
        existing.status = factNode.status;
        existing.replaced_at = factNode.replaced_at;
        existing.source_message = factNode.source_message;
      }
      return existing;
    }

    // New node created
    const bornAt = isFirstSnapshot ? 0 : now;
    if (apiNode.kind === "entity") {
      const ent = apiNode as EntityNode;
      return {
        id: ent.id,
        kind: "entity",
        label: ent.label,
        entity_type: ent.entity_type,
        created_at: ent.created_at,
        bornAt,
      };
    } else {
      const fact = apiNode as FactNode;
      return {
        id: fact.id,
        kind: "fact",
        label: fact.label,
        status: fact.status,
        created_at: fact.created_at,
        replaced_at: fact.replaced_at,
        source_message: fact.source_message,
        bornAt,
      };
    }
  });

  const newLinks: ExtendedLink[] = snapshot.edges.map((edge: ApiEdge) => ({
    source: edge.source,
    target: edge.target,
    type: edge.type,
  }));

  return { nodes: newNodes, links: newLinks };
}

/**
 * Filter out replaced facts and links connected to them when showHistory is false.
 */
export function filterHistory(
  data: ProcessedGraphData,
  showHistory: boolean
): ProcessedGraphData {
  if (showHistory) {
    return data;
  }

  const replacedNodeIds = new Set<string>(
    data.nodes
      .filter((n) => n.kind === "fact" && n.status === "replaced")
      .map((n) => n.id)
  );

  const visibleNodes = data.nodes.filter((n) => !replacedNodeIds.has(n.id));

  const visibleLinks = data.links.filter((link) => {
    const srcId = typeof link.source === "string" ? link.source : link.source.id;
    const tgtId = typeof link.target === "string" ? link.target : link.target.id;
    return !replacedNodeIds.has(srcId) && !replacedNodeIds.has(tgtId);
  });

  return { nodes: visibleNodes, links: visibleLinks };
}

/**
 * Determines whether the snapshot structure or timestamp has actually changed.
 */
export function snapshotChanged(
  prevSnapshot: GraphSnapshot | null,
  nextSnapshot: GraphSnapshot
): boolean {
  if (!prevSnapshot) return true;
  if (prevSnapshot.updated_at !== nextSnapshot.updated_at) return true;
  if (prevSnapshot.nodes.length !== nextSnapshot.nodes.length) return true;
  if (prevSnapshot.edges.length !== nextSnapshot.edges.length) return true;
  return false;
}

// Drawer lookup helpers

export function factsForEntity(entityId: string, snapshot: GraphSnapshot): FactNode[] {
  const factIds = new Set(
    snapshot.edges
      .filter((e) => e.type === "ABOUT" && e.target === entityId)
      .map((e) => e.source)
  );
  return snapshot.nodes.filter(
    (n): n is FactNode => n.kind === "fact" && factIds.has(n.id)
  );
}

export function entitiesForFact(factId: string, snapshot: GraphSnapshot): EntityNode[] {
  const entityIds = new Set(
    snapshot.edges
      .filter((e) => e.type === "ABOUT" && e.source === factId)
      .map((e) => e.target)
  );
  return snapshot.nodes.filter(
    (n): n is EntityNode => n.kind === "entity" && entityIds.has(n.id)
  );
}

export function replacedBy(factId: string, snapshot: GraphSnapshot): FactNode | null {
  const edge = snapshot.edges.find((e) => e.type === "REPLACES" && e.target === factId);
  if (!edge) return null;
  const replacingNode = snapshot.nodes.find((n) => n.id === edge.source);
  return replacingNode && replacingNode.kind === "fact" ? (replacingNode as FactNode) : null;
}

export function replaces(factId: string, snapshot: GraphSnapshot): FactNode[] {
  const targetFactIds = new Set(
    snapshot.edges
      .filter((e) => e.type === "REPLACES" && e.source === factId)
      .map((e) => e.target)
  );
  return snapshot.nodes.filter(
    (n): n is FactNode => n.kind === "fact" && targetFactIds.has(n.id)
  );
}
