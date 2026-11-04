import json,time,urllib.request,subprocess
from pathlib import Path
HOST="http://127.0.0.1:11434"
def post(path,payload,timeout=900):
 req=urllib.request.Request(HOST+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
ctx=16384; target=ctx*2
unit="O fluxo recebeu a solicitação, validou os dados, processou a tarefa e devolveu o resultado. O estado permaneceu íntegro. "
body=(unit*((target//len(unit))+1))[:target]
payload={"model":"qwen3.5:4b","messages":[{"role":"user","content":"Em uma frase, enumere as quatro etapas deste contexto em português: "+body}],
        "stream":False,"keep_alive":"5m","think":False,
        "options":{"temperature":0.2,"top_p":0.9,"top_k":40,"repeat_penalty":1.05,"num_ctx":ctx,"num_predict":64}}
start=time.perf_counter()
try:
 d=post("/api/chat",payload); msg=d.get("message",{}); text=msg.get("content","")
 try:
  gpu=subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.free,temperature.gpu","--format=csv,noheader,nounits"],text=True).strip()
 except Exception: gpu="unavailable"
 out={"ok":bool(text.strip()),"context":ctx,"wall_s":round(time.perf_counter()-start,3),
      "prompt_tokens":d.get("prompt_eval_count"),"generated_tokens":d.get("eval_count"),
      "tok_s":round(d.get("eval_count",0)/(d.get("eval_duration",1)/1e9),2),
      "load_s":round(d.get("load_duration",0)/1e9,3),"content_chars":len(text),"gpu":gpu}
except Exception as e: out={"ok":False,"error":str(e),"wall_s":round(time.perf_counter()-start,3)}
Path("build").mkdir(exist_ok=True); Path("build/qwen35_16k_test.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out),flush=True)
