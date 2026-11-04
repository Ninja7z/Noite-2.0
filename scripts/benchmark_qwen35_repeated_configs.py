from __future__ import annotations
import json,statistics,time,urllib.request
from datetime import datetime
from pathlib import Path
HOST="http://127.0.0.1:11434"; MODEL="qwen3.5:4b"
OUT=Path("build/ollama_qwen35_repeated_config_benchmark.json")
CONFIGS=[
 ("balanced",{"temperature":0.4,"top_p":0.9,"top_k":40,"repeat_penalty":1.05}),
 ("focused",{"temperature":0.2,"top_p":0.85,"top_k":30,"repeat_penalty":1.05}),
 ("broad",{"temperature":0.2,"top_p":0.95,"top_k":50,"repeat_penalty":1.0}),
 ("repeat_guard",{"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.1}),
 ("baseline",{"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.05}),
]
def post(payload):
 req=urllib.request.Request(HOST+"/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=900) as r:return json.loads(r.read().decode())
def prompt(ctx):
 target=max(1200,ctx*2); unit=("O fluxo recebeu a solicitação, validou os dados, processou a tarefa e devolveu o resultado. O estado permaneceu íntegro. ")
 return "Em uma frase, enumere as quatro etapas deste contexto em português: "+(unit*((target//len(unit))+1))[:target]
results=[]
for ctx in (2048,4096,8192):
 base={"model":MODEL,"messages":[{"role":"user","content":prompt(ctx)}],"stream":False,"keep_alive":"5m","think":False,
       "options":{"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.05,"num_ctx":ctx,"num_predict":64}}
 warm=post(base)
 print("WARMUP",ctx,"prompt_tokens",warm.get("prompt_eval_count"),"load_s",round((warm.get("load_duration") or 0)/1e9,3),flush=True)
 # Rotate order to avoid always giving the same configuration the same thermal/clock position.
 ordered=CONFIGS[ctx//2048 % len(CONFIGS):]+CONFIGS[:ctx//2048 % len(CONFIGS)]
 for rep in range(1,6):
  for name,opts in ordered:
   p={**base,"options":{**opts,"num_ctx":ctx,"num_predict":64}}
   start=time.perf_counter()
   try:
    d=post(p); wall=time.perf_counter()-start; m=d.get("message",{}); text=m.get("content","")
    n=int(d.get("eval_count") or 0); ns=int(d.get("eval_duration") or 0)
    pn=int(d.get("prompt_eval_count") or 0); pns=int(d.get("prompt_eval_duration") or 0)
    row={"context":ctx,"config":name,"rep":rep,"ok":bool(text.strip()),"wall_s":round(wall,4),
         "prompt_tokens":pn,"prompt_tok_s":round(pn/(pns/1e9),2) if pns else None,
         "generated_tokens":n,"tok_s":round(n/(ns/1e9),2) if ns else None,
         "load_s":round((d.get("load_duration") or 0)/1e9,4),
         "quality_steps":sum(x in text.casefold() for x in ("recebeu","validou","processou","devolveu"))}
   except Exception as e: row={"context":ctx,"config":name,"rep":rep,"ok":False,"error":str(e)}
   results.append(row)
   print(json.dumps(row,ensure_ascii=False),flush=True)
summary=[]
for ctx in (2048,4096,8192):
 for name,_ in CONFIGS:
  rows=[r for r in results if r.get("context")==ctx and r.get("config")==name and r.get("tok_s")]
  if rows:
   speeds=[r["tok_s"] for r in rows]
   walls=[r["wall_s"] for r in rows]
   summary.append({"context":ctx,"config":name,"n":len(rows),"median_tok_s":round(statistics.median(speeds),2),
                   "mean_tok_s":round(statistics.mean(speeds),2),"median_wall_s":round(statistics.median(walls),4),
                   "quality_mean":round(statistics.mean(r["quality_steps"] for r in rows),2)})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({"created_at":datetime.now().isoformat(),"model":MODEL,"runs":len(results),
                           "summary":summary,"results":results},ensure_ascii=False,indent=2),encoding="utf-8")
print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
print("SAVED",OUT.resolve(),flush=True)
