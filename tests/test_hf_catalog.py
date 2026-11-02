from __future__ import annotations

import json

import pytest

from noite import hf_catalog


def test_catalog_search_is_explicit_bounded_and_metadata_only(monkeypatch):
    captured = {"urls": []}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def __init__(self, body):
            self.body = body

        def read(self, limit):
            captured.setdefault("read_limits", []).append(limit)
            return json.dumps(self.body).encode()

    def fake_urlopen(request, timeout):
        captured["urls"].append(request.full_url)
        captured["timeout"] = timeout
        if "blobs=true" in request.full_url:
            return Response(
                {
                    "siblings": [
                        {
                            "rfilename": "model-q4_k_m.gguf",
                            "size": 2 * hf_catalog.GIB,
                        }
                    ]
                }
            )
        return Response(
            [
                {
                    "id": "example/Qwen-GGUF",
                    "downloads": 123,
                    "library_name": "gguf",
                    "pipeline_tag": "text-generation",
                    "tags": ["gguf", "Q4_K_M"],
                }
            ]
        )

    monkeypatch.setattr(hf_catalog, "urlopen", fake_urlopen)
    result = hf_catalog.search_huggingface_models("Qwen GGUF")

    assert len(result) == 1
    assert result[0].model_id == "example/Qwen-GGUF"
    assert result[0].is_gguf
    assert result[0].recommended_file == ("model-q4_k_m.gguf", 2 * hf_catalog.GIB)
    assert result[0].quantization == "Q4_K_M"
    assert "não garante" in result[0].hardware_advice()
    assert "text-generation" in captured["urls"][0]
    assert "blobs=true" in captured["urls"][1]
    assert captured["timeout"] == 8.0
    assert captured["read_limits"] == [hf_catalog.MAX_RESPONSE_BYTES] * 2


@pytest.mark.parametrize("query", ["", "x" * (hf_catalog.MAX_QUERY_LENGTH + 1)])
def test_catalog_rejects_empty_or_oversized_query_without_network(query, monkeypatch):
    monkeypatch.setattr(
        hf_catalog,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("network should not be called"),
    )
    with pytest.raises(ValueError):
        hf_catalog.search_huggingface_models(query)


def test_non_gguf_result_does_not_claim_local_compatibility():
    model = hf_catalog.HubModel(
        model_id="example/model",
        downloads=1,
        library="transformers",
        pipeline="text-generation",
        tags=(),
    )
    assert not model.is_gguf
    assert "não confirmada" in model.hardware_advice()
