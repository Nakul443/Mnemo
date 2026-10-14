# Prompt Changelog

This document tracks revisions to system prompts in `src/mnemo/prompts/`.

## [Day 1 - Initial Version] - 2026-10-15

### `extract.md` (v1.0.0)
- Initial extraction prompt for converting user messages into durable entities and facts.
- Restricts extraction to durable information (projects, tools, decisions, preferences, people).
- Output format: JSON with `entities` and `facts` arrays.

### `conflict.md` (v1.0.0)
- Initial conflict classification prompt comparing new facts against existing facts.
- Output actions: `add`, `replace`, `skip`.
- Requires listing `replaces` IDs when action is `replace`.
