import os, json, time, urllib.request
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
try:
    _opts = types.HttpOptions(timeout=12000, retry_options=types.HttpRetryOptions(attempts=1))
except Exception:
    _opts = types.HttpOptions(timeout=12000)
gclient = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=_opts)

GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ = "https://api.groq.com/openai/v1"
_groq_model = os.getenv("GROQ_MODEL")
_gem_models = None
_gem_good = None

def embed(text: str) -> list[float]:
    last = None
    for attempt in range(4):
        try:
            r = gclient.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            return r.embeddings[0].values
        except Exception as e:
            last = e
            time.sleep(1 + attempt)
    raise last

# ---------- Groq ----------
def _groq_req(path, body=None):
    headers = {"Authorization": "Bearer " + GROQ_KEY,
               "Content-Type": "application/json",
               "User-Agent": "memory-agent/1.0"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(GROQ + path, data, headers)
    return json.load(urllib.request.urlopen(req, timeout=30))

def _pick_groq_model():
    global _groq_model
    if _groq_model:
        return _groq_model
    ids = [m["id"] for m in _groq_req("/models")["data"]]
    skip = ("whisper", "tts", "guard", "playai", "embed", "orpheus")
    ids = [i for i in ids if not any(s in i for s in skip)]
    for pref in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
        if pref in ids:
            _groq_model = pref
            break
    else:
        _groq_model = ids[0]
    print("GROQ MODEL:", _groq_model)
    return _groq_model

def _groq(prompt, as_json=False):
    body = {"model": _pick_groq_model(),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3}
    if as_json:
        body["response_format"] = {"type": "json_object"}
    return _groq_req("/chat/completions", body)["choices"][0]["message"]["content"]

# ---------- Gemini (backup) ----------
def _gemini(prompt, as_json=False):
    global _gem_models, _gem_good
    if _gem_models is None:
        names = [m.name.replace("models/", "") for m in gclient.models.list()
                 if "generateContent" in (m.supported_actions or [])]
        skip = ("image", "tts", "live", "audio", "embedding", "robotics", "computer")
        flash = [n for n in names if "flash" in n and not any(s in n for s in skip)]
        flash.sort(key=lambda n: (n != "gemini-3.8-flash", "lite" not in n, n))
        _gem_models = flash[:3]
    cfg = types.GenerateContentConfig(response_mime_type="application/json") if as_json else None
    order = ([_gem_good] if _gem_good else []) + [m for m in _gem_models if m != _gem_good]
    last = None
    for model in order:
        try:
            r = gclient.models.generate_content(model=model, contents=prompt, config=cfg)
            _gem_good = model
            return r.text
        except Exception as e:
            last = e
            print("GEMINI FAIL", model, str(e)[:60])
    raise last

def _text(prompt, as_json=False):
    if GROQ_KEY:
        try:
            return _groq(prompt, as_json)
        except Exception as e:
            print("GROQ FAIL", str(e)[:80])
    return _gemini(prompt, as_json)

def generate(prompt: str) -> str:
    return _text(prompt)

def generate_json(prompt: str):
    try:
        data = json.loads(_text(prompt, as_json=True))
    except Exception:
        return []
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data] if data.get("content") else []
    return data if isinstance(data, list) else []
