// this file is responsible for defining the types used in the API responses and requests

export type Role = "user" | "assistant";

export interface ChatMessage {
  role: Role;
  text: string;
  seq: number;
  ts: number; // epoch ms
}

export interface RecalledFact {
  id: string;
  text: string;
  source: "preference" | "direct" | "related" | "recent";
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  event_id: string;
  recalled_fact_ids: string[];
  matched_entity_ids: string[];
  recalled: RecalledFact[];
  extraction_pending: number;
}

export type EntityType =
  | "Project"
  | "Tool"
  | "Person"
  | "Decision"
  | "Preference";

export interface EntityNode {
  id: string;
  kind: "entity";
  label: string;
  entity_type: EntityType;
  created_at: number;
}

export interface FactNode {
  id: string;
  kind: "fact";
  label: string;
  status: "current" | "replaced";
  created_at: number;
  replaced_at: number | null;
  source_message: string | null;
}

export type ApiNode = EntityNode | FactNode;

export interface ApiEdge {
  source: string; // fact id
  target: string; // entity id (ABOUT) or old fact id (REPLACES)
  type: "ABOUT" | "REPLACES";
}

export interface GraphSnapshot {
  nodes: ApiNode[];
  edges: ApiEdge[];
  stats: {
    entities: number;
    current_facts: number;
    replaced_facts: number;
  };
  updated_at: number;
  extraction_pending: number;
}

export interface HealthResponse {
  status: string;
  graph: string;
  agent_id: string;
}

export interface CreateSessionResponse {
  session_id: string;
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: ChatMessage[];
}
