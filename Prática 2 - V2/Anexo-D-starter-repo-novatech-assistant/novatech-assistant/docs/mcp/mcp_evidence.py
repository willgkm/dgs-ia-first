#!/usr/bin/env python3
"""Captura evidencia de uso real de um MCP server local.
Abre o server, faz handshake, envia uma sequencia de requisicoes JSON-RPC
(newline-delimited), fecha stdin e le todas as respostas do stdout.
Imprime um resumo legivel das respostas relevantes.

Uso: python mcp_evidence.py <config.json>
config = {"cmd","args","cwd","env":{...},"steps":[req,...],"show":"raw|summary"}
"""
import sys, json, subprocess, shutil, os

cfg = json.loads(open(sys.argv[1], encoding="utf-8").read())
env = os.environ.copy()
env.update(cfg.get("env", {}))
exe = shutil.which(cfg["cmd"]) or shutil.which(cfg["cmd"] + ".cmd") or cfg["cmd"]

reqs = [
    {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-06-18","capabilities":{},
        "clientInfo":{"name":"evidence-driver","version":"1.0"}}},
    {"jsonrpc":"2.0","method":"notifications/initialized"},
]
nid = 2
for step in cfg["steps"]:
    step.setdefault("jsonrpc", "2.0")
    if "method" in step and step["method"] != "notifications/initialized":
        step.setdefault("id", nid); nid += 1
    reqs.append(step)

stdin_data = "".join(json.dumps(r) + "\n" for r in reqs)

proc = subprocess.Popen([exe, *cfg["args"]], stdin=subprocess.PIPE,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cfg.get("cwd"),
    env=env, text=True, encoding="utf-8")
try:
    out, err = proc.communicate(stdin_data, timeout=cfg.get("timeout", 30))
except subprocess.TimeoutExpired:
    proc.kill(); out, err = proc.communicate()

responses = {}
for line in out.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        o = json.loads(line)
    except Exception:
        continue
    if "id" in o:
        responses[o["id"]] = o

print("=" * 70)
print(f"SERVER: {cfg['cmd']} {' '.join(cfg['args'])}")
print("=" * 70)
init = responses.get(1, {}).get("result", {})
if init:
    print(f"serverInfo: {init.get('serverInfo')}  protocol: {init.get('protocolVersion')}")

for label, rid in cfg.get("labels", {}).items():
    o = responses.get(rid)
    if not o:
        print(f"\n--- {label} (id={rid}): SEM RESPOSTA")
        continue
    print(f"\n--- {label} (id={rid}) ---")
    if "error" in o:
        print(f"ERROR: {json.dumps(o['error'], ensure_ascii=False)}")
        continue
    res = o.get("result", {})
    if "tools" in res:
        print("tools:", [t["name"] for t in res["tools"]])
    elif "content" in res:
        for c in res["content"]:
            txt = c.get("text", "")
            print(txt[:cfg.get("clip", 1200)])
    else:
        print(json.dumps(res, ensure_ascii=False)[:cfg.get("clip", 1200)])
