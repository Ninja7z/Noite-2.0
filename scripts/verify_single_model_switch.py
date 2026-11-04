import json,time,urllib.request
from pathlib import Path
H="http://127.0.0.1:11434"
def post(path,payload):
 q=urllib.request.Request(H+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(q,timeout=900) as r:return json.loads(r.read().decode())
def get(path):
 with urllib.request.urlopen(H+path,timeout=15) as r:return json.loads(r.read().decode())
seq=[("qwen3.5:4b",4096,True),("qwen2.5:3b",4096,False),
     ("qwen2.5-coder:3b",4096,False),("qwen2.5:1.5b",4096,False),
     ("gemma4:e2b",4096,True),("qwen3.5:4b",8192,True)]
out=[]
for model,ctx,disable_think in seq:
 print("START",model,ctx,flush=True)
 p={"model":model,"messages":[{"role":"user","content":"Responda em português: diga apenas troca confirmada."}],
    "stream":False,"keep_alive":"5m","options":{"temperature":0.2,"num_ctx":ctx,"num_predict":32}}
 if disable_think:p["think"]=False
 t=time.perf_counter()
 try:
  d=post("/api/chat",p); m=d.get("message",{}); loaded=[x.get("name") for x in get("/api/ps").get("models",[])]
  row={"model":model,"context":ctx,"ok":bool((m.get("content") or "").strip()),
       "content_chars":len(m.get("content") or ""),"thinking_chars":len(m.get("thinking") or ""),
       "wall_s":round(time.perf_counter()-t,2),"loaded":loaded,"one_model":len(loaded)<=1}
 except Exception as e:row={"model":model,"context":ctx,"ok":False,"error":str(e)}
 out.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
Path("build").mkdir(exist_ok=True)
Path("build/ollama_sequential_switch_verified.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("DONE",flush=True)
