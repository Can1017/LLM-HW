import json, urllib.request, urllib.error

from api_probe import load_env

env = load_env()
BASE = env["BASE_URL"].rstrip("/")
KEY = env["API_KEY"]


def post(path, body, headers=None):
    h = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]
    except Exception as e:
        return "ERR", repr(e)[:200]


for m in ["gpt-6.1-sol", "gpt-6-luna", "gemini-4-argon", "claude-opus-5-5", "deepseek-v4.1-flash-1017", "glm-5.3-flash"]:
    if m.startswith("gemini"):
        s, b = post(f"/v1beta/models/{m}:generateContent?key={KEY}",
                    {"contents": [{"role": "user", "parts": [{"text": "Say hi"}]}]})
    elif m.startswith("claude"):
        s, b = post("/v1/messages", {"model": m, "max_tokens": 30, "messages": [{"role": "user", "content": "Say hi"}]},
                    {"x-api-key": KEY, "anthropic-version": "2023-06-01"})
    else:
        s, b = post("/v1/chat/completions", {"model": m, "messages": [{"role": "user", "content": "Say hi"}],
                                            "max_completion_tokens": 30, "temperature": 0})
    print("=====", m, s)
    print(b[:400].replace("\n", " "))
