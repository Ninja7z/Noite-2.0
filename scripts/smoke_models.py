import json
import time
import urllib.request
from pathlib import Path

URL = "http://127.0.0.1:11434/api/chat"


def call(model, messages, num_predict=120, format_json=False):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": "5m",
        "options": {"temperature": 0.1, "num_ctx": 2048, "num_predict": num_predict},
    }
    if format_json:
        payload["format"] = "json"
    if model.startswith("qwen3.5:"):
        payload["think"] = False
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    first = None
    text = ""
    final = {}
    with urllib.request.urlopen(req, timeout=180) as response:
        for raw in response:
            if not raw.strip():
                continue
            item = json.loads(raw)
            chunk = item.get("message", {}).get("content", "")
            if chunk and first is None:
                first = time.perf_counter()
            text += chunk
            if item.get("done"):
                final = item
    end = time.perf_counter()
    return {
        "model": model,
        "text": text.strip(),
        "first_token_s": round((first or end) - start, 3),
        "total_s": round(end - start, 3),
        "tokens": final.get("eval_count", 0),
        "tokens_per_s": round(final.get("eval_count", 0) / (final.get("eval_duration", 1) / 1e9), 2)
        if final.get("eval_duration")
        else None,
        "load_s": round(final.get("load_duration", 0) / 1e9, 3),
    }


router_system = (
    "Você é um classificador de intenção. Retorne SOMENTE JSON válido com as chaves "
    "intent, target, use_rag. intent: chat_simple, reasoning, coding, tool. "
    "target: fast, reasoning, coding, direct. use_rag: boolean. "
    "Regras: saudação/pergunta cotidiana=chat_simple/fast/false; "
    "bug ou lógica=reasoning/reasoning/false; "
    "criar ou refatorar código=coding/coding/false; "
    "hora, abrir app, arquivo, clima ou pesquisa externa=tool/direct/false. "
    "Nunca invente ferramentas nem execute ações."
)
cases = [
    ("saudacao", "Bom dia, tudo bem?"),
    ("coding", "Refatore esta classe PySide6 para reduzir acoplamento e escreva testes unitários."),
    (
        "reasoning",
        (
            "Analise este bug: a tarefa assíncrona trava após o segundo evento. "
            "Liste hipóteses e um plano de diagnóstico."
        ),
    ),
    ("tool", "Que horas são agora?"),
    ("tool", "Pesquise a previsão do tempo para Gouveia amanhã."),
]
results = []
for label, prompt in cases:
    try:
        r = call(
            "qwen2.5:0.5b",
            [{"role": "system", "content": router_system}, {"role": "user", "content": prompt}],
            100,
            True,
        )
        try:
            obj = json.loads(r["text"])
            r["parsed"] = obj
            expected = {
                "saudacao": "chat_simple",
                "coding": "coding",
                "reasoning": "reasoning",
                "tool": "tool",
            }[label]
            r["correct_intent"] = obj.get("intent") == expected
        except Exception:
            r["parsed_error"] = True
            r["correct_intent"] = False
        r["case"] = label
        results.append(r)
    except Exception as e:
        results.append({"case": label, "error": str(e)})

tasks = [
    (
        "qwen2.5:1.5b",
        (
            "Responda em português brasileiro, em duas frases: por que separar "
            "interface e lógica de negócio?"
        ),
    ),
    (
        "qwen2.5-coder:1.5b",
        (
            "Escreva uma função Python curta que recebe uma lista de inteiros e retorna "
            "apenas os números pares, com type hints e docstring."
        ),
    ),
    (
        "deepseek-r1:1.5b",
        (
            "Uma tarefa leva 4 segundos. Duas tarefas independentes podem executar "
            "em paralelo. Quanto tempo mínimo levam juntas? Explique brevemente."
        ),
    ),
    (
        "qwen3.5:4b",
        (
            "Explique em português, de forma objetiva, por que um roteador de tarefas "
            "não deve decidir permissões de segurança."
        ),
    ),
]
for model, prompt in tasks:
    try:
        results.append(call(model, [{"role": "user", "content": prompt}], 150))
    except Exception as e:
        results.append({"model": model, "error": str(e)})

report = {"created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results}
out = Path("build/model-smoke-benchmark.json")
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
for r in results:
    print("\n###", r.get("case") or r.get("model"))
    print(
        "first_token_s:",
        r.get("first_token_s"),
        "total_s:",
        r.get("total_s"),
        "tok/s:",
        r.get("tokens_per_s"),
        "load_s:",
        r.get("load_s"),
        "correct:",
        r.get("correct_intent"),
    )
    print("output:", r.get("parsed") or r.get("text") or r.get("error"))
print("\nREPORT:", out)
