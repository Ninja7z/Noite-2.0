from __future__ import annotations
import json, subprocess, time, urllib.request
from datetime import datetime
from pathlib import Path

HOST="http://127.0.0.1:11434"
OUT=Path("build/ollama_all_models_context_sweep.json")

def request(path,payload=None,timeout=600):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(HOST+path,data=data,headers={"Content-Type":"application/json"} if data else {})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())

def gpu():
    try:
        raw=subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.free,temperature.gpu,utilization.gpu","--format=csv,noheader,nounits"],text=True,timeout=5).strip()
        a=[x.strip() for x in raw.split(",")]
        return {"used_mib":int(a[0]),"free_mib":int(a[1]),"temp_c":int(a[2]),"util_pct":int(a[3])}
    except Exception as e: return {"error":str(e)}

def prompt_for(ctx):
    target=max(1200,ctx*2)
    unit=("No registro técnico, o serviço local recebeu uma solicitação, validou os dados, "
          "processou a tarefa e devolveu um resultado consistente. O estado permaneceu íntegro. ")
    body=(unit*((target//len(unit))+1))[:target]
    return "Leia o contexto e responda em português brasileiro, em uma frase: qual é a sequência de quatro etapas descrita? Contexto:\n"+body

tags=request("/api/tags",timeout=30).get("models",[])
models=[x for x in tags if isinstance(x,dict) and x.get("name") and "nomic-embed" not in x["name"]]
# Largest package gets one conservative run; the 4.6 GB package is capped at 4K.
results=[]
for item in sorted(models,key=lambda x:int(x.get("size",0))):
    model=item["name"]; size=int(item.get("size",0))
    contexts=[2048,4096]
    if size <= 4_000_000_000: contexts.append(8192)
    if model=="gemma4:e2b": contexts=[2048,4096]
    if model=="gemma4:e4b": contexts=[2048]
    print("MODEL",model,"DISK_GB",round(size/1e9,2),"CONTEXTS",contexts,flush=True)
    for ctx in contexts:
        payload={"model":model,"messages":[{"role":"user","content":prompt_for(ctx)}],
                 "stream":False,"keep_alive":"5m",
                 "options":{"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.05,
                            "num_ctx":ctx,"num_predict":48}}
        if model.startswith("qwen3.5:"): payload["think"]=False
        started=time.perf_counter()
        try:
            data=request("/api/chat",payload,timeout=900)
            wall=time.perf_counter()-started
            msg=data.get("message",{}); answer=msg.get("content","")
            n=int(data.get("eval_count") or 0); ns=int(data.get("eval_duration") or 0)
            pn=int(data.get("prompt_eval_count") or 0); pns=int(data.get("prompt_eval_duration") or 0)
            row={"model":model,"disk_bytes":size,"context":ctx,"ok":bool(answer.strip()),
                 "wall_s":round(wall,3),"prompt_tokens":pn,
                 "prompt_tok_s":round(pn/(pns/1e9),2) if pns else None,
                 "generated_tokens":n,"tok_s":round(n/(ns/1e9),2) if ns else None,
                 "load_s":round(int(data.get("load_duration") or 0)/1e9,3),
                 "response_chars":len(answer),"mentions_steps":sum(w in answer.casefold() for w in ("recebeu","validou","processou","devolveu")),
                 "gpu":gpu()}
        except Exception as e:
            row={"model":model,"disk_bytes":size,"context":ctx,"ok":False,"error":str(e),"gpu":gpu()}
        results.append(row)
        print(json.dumps({k:row.get(k) for k in ("model","context","ok","wall_s","prompt_tokens","tok_s","load_s","gpu","error")},ensure_ascii=False),flush=True)
        # Free memory before the next context/model; Ollama max-loaded-models=1.
        try: request("/api/generate",{"model":model,"prompt":"","stream":False,"keep_alive":0},timeout=60)
        except Exception: pass
    try: request("/api/generate",{"model":model,"prompt":"","stream":False,"keep_alive":0},timeout=60)
    except Exception: pass

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({"created_at":datetime.now().isoformat(),"model_count":len(models),
                           "test_count":len(results),"models":[x["name"] for x in models],
                           "results":results},ensure_ascii=False,indent=2),encoding="utf-8")
print("SAVED",OUT.resolve(),flush=True)
