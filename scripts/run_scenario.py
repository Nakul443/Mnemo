"""Scenario runner script for Mnemo memory evaluation."""

import argparse
import json
import logging
import sys
from pathlib import Path

from mnemo.config import get_settings
from mnemo.memory.client import get_graph
from mnemo.memory.pipeline import process_message
from mnemo.memory.schema import init_schema
from mnemo.memory.write import create_session, ensure_agent


def reset_graph() -> None:
    """Delete the graph and re-initialize indexes and agent."""
    settings = get_settings()
    try:
        get_graph().delete()
        print(f"Deleted graph '{settings.falkordb_graph}'.")
    except Exception as error:
        print(f"Could not delete graph '{settings.falkordb_graph}': {error}")
    init_schema()
    ensure_agent(settings.agent_id, settings.agent_name)
    print(f"Re-initialized graph '{settings.falkordb_graph}'.")


def run_scenario(
    scenario_path: Path,
    verbose: bool = False,
    reset: bool = False,
) -> None:
    settings = get_settings()
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if reset:
        reset_graph()
    else:
        ensure_agent(settings.agent_id, settings.agent_name)

    with scenario_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sessions = data.get("sessions", [])
    print(
        f"\n========================================================"
        f"\nRunning scenario '{scenario_path.name}' ({len(sessions)} session(s))"
        f"\n========================================================\n"
    )

    msg_counter = 0
    for s_idx, session_data in enumerate(sessions, start=1):
        session_name = session_data.get("name", f"Session {s_idx}")
        messages = session_data.get("messages", [])
        session_id = create_session(settings.agent_id)
        print(
            f"--- {session_name} (ID: {session_id[:8]}..., {len(messages)} message(s)) ---"
        )

        for msg_text in messages:
            msg_counter += 1
            print(f'\n[#{msg_counter}] USER: "{msg_text}"')
            result = process_message(settings.agent_id, session_id, msg_text)

            if not result.entities and not result.fact_decisions:
                print("  -> (no entities or facts extracted)")
                continue

            if result.entities:
                ents_str = ", ".join(f"{e.name} ({e.type})" for e in result.entities)
                print(f"  Entities: {ents_str}")

            for fd in result.fact_decisions:
                if fd.action == "add":
                    print(f'  [ADD]     "{fd.text}"')
                elif fd.action == "replace":
                    replaces_str = ", ".join(fd.replaces)
                    print(f'  [REPLACE] "{fd.text}" -> replaces [{replaces_str}]')
                elif fd.action == "skip":
                    print(f'  [SKIP]    "{fd.text}"')

        print()

    print("========================================================")
    print("Scenario execution complete.")
    print("========================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Mnemo memory scenario evaluation."
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="tests/scenarios/day1_scenario.json",
        help="Path to scenario JSON file (default: tests/scenarios/day1_scenario.json)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--reset",
        "-r",
        action="store_true",
        help="Delete and re-initialize graph before running",
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.exists():
        print(
            f"Error: Scenario file '{scenario_path}' does not exist.", file=sys.stderr
        )
        sys.exit(1)

    run_scenario(scenario_path, verbose=args.verbose, reset=args.reset)


if __name__ == "__main__":
    main()
