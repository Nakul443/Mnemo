# this file is responsible for testing the validation and extraction logic in the Mnemo memory module.
# in simple words,
# it checks that the extract and check_conflict functions correctly handle invalid JSON output from the Gemini LLM,
# and that they sanitize the output to ensure that only valid actions and replacement IDs are returned.

import json
from dataclasses import replace
from types import SimpleNamespace

import mnemo.llm.client as llm_client
import mnemo.memory.extract as extract_module
import pytest
from google.genai.errors import ClientError
from mnemo.memory import conflicts


def test_extract_cleans_invalid_entities_and_unknown_fact_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = """```json
    {
      "entities": [
        {"name": " Project X ", "type": "Project"},
        {"name": "project  x", "type": "Tool"},
        {"name": "Mystery", "type": "Unknown"},
        {"name": "Go", "type": "Tool"}
      ],
      "facts": [
        {"text": " Project X uses Go ", "about": ["project x", "Go", "Mystery"]},
        {"text": " ", "about": ["Project X"]},
        {"text": "unlinked", "about": ["Missing"]}
      ]
    }
    ```"""
    calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        extract_module,
        "generate_json",
        lambda model, system_prompt, content: (
            calls.append((model, system_prompt, content)) or response
        ),
    )

    result = extract_module.extract("We use Go.", ["We started Project X."])

    assert [(entity.name, entity.type) for entity in result.entities] == [
        ("Project X", "Project"),
        ("Go", "Tool"),
    ]
    assert [(fact.text, fact.about) for fact in result.facts] == [
        ("Project X uses Go", ["Project X", "Go"])
    ]
    assert calls[0][0] == extract_module.get_settings().extraction_model
    assert "RECENT:\n- We started Project X.\nMESSAGE: We use Go." == calls[0][2]
    assert calls[0][1] == extract_module.load_prompt("extract")


def test_extract_retries_invalid_json_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            "not json",
            json.dumps({"entities": [], "facts": []}),
        ]
    )
    calls = 0

    def generate(*args: str) -> str:
        nonlocal calls
        calls += 1
        return next(responses)

    monkeypatch.setattr(extract_module, "generate_json", generate)

    assert extract_module.extract("Thanks!", []) == extract_module.ExtractionResult()
    assert calls == 2


def test_extract_returns_empty_after_two_invalid_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def generate(*args: str) -> str:
        nonlocal calls
        calls += 1
        return '{"entities": "not a list", "facts": []}'

    monkeypatch.setattr(extract_module, "generate_json", generate)

    assert extract_module.extract("Hello", []) == extract_module.ExtractionResult()
    assert calls == 2


def test_conflict_prefilters_empty_and_normalized_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*args: str) -> str:
        raise AssertionError("prefilters must not call Gemini")

    monkeypatch.setattr(conflicts, "generate_json", unexpected_call)

    assert conflicts.check_conflict("Anything", []).action == "add"
    duplicate = conflicts.check_conflict(
        "  Project   X USES Go ",
        [{"id": "known", "text": "project x uses go"}],
    )
    assert duplicate.action == "skip"
    assert duplicate.replaces == []


@pytest.mark.parametrize(
    ("response", "expected_action", "expected_ids"),
    [
        (
            '{"action":"replace","replaces":["known","unknown","known"]}',
            "replace",
            ["known"],
        ),
        ('{"action":"replace","replaces":["unknown"]}', "add", []),
        ('{"action":"skip","replaces":["known"]}', "skip", []),
        ('{"action":"surprise","replaces":["known"]}', "add", []),
        ('{"action":"add","replaces":["known"]}', "add", []),
    ],
)
def test_conflict_sanitizes_actions_and_replacement_ids(
    monkeypatch: pytest.MonkeyPatch,
    response: str,
    expected_action: str,
    expected_ids: list[str],
) -> None:
    monkeypatch.setattr(conflicts, "generate_json", lambda *args: response)

    decision = conflicts.check_conflict(
        "Project X uses Go",
        [{"id": "known", "text": "Project X uses Python"}],
    )

    assert decision.action == expected_action
    assert decision.replaces == expected_ids


def test_conflict_retries_malformed_output_then_defaults_to_add(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["{bad", "{still bad"])
    calls = 0

    def generate(*args: str) -> str:
        nonlocal calls
        calls += 1
        return next(responses)

    monkeypatch.setattr(conflicts, "generate_json", generate)

    decision = conflicts.check_conflict(
        "Project X uses Go",
        [{"id": "known", "text": "Project X uses Python"}],
    )

    assert decision.action == "add"
    assert decision.replaces == []
    assert calls == 2


def test_generate_json_retries_http_429_and_503_with_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = replace(llm_client.get_settings(), gemini_api_key="fake-key")
    monkeypatch.setattr(llm_client, "get_settings", lambda: settings)
    monkeypatch.setattr(llm_client, "_get_client", lambda _: fake_client)
    sleeps: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
    monkeypatch.setattr(llm_client.random, "uniform", lambda start, stop: 0.5)

    class FakeModels:
        calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise ClientError(429, {"message": "rate limited"})
            if self.calls == 2:
                raise ClientError(503, {"message": "service unavailable"})
            assert kwargs["model"] == "test-model"
            assert kwargs["config"].temperature == 0
            assert kwargs["config"].response_mime_type == "application/json"
            return SimpleNamespace(text='{"ok": true}')

    models = FakeModels()
    fake_client = SimpleNamespace(models=models)

    result = llm_client.generate_json("test-model", "system", "input")

    assert result == '{"ok": true}'
    assert models.calls == 3
    assert sleeps == [1.5, 2.5]


def test_generate_json_propagates_non_rate_limit_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = replace(llm_client.get_settings(), gemini_api_key="fake-key")
    monkeypatch.setattr(llm_client, "get_settings", lambda: settings)

    class FakeModels:
        def generate_content(self, **kwargs):
            raise ClientError(400, {"message": "invalid request"})

    monkeypatch.setattr(
        llm_client,
        "_get_client",
        lambda _: SimpleNamespace(models=FakeModels()),
    )
    sleeps: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)

    with pytest.raises(ClientError):
        llm_client.generate_json("test-model", "system", "input")
    assert sleeps == []


def test_is_retryable_daily_quota_and_rate_limits() -> None:
    per_day_error = ClientError(
        429,
        {"message": "quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"},
    )
    plain_429_error = ClientError(429, {"message": "rate limited"})
    plain_503_error = ClientError(503, {"message": "service unavailable"})

    assert llm_client._is_retryable(per_day_error) is False
    assert llm_client._is_retryable(plain_429_error) is True
    assert llm_client._is_retryable(plain_503_error) is True
