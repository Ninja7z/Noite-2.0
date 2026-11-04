import json,time,urllib.request
from pathlib import Path
HOST="http://127.0.0.1:11434"
def post(path,payload,timeout=600):
 req=urllib.request.Request(HOST+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
def get(path,timeout=15):
 with urllib.request.urlopen(HOST+path,timeout=timeout) as r:return json.loads(r.read().decode())
sequence=[
 ("qwen3.5:4b",4096,True),("qwen2.5:3b",4096,False),
 ("qwen2.5-coder:3b",4096,False),("qwen2.5:1.5b",4096,False),
 ("gemma4:e2b",4096,True),("qwen3.5:4b",8192,True),
]
results=[]
for model,ctx,think in sequence:
 p={"model":model,"messages":[{"role":"user","content":"Responda em português: diga apenas 'troca confirmada'."}],
    "stream":False,"keep_alive":"5m","options":{"temperature":0.2,"num_ctx":ctx,"num_predict":32}}
 if think:p["think"]=False
 start=time.perf_counter()
 try:
  d=post("/api/chat",p); m=d.get("message",{})
  ps=get("/api/ps")
  loaded=[x.get("name") for x in ps.get("models",[])]
  row={"requested":model,"context":ctx,"content_chars":len(m.get("content") or ""),
       "thinking_chars":len(m.get("thinking") or ""),"wall_s":round(time.perf_counter()-start,3),
       "loaded_models":loaded,"single_model_only":len(loaded)<=1 and (not loaded or loaded[0]==model)}
 except Exception as e:row={"requested":model,"context":ctx,"error":str(e)}
 results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
Path("build").mkdir(exist_ok=True)
Path("build/ollama_sequential_model_switch.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
