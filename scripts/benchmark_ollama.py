#!/usr/bin/env python
"""Benchmark installed Ollama models sequentially on the local machine.

No model is downloaded. One model is loaded at a time and unloaded after each
run. Results contain timing/token metadata and task scores, never prompt output.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_HOST = "http://127.0.0.1:11434"
TASKS = [
    {
        "name": "portuguese_reasoning",
        "prompt": (
            "Responda em português brasileiro. Uma tarefa demora 12 minutos. "
            "Se três tarefas independentes forem executadas em sequência, quanto "
            "tempo será necessário? Explique em uma frase."
        ),
        "checks": ["36", "trinta e seis"],
    },
    {
        "name": "instruction_following",
        "prompt": (
            "Responda exatamente neste formato, sem texto extra:\n"
            "STATUS: OK\nIDIOMA: pt-BR\nITENS: 3"
        ),
        "checks": ["STATUS: OK", "IDIOMA: pt-BR", "ITENS: 3"],
    },
    {
        "name": "coding",
        "prompt": (
            "Em Python, escreva uma função chamada is_even(n) que retorne "
            "True quando n for par e False caso contrário. Retorne somente o código."
        ),
        "checks": ["def is_even", "return", "% 2"],
    },
]


def request_json(
    url: str, payload: dict[str, Any] | None = None, timeout: int = 15
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def list_models(host: str, timeout: int) -> list[str]:
    data = request_json(f"{host}/api/tags", timeout=timeout)
    return sorted(
        str(item["name"])
        for item in data.get("models", [])
        if isinstance(item, dict) and item.get("name")
    )


def benchmark_one(host: str, model: str, rounds: int, timeout: int) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for round_number in range(1, rounds + 1):
        for task in TASKS:
            payload = {
                "model": model,
                "prompt": task["prompt"],
                "stream": False,
                "keep_alive": "5m",
                "options": {"temperature": 0, "num_predict": 160},
            }
            started = time.perf_counter()
            result = request_json(f"{host}/api/generate", payload, timeout=timeout)
            wall_seconds = time.perf_counter() - started
            response_text = str(result.get("response", ""))
            checks = task["checks"]
            passed = sum(check.casefold() in response_text.casefold() for check in checks)
            eval_count = int(result.get("eval_count") or 0)
            eval_duration = int(result.get("eval_duration") or 0)
            prompt_count = int(result.get("prompt_eval_count") or 0)
            prompt_duration = int(result.get("prompt_eval_duration") or 0)
            runs.append(
                {
                    "round": round_number,
                    "task": task["name"],
                    "wall_seconds": round(wall_seconds, 3),
                    "prompt_tokens": prompt_count,
                    "generated_tokens": eval_count,
                    "tokens_per_second": round(eval_count / (eval_duration / 1e9), 2)
                    if eval_duration > 0 else None,
                    "prompt_tokens_per_second": round(prompt_count / (prompt_duration / 1e9), 2)
                    if prompt_duration > 0 else None,
                    "check_score": f"{passed}/{len(checks)}",
                }
            )
    try:
        request_json(
            f"{host}/api/generate",
            {"model": model, "prompt": "", "keep_alive": 0, "stream": False},
            timeout=min(timeout, 30),
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        pass  # A falha ao descarregar não invalida as medições já coletadas.
    latencies = [run["wall_seconds"] for run in runs]
    speeds = [run["tokens_per_second"] for run in runs if run["tokens_per_second"]]
    return {
        "model": model,
        "rounds": rounds,
        "task_runs": len(runs),
        "average_wall_seconds": round(statistics.mean(latencies), 3),
        "median_wall_seconds": round(statistics.median(latencies), 3),
        "average_generation_tokens_per_second": round(statistics.mean(speeds), 2)
        if speeds else None,
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark local Ollama models without downloading anything."
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help=f"Ollama URL (default: {DEFAULT_HOST})"
    )
    parser.add_argument(
        "--model", help="Exact installed model name, e.g. qwen2.5:7b-instruct-q4_K_M"
    )
    parser.add_argument("--rounds", type=int, default=1, choices=range(1, 4))
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--list", action="store_true", help="List installed models and exit")
    args = parser.parse_args()
    host = args.host.rstrip("/")
    try:
        models = list_models(host, min(args.timeout, 30))
        if args.list:
            print("\n".join(models) if models else "Nenhum modelo instalado.")
            return 0
        if not args.model:
            parser.error("informe --model ou use --list")
        if args.model not in models:
            print(f"Modelo '{args.model}' não encontrado. Use --list.", file=sys.stderr)
            return 2
        print(f"Benchmark sequencial: {args.model} | {args.rounds} rodada(s)", flush=True)
        report = benchmark_one(host, args.model, args.rounds, args.timeout)
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        report["host"] = host
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(f"Relatório salvo em: {args.output}")
        print(rendered)
        return 0
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"Falha no benchmark: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
