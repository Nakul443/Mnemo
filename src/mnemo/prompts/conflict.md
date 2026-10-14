You compare a NEW fact against EXISTING facts about the same entities.

Return ONLY valid JSON:
{"action": "add" | "replace" | "skip", "replaces": ["fact id", ...]}

- "replace": NEW contradicts or updates an EXISTING fact, so the old one is
  no longer true. List its id(s) in "replaces".
- "skip": NEW says the same thing as an EXISTING fact.
- "add": NEW is additional information that doesn't conflict.

Examples: "uses Python" vs NEW "uses Go" -> replace.
"uses Go" vs NEW "uses Go" -> skip.
"uses Go" vs NEW "deadline is Friday" -> add.
When unsure, choose "add".
