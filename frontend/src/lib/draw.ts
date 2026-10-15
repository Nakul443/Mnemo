// this file is responsible for defining the drawNode function
// It provides a custom canvas renderer for force-graph 2D nodes,
// handling the drawing of Entity circles and Fact pills with various visual effects.
// In simple words,
    // it draws each node in the graph with specific styles based on its type (entity or fact),
    // applies animations for new nodes and replaced facts,
    // and highlights selected, recalled, or hovered nodes with visual cues like pulses and glows.

import { COLORS, ENTITY_COLORS } from "./colors";
import type { ExtendedNode } from "./graphData";

function truncateText(text: string, maxLen: number = 32): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "…";
}

/**
 * Custom canvas renderer for force-graph 2D nodes.
 * Draws Entity circles and Fact pills with custom colors, strokes, labels, strikethrough, and pulse/glow animations.
 */
export function drawNode(
  node: ExtendedNode,
  ctx: CanvasRenderingContext2D,
  globalScale: number,
  now: number,
  selectedNodeId: string | null,
  highlightedNodeId: string | null,
  recalledNodeIds: Set<string>
): void {
  const x = node.x ?? 0;
  const y = node.y ?? 0;
  const isSelected = selectedNodeId === node.id;
  const isHoverHighlighted = highlightedNodeId === node.id;
  const isRecalled = recalledNodeIds.has(node.id);

  // Animation 1: Entrance scaling and entrance glow
  const isNew = node.bornAt > 0 && now - node.bornAt < 1500;
  let entranceScale = 1;
  if (node.bornAt > 0) {
    const age = now - node.bornAt;
    if (age < 400) {
      entranceScale = age / 400; // 0 to 1 over 400ms
    }
  }

  // Animation 2: Fact replaced fade transition
  let alpha = 1;
  if (node.kind === "fact" && node.status === "replaced") {
    if (node.replacedSeenAt && now - node.replacedSeenAt < 700) {
      const progress = (now - node.replacedSeenAt) / 700;
      alpha = 1 - progress * 0.55; // Fade from 1.0 down to 0.45
    } else {
      alpha = 0.45;
    }
  }

  ctx.save();
  ctx.globalAlpha = alpha;

  // Draw Gold Pulse Animation for Recalled / Hover-Highlighted Nodes
  if (isRecalled || isHoverHighlighted) {
    let pulseRadiusExtra = 8;
    let pulseAlpha = 0.8;

    if (isRecalled) {
      const cycleMs = 1200;
      const progress = ((now % cycleMs) / cycleMs);
      pulseRadiusExtra = 4 + progress * 10; // 4px to 14px
      pulseAlpha = 1 - progress; // Fade out 1 -> 0
    }

    ctx.save();
    ctx.globalAlpha = alpha * pulseAlpha;
    ctx.strokeStyle = COLORS.gold;
    ctx.lineWidth = 2 / globalScale;
    ctx.beginPath();
    const baseRadius = node.kind === "entity" ? (node.entity_type === "Project" ? 11 : 8) : 9;
    ctx.arc(x, y, baseRadius + pulseRadiusExtra / globalScale, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.restore();
  }

  // Draw Entrance Glow for New Nodes
  if (isNew) {
    const age = now - node.bornAt;
    const glowAlpha = Math.max(0, 1 - age / 1500);
    ctx.save();
    ctx.globalAlpha = alpha * glowAlpha;
    ctx.strokeStyle = COLORS.ok;
    ctx.lineWidth = 3 / globalScale;
    ctx.beginPath();
    const baseRadius = node.kind === "entity" ? (node.entity_type === "Project" ? 11 : 8) : 9;
    ctx.arc(x, y, baseRadius + 4 / globalScale, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.restore();
  }

  // DRAW ENTITY NODE
  if (node.kind === "entity") {
    const radius =
      (node.entity_type === "Project" ? 11 : 8) * entranceScale;
    const typeColor = node.entity_type
      ? ENTITY_COLORS[node.entity_type]
      : COLORS.accent;

    // Circle Body
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = typeColor;
    ctx.fill();

    // Stroke
    ctx.lineWidth = (isSelected ? 2.5 : 1.5) / globalScale;
    ctx.strokeStyle = isSelected ? "#FFFFFF" : COLORS.bg;
    ctx.stroke();

    // Label below circle
    const labelFontSize = 12 / globalScale;
    ctx.font = `${labelFontSize}px Inter, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    const labelY = y + radius + 4 / globalScale;

    // Dual pass for legible background outline
    ctx.strokeStyle = COLORS.bg;
    ctx.lineWidth = 3 / globalScale;
    ctx.strokeText(node.label, x, labelY);

    ctx.fillStyle = COLORS.text;
    ctx.fillText(node.label, x, labelY);
  }

  // DRAW FACT NODE (PILL)
  else {
    const isReplaced = node.status === "replaced";

    // Zoomed-out mode (scale < 0.7): draw simple 3px dot instead of pill
    if (globalScale < 0.7) {
      const dotRadius = 3 * entranceScale;
      ctx.beginPath();
      ctx.arc(x, y, dotRadius, 0, 2 * Math.PI);
      ctx.fillStyle = isReplaced ? COLORS.muted : COLORS.panel2;
      ctx.fill();
      ctx.strokeStyle = isSelected ? "#FFFFFF" : "#5B6DAA";
      ctx.lineWidth = (isSelected ? 2 : 1) / globalScale;
      ctx.stroke();
      ctx.restore();
      return;
    }

    const displayText = truncateText(node.label, 32);
    const fontSize = 10.5 / globalScale;
    ctx.font = `${fontSize}px Inter, sans-serif`;

    const textMetrics = ctx.measureText(displayText);
    const textWidth = textMetrics.width;

    const paddingX = 8 / globalScale;
    const pillHeight = 18 / globalScale;
    const pillWidth = (textWidth + paddingX * 2) * entranceScale;
    const cornerRadius = 9 / globalScale;

    const pillX = x - pillWidth / 2;
    const pillY = y - pillHeight / 2;

    // Rounded rectangle path
    ctx.beginPath();
    ctx.roundRect(pillX, pillY, pillWidth, pillHeight, cornerRadius);

    if (isReplaced) {
      ctx.fillStyle = "rgba(18, 24, 47, 0.5)";
      ctx.fill();

      ctx.save();
      ctx.setLineDash([4 / globalScale, 3 / globalScale]);
      ctx.strokeStyle = isSelected ? "#FFFFFF" : "rgba(91, 109, 170, 0.5)";
      ctx.lineWidth = (isSelected ? 2 : 1) / globalScale;
      ctx.stroke();
      ctx.restore();
    } else {
      ctx.fillStyle = COLORS.panel2;
      ctx.fill();

      ctx.strokeStyle = isSelected ? "#FFFFFF" : "#5B6DAA";
      ctx.lineWidth = (isSelected ? 2 : 1) / globalScale;
      ctx.stroke();
    }

    // Text Label
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = isReplaced ? COLORS.muted : COLORS.text;
    ctx.fillText(displayText, x, y);

    // Strikethrough for replaced facts
    if (isReplaced) {
      ctx.beginPath();
      ctx.moveTo(x - textWidth / 2, y);
      ctx.lineTo(x + textWidth / 2, y);
      ctx.strokeStyle = COLORS.muted;
      ctx.lineWidth = 1 / globalScale;
      ctx.stroke();
    }
  }

  ctx.restore();
}
