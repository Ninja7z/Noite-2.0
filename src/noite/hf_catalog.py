"""Explicit, metadata-only queries to the public Hugging Face catalog."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

MAX_QUERY_LENGTH = 80
MAX_RESULTS = 5
MAX_FILE_DETAILS = 5
MAX_RESPONSE_BYTES = 250_000
GIB = 1024**3


@dataclass(frozen=True)
class HubModel:
    model_id: str
    downloads: int | None
    library: str
    pipeline: str
    tags: tuple[str, ...]
    gguf_files: tuple[tuple[str, int], ...] = ()

    @property
    def is_gguf(self) -> bool:
        return self.library.casefold() == "gguf" or "gguf" in {
            tag.casefold() for tag in self.tags
        }

    @property
    def recommended_file(self) -> tuple[str, int] | None:
        if not self.gguf_files:
            return None
        priorities = ("q4_k_m", "q4_k_s", "q4_0", "q4_1", "q3_k_m", "q5_k_m")
        for preferred in priorities:
            candidate = next(
                (file for file in self.gguf_files if preferred in file[0].casefold()), None
            )
            if candidate is not None:
                return candidate
        return min(self.gguf_files, key=lambda item: item[1])

    @property
    def quantization(self) -> str | None:
        candidate = self.recommended_file
        if candidate is None:
            return None
        match = re.search(r"(?i)(?:IQ|Q)\d+_[A-Z0-9_]+", candidate[0])
        return match.group(0).upper() if match else "menor variante disponível"

    def hardware_advice(self) -> str:
        if not self.is_gguf:
            return "Sem indicação GGUF; compatibilidade local não confirmada."
        candidate = self.recommended_file
        if candidate is None:
            return "GGUF encontrado; quantização e tamanho de arquivo indisponíveis."
        size_gib = candidate[1] / GIB
        if size_gib <= 3:
            return (
                f"Candidato {self.quantization} pequeno ({size_gib:.2f} GiB em disco) para "
                "avaliação; o arquivo não garante memória de execução nem CPU sem AVX2."
            )
        if size_gib <= 6:
            return (
                "Pode precisar dividir carga entre VRAM e RAM; confirme o backend sem AVX2 "
                "e a memória livre antes de usar."
            )
        return (
            "Grande para a GTX 1660 Super de 6 GB; pode pressionar os 16 GB de RAM. "
            "Não recomendado sem avaliação manual do backend e da quantização."
        )


def search_huggingface_models(query: str, *, timeout: float = 8.0) -> list[HubModel]:
    """Search public text-generation model metadata; this never downloads model files."""
    query = query.strip()
    if not query or len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"A busca deve ter entre 1 e {MAX_QUERY_LENGTH} caracteres.")
    params = urlencode(
        {
            "search": query,
            "pipeline_tag": "text-generation",
            "limit": MAX_RESULTS,
            "sort": "downloads",
            "direction": -1,
        }
    )
    request = Request(
        f"https://huggingface.co/api/models?{params}",
        headers={"Accept": "application/json", "User-Agent": "Noite-2.0-model-catalog"},
    )
    timeout = max(1.0, min(timeout, 15.0))
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read(MAX_RESPONSE_BYTES).decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("O catálogo Hugging Face retornou uma resposta inesperada.")
    base_models = []
    for item in payload[:MAX_RESULTS]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        downloads = item.get("downloads")
        base_models.append(
            HubModel(
                model_id=item["id"],
                downloads=downloads if isinstance(downloads, int) else None,
                library=str(item.get("library_name") or ""),
                pipeline=str(item.get("pipeline_tag") or ""),
                tags=tuple(str(tag) for tag in tags[:100]),
            )
        )

    details_targets = [model for model in base_models if model.is_gguf][:MAX_FILE_DETAILS]

    def fetch_files(model: HubModel) -> tuple[str, tuple[tuple[str, int], ...]]:
        model_id = quote(model.model_id, safe="/")
        detail_request = Request(
            f"https://huggingface.co/api/models/{model_id}?blobs=true",
            headers={"Accept": "application/json", "User-Agent": "Noite-2.0-model-catalog"},
        )
        try:
            with urlopen(detail_request, timeout=timeout) as response:
                details = json.loads(response.read(MAX_RESPONSE_BYTES).decode("utf-8"))
        except (OSError, ValueError):
            return model.model_id, ()
        siblings = details.get("siblings") if isinstance(details, dict) else None
        files = []
        if isinstance(siblings, list):
            for sibling in siblings:
                if not isinstance(sibling, dict):
                    continue
                name = str(sibling.get("rfilename", ""))
                size = sibling.get("size")
                if name.casefold().endswith(".gguf") and isinstance(size, int) and size > 0:
                    files.append((name, size))
        return model.model_id, tuple(files[:100])

    file_map = {}
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="noite-hf-metadata") as executor:
        for model_id, files in executor.map(fetch_files, details_targets):
            file_map[model_id] = files
    return [
        HubModel(
            model_id=model.model_id,
            downloads=model.downloads,
            library=model.library,
            pipeline=model.pipeline,
            tags=model.tags,
            gguf_files=file_map.get(model.model_id, ()),
        )
        for model in base_models
    ]
