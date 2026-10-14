"""Dump current graph contents in readable plain text."""

# this file is responsible for dumping the current contents of the Mnemo graph in a human-readable format.
# in simple words, it retrieves the entities and facts from the graph and prints them to the console,
# grouped by type and including provenance information.
# provenance here means the source message that led to the fact being stored,
# as well as any replacement history for facts that have been superseded.

import sys
from collections import defaultdict

from mnemo.config import get_settings
from mnemo.memory.read import dump_memory


def dump() -> None:
    settings = get_settings()
    data = dump_memory(settings.agent_id)

    entities = data.get("entities", [])
    current_facts = data.get("current_facts", [])
    replaced_facts = data.get("replaced_facts", [])

    print("\n========================================================")
    print(f" GRAPH MEMORY DUMP — Agent: '{settings.agent_id}'")
    print("========================================================\n")

    # 1. Entities grouped by type
    print(f"--- ENTITIES ({len(entities)}) ---")
    entities_by_type: dict[str, list[str]] = defaultdict(list)
    if isinstance(entities, list):
        for ent in entities:
            if isinstance(ent, dict):
                entities_by_type[str(ent.get("type", "Unknown"))].append(
                    str(ent.get("name", ""))
                )

    if not entities:
        print("  (no entities found)\n")
    else:
        for etype, names in sorted(entities_by_type.items()):
            print(f"  [{etype}] {', '.join(names)}")
        print()

    # 2. Current facts
    print(f"--- CURRENT FACTS ({len(current_facts)}) ---")
    if not current_facts or not isinstance(current_facts, list):
        print("  (no current facts found)\n")
    else:
        for fact in current_facts:
            if not isinstance(fact, dict):
                continue
            about_objs = fact.get("about")
            about_names: list[str] = []
            if isinstance(about_objs, list):
                about_names = [
                    str(o.get("name", "")) for o in about_objs if isinstance(o, dict)
                ]
            about_str = f" [about: {', '.join(about_names)}]" if about_names else ""
            src_msg = fact.get("source_message")
            src_str = f'\n    Source: "{src_msg}"' if src_msg else ""
            print(f"  • {fact['text']}{about_str}{src_str}")
        print()

    # 3. Replaced facts
    print(f"--- REPLACED FACTS ({len(replaced_facts)}) ---")
    if not replaced_facts or not isinstance(replaced_facts, list):
        print("  (no replaced facts found)\n")
    else:
        for fact in replaced_facts:
            if not isinstance(fact, dict):
                continue
            about_objs = fact.get("about")
            about_names: list[str] = []
            if isinstance(about_objs, list):
                about_names = [
                    str(o.get("name", "")) for o in about_objs if isinstance(o, dict)
                ]
            about_str = f" [about: {', '.join(about_names)}]" if about_names else ""
            src_msg = fact.get("source_message")
            src_str = f'\n    Source: "{src_msg}"' if src_msg else ""
            replacements = fact.get("replaced_by")
            rep_texts: list[str] = []
            if isinstance(replacements, list):
                rep_texts = [
                    str(r.get("text", "")) for r in replacements if isinstance(r, dict)
                ]
            rep_str = (
                f'\n    Replaced by: "{", ".join(rep_texts)}"' if rep_texts else ""
            )
            print(f"  • [INACTIVE] {fact['text']}{about_str}{src_str}{rep_str}")
        print()

    print("========================================================\n")


def main() -> None:
    try:
        dump()
    except (RuntimeError, ValueError, KeyError, AttributeError) as error:
        print(f"Error dumping graph: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
