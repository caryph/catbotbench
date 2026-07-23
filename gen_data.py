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
SVG_OUT = ROOT / "assets" / "leaderboard.svg"
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

    write_svg(data)


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _short_name(model_id):
    parts = model_id.split("/")
    return parts[1] if len(parts) > 1 else model_id


def _b64(path):
    import base64
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def write_svg(data):
    """Render a dependency-free leaderboard SVG for the README.

    GitHub renders repo-relative SVGs inline in README.md via <img>.
    SVGs loaded as <img> are in secure-static mode: external URLs are
    blocked, but data: URIs are allowed, so provider logos are embedded
    as base64 PNGs. Top 5 only, highest->lowest.
    """
    models = sorted(data["models"], key=lambda m: -m["score"])[:5]
    n = len(models)
    if not n:
        return

    W = 780
    MARGIN_L = 232           # bar area starts here
    BAR_MAX = 452            # bar area width = 100%
    BAR_X0 = MARGIN_L
    BAR_X1 = MARGIN_L + BAR_MAX
    ROW_H = 44
    TOP = 78
    BOTTOM = 34
    H = TOP + n * ROW_H + BOTTOM
    LOGO = 20
    FONT = "-apple-system, Segoe UI, Inter, Roboto, sans-serif"

    defs = (
        "<defs>"
        "<linearGradient id='bg' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0%' stop-color='#0a0908'/><stop offset='100%' stop-color='#1a1512'/></linearGradient>"
        "<linearGradient id='title' x1='0' y1='0' x2='1' y2='0'>"
        "<stop offset='0%' stop-color='#d4863a'/><stop offset='100%' stop-color='#ff9f43'/></linearGradient>"
        "</defs>"
    )
    bg = f"<rect width='{W}' height='{H}' fill='url(#bg)'/>"
    title = (
        f"<text x='24' y='44' fill='url(#title)' font-family='{FONT}' "
        f"font-size='30' font-weight='800' letter-spacing='-0.5'>catbotbench</text>"
        f"<rect x='24' y='54' width='120' height='3' rx='1.5' fill='#d4863a'/>"
        f"<text x='24' y='70' fill='#6e645b' font-family='{FONT}' font-size='10'>"
        f"% correct \u00b7 top {n} \u00b7 highest to lowest</text>"
    )

    # vertical grid tiles at 0,20,40,60,80,100
    grid = []
    chart_top = TOP
    chart_bot = TOP + n * ROW_H
    for pct in (0, 20, 40, 60, 80, 100):
        gx = BAR_X0 + round(pct / 100 * BAR_MAX)
        grid.append(
            f"<line x1='{gx}' y1='{chart_top}' x2='{gx}' y2='{chart_bot}' "
            f"stroke='#352f2a' stroke-width='1' stroke-dasharray='3 4'/>"
        )
        grid.append(
            f"<text x='{gx}' y='{chart_top - 6}' fill='#6e645b' font-family='{FONT}' "
            f"font-size='9' text-anchor='middle'>{pct}</text>"
        )

    rows = []
    for i, m in enumerate(models):
        y = TOP + i * ROW_H
        pct = (m["score"] / m["total"]) * 100 if m["total"] else 0
        bw = max(2, round(pct / 100 * BAR_MAX))
        color = m.get("color") or DEFAULT_COLOR
        name = _esc(_short_name(m["model"]))
        cy = y + ROW_H // 2
        # logo as base64 data URI (renders under SVG secure-static mode)
        if m.get("logo"):
            lp = ROOT / "logos" / m["logo"]
            if lp.exists():
                uri = f"data:image/png;base64,{_b64(lp)}"
                rows.append(
                    f"<image x='20' y='{cy - LOGO//2}' width='{LOGO}' height='{LOGO}' "
                    f"href='{uri}' preserveAspectRatio='xMidYMid meet'/>"
                )
                name_x = 48
            else:
                name_x = 20
        else:
            name_x = 20
        rows.append(
            f"<text x='{name_x}' y='{cy + 4}' fill='#a0978e' font-family='{FONT}' "
            f"font-size='13' text-anchor='start'>{name}</text>"
        )
        rows.append(
            f"<rect x='{BAR_X0}' y='{y + 8}' width='{bw}' height='{ROW_H - 16}' rx='5' fill='{color}'/>"
        )
        rows.append(
            f"<text x='{BAR_X0 + bw + 8}' y='{cy + 4}' fill='#e8e4df' font-family='{FONT}' "
            f"font-size='13' font-weight='600'>{round(pct)}%</text>"
        )

    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' "
        f"viewBox='0 0 {W} {H}' role='img' aria-label='catbotbench leaderboard'>"
        f"{defs}{bg}{title}{''.join(grid)}{''.join(rows)}</svg>"
    )
    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {SVG_OUT} ({SVG_OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
