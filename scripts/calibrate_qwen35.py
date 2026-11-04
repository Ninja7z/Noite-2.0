from __future__ import annotations
import json, statistics, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

HOST = "http://127.0.0.1:11434"
MODEL = "qwen3.5:4b"
OUT = Path("build/ollama_profile_calibration_qwen35.json")

def post(path, payload, timeout=600):
    req=urllib.request.Request(HOST+path, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def ps():
    try: return post("/api/ps", {}, 10)
    except Exception: return {}

def prompt_for(ctx):
    # Approx. 4 chars/token in Portuguese; target ~55% of configured context.
    target=max(1200, ctx*2)
    unit=("No registro técnico, o serviço local recebeu uma solicitação, validou os dados, "
          "processou a tarefa e devolveu um resultado consistente. O estado permaneceu íntegro. ")
    body=(unit*((target//len(unit))+1))[:target]
    return ("Leia o contexto e responda em português brasileiro, em uma frase: "
            "qual é a sequência de quatro etapas descrita? Contexto:\n"+body)

configs = [
 ("baseline", {"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.05}),
 ("balanced", {"temperature":0.4,"top_p":0.9,"top_k":40,"repeat_penalty":1.05}),
 ("focused", {"temperature":0.2,"top_p":0.85,"top_k":30,"repeat_penalty":1.05}),
 ("broad", {"temperature":0.2,"top_p":0.95,"top_k":50,"repeat_penalty":1.0}),
 ("repeat_guard", {"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.1}),
]
results=[]
for ctx in (2048,4096,8192):
  for name, opts in configs:
    payload={"model":MODEL,"messages":[{"role":"user","content":prompt_for(ctx)}],
             "stream":False,"keep_alive":"5m","think":False,
             "options":{**opts,"num_ctx":ctx,"num_predict":64}}
    t=time.perf_counter()
    try:
      data=post("/api/chat",payload)
      wall=time.perf_counter()-t
      msg=data.get("message",{})
      content=msg.get("content","")
      eval_n=int(data.get("eval_count") or 0)
      eval_ns=int(data.get("eval_duration") or 0)
      prompt_n=int(data.get("prompt_eval_count") or 0)
      prompt_ns=int(data.get("prompt_eval_duration") or 0)
      row={"model":MODEL,"context":ctx,"config":name,"options":opts,
           "ok":bool(content.strip()),"wall_s":round(wall,3),
           "prompt_tokens":prompt_n,"prompt_eval_s":round(prompt_ns/1e9,3),
           "prompt_tok_s":round(prompt_n/(prompt_ns/1e9),2) if prompt_ns else None,
           "generated_tokens":eval_n,"generation_s":round(eval_ns/1e9,3),
           "tok_s":round(eval_n/(eval_ns/1e9),2) if eval_ns else None,
           "load_s":round(int(data.get("load_duration") or 0)/1e9,3),
           "response_chars":len(content),"gpu":ps()}
      if ctx==2048 and name=="baseline":
        row["quality_check"]={"mentions_read_validate_process_return": all(x in content.casefold() for x in ("recebeu","validou","processou","devolveu"))}
      results.append(row)
      print(json.dumps({k:row.get(k) for k in ("context","config","ok","wall_s","prompt_tokens","tok_s","load_s")},ensure_ascii=False),flush=True)
    except Exception as e:
      row={"model":MODEL,"context":ctx,"config":name,"options":opts,"ok":False,"error":str(e)}
      results.append(row)
      print(json.dumps(row,ensure_ascii=False),flush=True)
OUT.parent.mkdir(parents=True,exist_ok=True)
report={"created_at":datetime.now().isoformat(),"model":MODEL,"test_count":len(results),"results":results}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("SAVED",OUT.resolve(),flush=True)
