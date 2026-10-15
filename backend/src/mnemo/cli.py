"""Terminal CLI chat interface for Mnemo agent."""

# this file provides a command-line interface (CLI) for interacting with the Mnemo agent.
# it allows users to start a new chat session or resume an existing one,
# send messages to the agent, and receive responses.
# it also provides options to display recalled memory and handle background extraction

import argparse
import logging
import sys

from mnemo.agent.service import run_turn
from mnemo.config import get_settings
from mnemo.memory import read, schema, worker, write


def main() -> None:
    parser = argparse.ArgumentParser(description="Mnemo interactive CLI chat loop")
    parser.add_argument(
        "--session",
        "-s",
        type=str,
        default=None,
        help="Existing session ID to resume (creates new session if omitted)",
    )
    parser.add_argument(
        "--show-memory",
        "-m",
        action="store_true",
        help="Print recalled facts after each assistant reply",
    )
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    schema.init_schema()
    write.ensure_agent(settings.agent_id, settings.agent_name)

    session_id = args.session
    if not session_id:
        session_id = write.create_session(settings.agent_id)
        print(f"Started new session: {session_id}")
    else:
        if not read.session_exists(settings.agent_id, session_id):
            print(f"Error: Session '{session_id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(f"Resumed session: {session_id}")

    print("Type your message and press Enter. Type '/quit' or press Ctrl+D to exit.\n")

    while True:
        try:
            user_input = input("User > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_input:
            continue

        if user_input.casefold() in ("/quit", "/exit", "quit", "exit"):
            print("Exiting...")
            break

        try:
            turn_res = run_turn(settings.agent_id, session_id, user_input)
            print(f"\nMnemo > {turn_res.reply}\n")

            if args.show_memory and turn_res.recalled:
                print("--- Recalled Memory ---")
                for rf in turn_res.recalled:
                    print(f"  • [{rf.source}] {rf.text}")
                print()
        except Exception as error:  # noqa: BLE001
            print(f"\n[Error] {error}\n", file=sys.stderr)

    # Wait for pending background extraction jobs before exiting
    pending = worker.pending_count()
    if pending > 0:
        print(f"Waiting for {pending} background extraction job(s) to finish...")
        worker.wait_for_idle(timeout=10.0)

    print("Goodbye!")


if __name__ == "__main__":
    main()
