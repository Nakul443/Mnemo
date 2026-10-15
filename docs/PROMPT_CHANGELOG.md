# Prompt Changelog

This document tracks revisions to system prompts in `src/mnemo/prompts/`.

## [Day 2 - Prompt Refinements] - 2026-10-16

### `extract.md` (v1.1.0)
- Added Rule 9: Preference entities must be named by topic (e.g., "Answer style") rather than value ("Concise answers") to ensure preference updates reuse the same entity node and trigger replacement correctly.
- Simplified example output: removed compound/redundant transition fact ("Project X switched from Python to Go for speed") so the model does not generate facts that conflict with the new state.

## [Day 1 - Initial Version] - 2026-10-15

### `extract.md` (v1.0.0)
- Initial extraction prompt for converting user messages into durable entities and facts.
- Restricts extraction to durable information (projects, tools, decisions, preferences, people).
- Output format: JSON with `entities` and `facts` arrays.

### `conflict.md` (v1.0.0)
- Initial conflict classification prompt comparing new facts against existing facts.
- Output actions: `add`, `replace`, `skip`.
- Requires listing `replaces` IDs when action is `replace`.
