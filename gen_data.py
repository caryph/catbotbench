#!/usr/bin/env python3
"""Generate the single universal source JSON for the CatBotBench site.

Reads:
  site/config.yml            - providers (color/logo) + ordered model ids to show
  benchmark/questions.json    - the benchmark questions + true answers
  benchmark/eval/*.json       - per-model results (written by benchmark/run.py)
Writes:
  data.json                   - {models, questions} consumed by index.html

index.html fetches this file at runtime; no data is baked into the HTML.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVAL_DIR = ROOT / "benchmark" / "eval"
QUESTIONS_FILE = ROOT / "benchmark" / "questions.json"
CONFIG_FILE = ROOT / "config.yml"
OUT = ROOT / "data.json"
DEFAULT_COLOR = "#ff9f43"


def _strip_comment(line):
    """Remove a trailing # comment, ignoring # inside quotes."""
    out = []
    in_q = None
    for ch in line:
        if in_q:
            out.append(ch)
            if ch == in_q:
                in_q = None
        elif ch in "\"'":
            in_q = ch
            out.append(ch)
        elif ch == '#':
            break
        else:
            out.append(ch)
    return ''.join(out)


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _parse_simple_yaml(text):
    """Fallback parser for the fixed config shape (no PyYAML available):
    providers: / models: with 2-space indentation."""
    cfg = {"providers": {}, "models": []}
    section = None
    cur_provider = None
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        if indent == 0 and s.endswith(":"):
            section = s[:-1]
            cur_provider = None
            continue
        if section == "providers":
            if indent == 2 and s.endswith(":"):
                cur_provider = s[:-1]
                cfg["providers"][cur_provider] = {}
            elif indent >= 4 and cur_provider is not None and ":" in s:
                k, _, v = s.partition(":")
                cfg["providers"][cur_provider][k.strip()] = _unquote(v)
        elif section == "models":
            if indent == 2 and s.startswith("- "):
                cfg["models"].append(_unquote(s[2:]))
    return cfg


def load_config():
    text = CONFIG_FILE.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        cfg = yaml.safe_load(text) or {}
    except ImportError:
        cfg = _parse_simple_yaml(text)
    providers = cfg.get("providers") or {}
    out = []
    for model_id in (cfg.get("models") or []):
        provider = model_id.split("/", 1)[0]
        p = providers.get(provider) or {}
        out.append({
            "id": model_id,
            "color": (p.get("color") or DEFAULT_COLOR).strip(),
            "logo": p.get("logo") or None,
        })
    return out


def eval_filename(model_id):
    # mirrors benchmark/run.py log_filename derivation
    return model_id.replace("/", "_").replace(":", "-") + ".json"


def main():
    config = load_config()
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))

    models = []
    for entry in config:
        path = EVAL_DIR / eval_filename(entry["id"])
        if not path.exists():
            print(f"warn: no eval file for {entry['id']} ({path})", file=sys.stderr)
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        per_q = {row["question"]: row["correct"] for row in d["data"]}
        models.append({
            "model": d["eval_model"],
            "score": d["score"],
            "total": len(d["data"]),
            "cost": d["cost"],
            "time": d["time"],
            "per_q": per_q,
            "color": entry["color"],
            "logo": entry["logo"],
        })

    # ascending: lowest score first, highest last; ties keep config.yml order
    models.sort(key=lambda m: m["score"])

    q_stats = []
    for q in questions:
        n = sum(1 for m in models if m["per_q"].get(q["q"]))
        q_stats.append({"q": q["q"], "a": q["a"], "correct": n, "total": len(models)})

    data = {"models": models, "questions": q_stats}
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(models)} models, {len(questions)} questions)")


if __name__ == "__main__":
    main()
