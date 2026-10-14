"""Dump current graph contents in readable plain text."""

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

    print(f"\n========================================================")
    print(f" GRAPH MEMORY DUMP — Agent: '{settings.agent_id}'")
    print(f"========================================================\n")

    # 1. Entities grouped by type
    print(f"--- ENTITIES ({len(entities)}) ---")
    entities_by_type: dict[str, list[str]] = defaultdict(list)
    for ent in entities:
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
    if not current_facts:
        print("  (no current facts found)\n")
    else:
        for fact in current_facts:
            about_objs = fact.get("about", [])
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
    if not replaced_facts:
        print("  (no replaced facts found)\n")
    else:
        for fact in replaced_facts:
            about_objs = fact.get("about", [])
            about_names = [
                str(o.get("name", "")) for o in about_objs if isinstance(o, dict)
            ]
            about_str = f" [about: {', '.join(about_names)}]" if about_names else ""
            src_msg = fact.get("source_message")
            src_str = f'\n    Source: "{src_msg}"' if src_msg else ""
            replacements = fact.get("replaced_by", [])
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
    except Exception as error:
        print(f"Error dumping graph: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
