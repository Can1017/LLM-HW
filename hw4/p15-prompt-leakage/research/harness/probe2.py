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
            return r.status, r.read().decode()[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]
    except Exception as e:
        return "ERR", repr(e)[:200]


print("--- anthropic /v1/messages ---")
print(post("/v1/messages", {"model": "claude-sonnet-4-6", "max_tokens": 32,
                            "messages": [{"role": "user", "content": "Say hi"}]},
           {"x-api-key": key, "anthropic-version": "2023-06-01"}))
print("--- openai format other models ---")
for m in ["qwen3.8-27b", "glm-5.3", "gemini-4-argon", "gpt-6-astra", "ernie-4.5-turbo-128k"]:
    s, b = post("/v1/chat/completions", {"model": m, "messages": [{"role": "user", "content": "Say hi"}],
                                        "max_completion_tokens": 20})
    print(m, s, b[:180].replace("\n", " "))
