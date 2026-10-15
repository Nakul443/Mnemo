"""Unit tests for CLI interface."""

import pytest

from mnemo.agent.models import TurnResult
from mnemo.cli import main
from mnemo.memory import read, worker, write
from mnemo.models import RecalledFact


def test_cli_new_session_loop(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inputs = iter(["Hello agent", "/quit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    monkeypatch.setattr(write, "ensure_agent", lambda agent_id, name: None)
    monkeypatch.setattr(write, "create_session", lambda agent_id: "s_cli_1")

    def mock_run_turn(agent_id: str, session_id: str, text: str) -> TurnResult:
        assert session_id == "s_cli_1"
        assert text == "Hello agent"
        return TurnResult(
            reply="Hello from CLI test!",
            session_id=session_id,
            event_id="ev_cli_1",
            recalled=[
                RecalledFact(
                    id="f1", text="Project X uses Go", created_at=100, source="direct"
                )
            ],
        )

    monkeypatch.setattr("mnemo.cli.run_turn", mock_run_turn)
    monkeypatch.setattr(worker, "wait_for_idle", lambda timeout=None: True)

    monkeypatch.setattr("sys.argv", ["mnemo-chat", "--show-memory"])

    main()

    captured = capsys.readouterr().out
    assert "Started new session: s_cli_1" in captured
    assert "Mnemo > Hello from CLI test!" in captured
    assert "--- Recalled Memory ---" in captured
    assert "[direct] Project X uses Go" in captured


def test_cli_resume_nonexistent_session_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(write, "ensure_agent", lambda agent_id, name: None)
    monkeypatch.setattr(read, "session_exists", lambda agent_id, s_id: False)
    monkeypatch.setattr("sys.argv", ["mnemo-chat", "--session", "bad-session-id"])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
