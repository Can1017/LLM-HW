import json, urllib.request, urllib.error

from api_probe import load_env

env = load_env()
base = env["BASE_URL"].rstrip("/")
key = env["API_KEY"]


def post(path, body, headers=None):
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]
    except Exception as e:
        return "ERR", repr(e)[:200]


s, b = post("/v1/chat/completions", {"model": "qwen3.8-27b", "messages": [{"role": "user", "content": "Say hi in Chinese"}], "max_completion_tokens": 100})
print("QWEN", s, b[:800])
print()
s, b = post("/v1/chat/completions", {"model": "gpt-5.4", "messages": [{"role": "user", "content": "Say hi"}], "max_completion_tokens": 20, "temperature": 0})
print("GPT5.4 temp0", s, b[:300])
print()
for path in ["/v1beta/models/gemini-3.1-pro-preview:generateContent?key=" + key]:
    s, b = post(path, {"contents": [{"parts": [{"text": "Say hi"}]}]})
    print("GEMINI", s, b[:300])
