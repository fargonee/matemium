from __future__ import annotations

import json

from matemium.agent.local_openai_server import LocalOpenAIHandler, SERVER_MODEL


def test_completion_response_shape() -> None:
    response = LocalOpenAIHandler._completion_response(object.__new__(LocalOpenAIHandler), "hello")

    assert response["model"] == SERVER_MODEL
    assert response["choices"][0]["message"] == {"role": "assistant", "content": "hello"}
    assert response["choices"][0]["finish_reason"] == "stop"
    assert response["usage"]["total_tokens"] == 0


def test_model_constant_is_aider_model_suffix() -> None:
    assert SERVER_MODEL == "matemium-local"
    json.dumps({"model": SERVER_MODEL})
