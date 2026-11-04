import json,time,urllib.request
from pathlib import Path
HOST="http://127.0.0.1:11434"
def post(path,payload,timeout=600):
 req=urllib.request.Request(HOST+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
results=[]
for model in ["gemma4:e2b","deepseek-r1:1.5b","qwen3.5:4b"]:
 for think in ([False,True] if model=="gemma4:e2b" else [False]):
  p={"model":model,"messages":[{"role":"user","content":"Responda em português em duas frases: explique por que separar interface e lógica de negócio."}],
     "stream":False,"keep_alive":"5m","options":{"temperature":0.2,"num_ctx":4096,"num_predict":128}}
  p["think"]=think
  start=time.perf_counter()
  try:
   d=post("/api/chat",p); m=d.get("message",{})
   row={"model":model,"think":think,"content":m.get("content",""),"thinking":m.get("thinking",""),
        "wall_s":round(time.perf_counter()-start,3),"eval_count":d.get("eval_count"),
        "eval_s":round(d.get("eval_duration",0)/1e9,3)}
  except Exception as e:row={"model":model,"think":think,"error":str(e)}
  results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  try:post("/api/generate",{"model":model,"prompt":"","keep_alive":0,"stream":False})
  except Exception:pass
Path("build").mkdir(exist_ok=True);Path("build/ollama_thinking_channels.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
