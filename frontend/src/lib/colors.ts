// this file is responsible for defining the types used in the API responses and requests

import type { EntityType } from "../api/types";

export const COLORS = {
  bg: "#0B1020",
  panel: "#111833",
  panel2: "#182044",
  border: "#1F2A4D",
  text: "#E6EAF5",
  muted: "#8B96B8",
  accent: "#7C9CFF",
  danger: "#F87171",
  ok: "#34D399",
  gold: "#FFD166",
};

export const ENTITY_COLORS: Record<EntityType, string> = {
  Project: "#7C9CFF",
  Tool: "#34D399",
  Person: "#F59E0B",
  Decision: "#F472B6",
  Preference: "#A78BFA",
};
