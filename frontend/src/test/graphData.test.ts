// this file is responsible for testing the graphData helper functions

import { describe, expect, it } from "vitest";
import type { GraphSnapshot } from "../api/types";
import {
  entitiesForFact,
  factsForEntity,
  filterHistory,
  mergeSnapshot,
  replacedBy,
  replaces,
  snapshotChanged,
} from "../lib/graphData";

const sampleSnapshot: GraphSnapshot = {
  nodes: [
    { id: "e1", kind: "entity", label: "Project X", entity_type: "Project", created_at: 100 },
    { id: "e2", kind: "entity", label: "Python", entity_type: "Tool", created_at: 100 },
    { id: "e3", kind: "entity", label: "Go", entity_type: "Tool", created_at: 200 },
    {
      id: "f1",
      kind: "fact",
      label: "Project X uses Python",
      status: "replaced",
      created_at: 100,
      replaced_at: 200,
      source_message: "I am building Project X in Python.",
    },
    {
      id: "f2",
      kind: "fact",
      label: "Project X uses Go",
      status: "current",
      created_at: 200,
      replaced_at: null,
      source_message: "Actually I switched Project X to Go.",
    },
  ],
  edges: [
    { source: "f1", target: "e1", type: "ABOUT" },
    { source: "f1", target: "e2", type: "ABOUT" },
    { source: "f2", target: "e1", type: "ABOUT" },
    { source: "f2", target: "e3", type: "ABOUT" },
    { source: "f2", target: "f1", type: "REPLACES" },
  ],
  stats: { entities: 3, current_facts: 1, replaced_facts: 1 },
  updated_at: 200,
  extraction_pending: 0,
};

describe("graphData helpers", () => {
  it("mergeSnapshot reuses previous node objects by ID to preserve positions", () => {
    const firstRun = mergeSnapshot([], sampleSnapshot, 1000);
    expect(firstRun.nodes.length).toBe(5);
    expect(firstRun.nodes[0].bornAt).toBe(0); // First snapshot bornAt is 0

    // Simulate D3 positioning
    firstRun.nodes[0].x = 42;
    firstRun.nodes[0].y = 84;

    const secondRun = mergeSnapshot(firstRun.nodes, sampleSnapshot, 2000);
    expect(secondRun.nodes[0].x).toBe(42);
    expect(secondRun.nodes[0].y).toBe(84);
    expect(secondRun.nodes[0]).toBe(firstRun.nodes[0]); // Same reference
  });

  it("mergeSnapshot sets bornAt for newly added nodes", () => {
    const initial = mergeSnapshot([], sampleSnapshot, 1000);

    const updatedSnapshot: GraphSnapshot = {
      ...sampleSnapshot,
      nodes: [
        ...sampleSnapshot.nodes,
        { id: "e4", kind: "entity", label: "Rafael", entity_type: "Person", created_at: 300 },
      ],
      updated_at: 300,
    };

    const nextRun = mergeSnapshot(initial.nodes, updatedSnapshot, 3000);
    const newEntity = nextRun.nodes.find((n) => n.id === "e4");
    expect(newEntity).toBeDefined();
    expect(newEntity?.bornAt).toBe(3000);
  });

  it("filterHistory removes replaced facts and connected links when showHistory is false", () => {
    const data = mergeSnapshot([], sampleSnapshot, 1000);
    const filtered = filterHistory(data, false);

    expect(filtered.nodes.some((n) => n.id === "f1")).toBe(false);
    expect(filtered.nodes.some((n) => n.id === "f2")).toBe(true);
    expect(filtered.links.some((l) => l.source === "f1" || l.target === "f1")).toBe(false);
  });

  it("snapshotChanged returns false when update_at and lengths match", () => {
    expect(snapshotChanged(sampleSnapshot, sampleSnapshot)).toBe(false);

    const modified = { ...sampleSnapshot, extraction_pending: 1 };
    expect(snapshotChanged(sampleSnapshot, modified)).toBe(false);

    const changedAt = { ...sampleSnapshot, updated_at: 300 };
    expect(snapshotChanged(sampleSnapshot, changedAt)).toBe(true);
  });

  it("drawer lookup helpers extract facts, entities, and replacements", () => {
    const facts = factsForEntity("e1", sampleSnapshot);
    expect(facts.map((f) => f.id)).toEqual(["f1", "f2"]);

    const entities = entitiesForFact("f2", sampleSnapshot);
    expect(entities.map((e) => e.id)).toEqual(["e1", "e3"]);

    const repBy = replacedBy("f1", sampleSnapshot);
    expect(repBy?.id).toBe("f2");

    const repList = replaces("f2", sampleSnapshot);
    expect(repList.map((f) => f.id)).toEqual(["f1"]);
  });
});
