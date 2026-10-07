import json, httpx, pytest
from data_tag import OLLAMA_URL, MODEL

SCHEMA = {"type": "object", "required": ["datasets"],
          "properties": {"datasets": {"type": "array", "items": {
              "type": "object", "required": ["name", "type"],
              "properties": {"name": {"type": "string"},
                             "type": {"type": "string", "enum": ["survey", "other"]}}}}}}

def _ollama_up():
    try:
        names = [m["name"] for m in httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).json()["models"]]
        return MODEL in names
    except Exception:
        return False

@pytest.mark.skipif(not _ollama_up(), reason="Ollama or model not available")
def test_format_schema_returns_valid_json():
    body = {"model": MODEL, "stream": False, "format": SCHEMA,
            "options": {"temperature": 0, "num_ctx": 2048},
            "messages": [{"role": "user", "content":
                "Text: 'We use the American Housing Survey 2015.' List datasets as JSON."}]}
    resp = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=120)
    resp.raise_for_status()
    parsed = json.loads(resp.json()["message"]["content"])
    assert parsed["datasets"] and parsed["datasets"][0]["type"] in ("survey", "other")
