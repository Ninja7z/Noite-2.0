from __future__ import annotations
import json,time,urllib.request
from pathlib import Path
HOST="http://127.0.0.1:11434"
OUT=Path("build/ollama_tool_call_matrix.json")
def post(path,payload,timeout=600):
    req=urllib.request.Request(HOST+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
def tool(name,desc,props,required):
    return {"type":"function","function":{"name":name,"description":desc,"parameters":{"type":"object","properties":props,"required":required}}}
tools=[
 tool("get_weather","Get current weather for a city",{"city":{"type":"string"}},["city"]),
 tool("search_web","Search the web",{"query":{"type":"string"}},["query"]),
 tool("read_file","Read a permitted project file",{"path":{"type":"string"}},["path"]),
 tool("create_task","Create a task after approval",{"title":{"type":"string"}},["title"]),
 tool("get_time","Get local time",{"timezone":{"type":"string"}},["timezone"]),
]
models=["qwen3.5:4b","qwen2.5:3b","qwen2.5-coder:3b","deepseek-r1:1.5b","gemma4:e2b"]
results=[]
for model in models:
  for count in (1,5):
    selected=tools[:count]
    prompt="Use get_weather for the city Gouveia. Do not answer with prose; request the function with city='Gouveia'."
    payload={"model":model,"messages":[{"role":"user","content":prompt}],"tools":selected,
             "stream":False,"keep_alive":"5m",
             "options":{"temperature":0,"num_ctx":4096,"num_predict":128}}
    if model.startswith(("qwen3.5:","gemma4:","deepseek-r1:")): payload["think"]=False
    started=time.perf_counter()
    try:
      data=post("/api/chat",payload,timeout=900); msg=data.get("message",{})
      calls=msg.get("tool_calls") or []
      names=[]
      for c in calls:
        fn=c.get("function",{}) if isinstance(c,dict) else {}
        names.append(fn.get("name"))
      row={"model":model,"tool_count":count,"ok":bool(calls),
           "tool_names":names,"content_chars":len(msg.get("content") or ""),
           "thinking_chars":len(msg.get("thinking") or ""),
           "wall_s":round(time.perf_counter()-started,3),
           "eval_tokens":data.get("eval_count"),"error":None}
    except Exception as e:
      row={"model":model,"tool_count":count,"ok":False,"tool_names":[],"wall_s":round(time.perf_counter()-started,3),"error":str(e)}
    results.append(row); print(json.dumps(row,ensure_ascii=False),flush=True)
    try:post("/api/generate",{"model":model,"prompt":"","keep_alive":0,"stream":False},60)
    except Exception:pass
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({"results":results},ensure_ascii=False,indent=2),encoding="utf-8")
print("SAVED",OUT.resolve(),flush=True)
