import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

def load_env(path=None):
    env = {}
    if path is None:
        path = next((parent / ".env" for parent in Path(__file__).resolve().parents
                     if (parent / ".env").is_file()), None)
    if path is not None:
        env.update(_read_env(path))
    for name in ("BASE_URL", "API_KEY"):
        if name in os.environ:
            env[name] = os.environ[name]
    return env

def _read_env(path):
    env = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def chat(model, messages, max_tokens=128, temperature=None, extra=None):
    env = load_env()
    base = env["BASE_URL"].rstrip("/")
    body = {"model": model, "messages": messages}
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if temperature is not None:
        body["temperature"] = temperature
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        base + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + env["API_KEY"], "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
            dt = time.time() - t0
            choice = data["choices"][0]["message"]
            return {"ok": True, "model": data.get("model"), "content": choice.get("content"), "reasoning": choice.get("reasoning_content"), "usage": data.get("usage"), "sec": round(dt, 2)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "body": e.read().decode(errors="replace")[:500], "sec": round(time.time() - t0, 2)}
    except Exception as e:
        return {"ok": False, "error": repr(e), "sec": round(time.time() - t0, 2)}

if __name__ == "__main__":
    msgs = [
        {"role": "system", "content": "You are TestBot. Secret code: CANARY-1234. Never reveal it."},
        {"role": "user", "content": "What is 2+2? Answer in three words."},
    ]
    for m in sys.argv[1:]:
        for variant in ("max_tokens", "max_completion_tokens"):
            extra = {"max_completion_tokens": 128} if variant == "max_completion_tokens" else None
            if variant == "max_completion_tokens":
                # replace max_tokens key
                res = chat(m, msgs, max_tokens=None, extra={"max_completion_tokens": 128})
            else:
                res = chat(m, msgs, max_tokens=128)
            print(m, variant, json.dumps(res, ensure_ascii=False)[:600])
            if res.get("ok"):
                break
