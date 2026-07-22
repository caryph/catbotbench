#!/usr/bin/env python3
"""Generate index.html for the CatBotBench site.

Reads:
  config.yml  - providers (color/logo) + ordered list of model ids to display
  data.json   - the benchmark questions + true answers
  eval/*.json - per-model results (written by src/run.py)
Writes:
  index.html  - self-contained site (logos referenced from logos/)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "eval"
DATA_FILE = ROOT / "data.json"
CONFIG_FILE = ROOT / "config.yml"
OUT = ROOT / "index.html"
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
    # mirrors src/run.py log_filename derivation
    return model_id.replace("/", "_").replace(":", "-") + ".json"


def main():
    config = load_config()
    questions = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    models = []
    for entry in config:
        path = EVAL_DIR / eval_filename(entry["id"])
        if not path.exists():
            print(f"warn: no eval file for {entry['id']} (eval/{path.name})", file=sys.stderr)
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

    data_json = json.dumps({"models": models, "questions": q_stats}, ensure_ascii=False)

    PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CatBotBench</title>
<meta name="description" content="CatBotBench — how well do LLMs know Discord Cat Bot?">
<style>
  :root {
    --bg: #141518;
    --bg-elev: #1c1e22;
    --bg-bar: #2a2d33;
    --fg: #e6e7ea;
    --fg-dim: #9a9da4;
    --fg-faint: #6b6e75;
    --accent: #ff9f43;
    --border: #2a2d33;
    --grid: #303239;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--fg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 920px; margin: 0 auto; padding: 0 24px; }

  header.hero { padding: 88px 0 48px; }
  .hero .eyebrow {
    color: var(--accent);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin: 0 0 14px;
  }
  .hero h1 {
    font-size: clamp(2.4rem, 6vw, 3.4rem);
    line-height: 1.05;
    margin: 0 0 18px;
    letter-spacing: -0.02em;
  }
  .hero p.lead {
    color: var(--fg-dim);
    font-size: 1.1rem;
    max-width: 620px;
    margin: 0;
  }

  section { padding: 40px 0; border-top: 1px solid var(--border); }
  h2 {
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0 0 6px;
    letter-spacing: -0.01em;
  }
  .section-sub { color: var(--fg-faint); font-size: 0.9rem; margin: 0 0 28px; }

  /* vertical bar chart: bars grow upward, gridlines mark every 20% (max = 5/5) */
  .chart {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    height: 320px;
    padding: 30px 4px 0;
    border-bottom: 1px solid var(--grid);
    background-image: repeating-linear-gradient(to top, var(--grid) 0 1px, transparent 1px 20%);
    background-origin: content-box;
    background-clip: content-box;
    overflow-x: auto;
  }
  .col {
    flex: 1 1 0;
    min-width: 56px;
    height: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }
  .bar {
    width: 80%;
    max-width: 44px;
    background: var(--bar-color, var(--accent));
    border-radius: 6px 6px 0 0;
    height: 0;
    transition: height 0.9s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    min-height: 3px;
  }
  .score-num {
    position: absolute;
    top: -22px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--fg-dim);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .labels {
    display: flex;
    gap: 10px;
    padding: 10px 4px 0;
  }
  .label-block {
    flex: 1 1 0;
    min-width: 56px;
    text-align: center;
  }
  .logo {
    width: 20px; height: 20px;
    object-fit: contain;
    margin: 0 auto 4px;
    display: block;
  }
  .model-name {
    font-size: 0.72rem;
    color: var(--fg-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* questions */
  details {
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 10px;
    overflow: hidden;
  }
  details > summary {
    cursor: pointer;
    padding: 16px 18px;
    font-weight: 500;
    list-style: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  details > summary::-webkit-details-marker { display: none; }
  details > summary::before {
    content: "+";
    color: var(--accent);
    font-weight: 600;
    font-size: 1.05rem;
    width: 1ch;
    display: inline-block;
  }
  details[open] > summary::before { content: "\\2212"; }
  .q-meta { color: var(--fg-faint); font-size: 0.78rem; font-weight: 400; white-space: nowrap; }
  .q-body { padding: 0 18px 18px 18px; color: var(--fg-dim); font-size: 0.92rem; }
  .q-body .label { color: var(--fg-faint); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 10px 0 4px; }
  .q-body .answer { color: var(--fg); white-space: pre-wrap; }

  footer {
    border-top: 1px solid var(--border);
    padding: 36px 0 56px;
    color: var(--fg-faint);
    font-size: 0.82rem;
  }
  footer a { color: var(--fg-dim); text-decoration: none; }
  footer a:hover { color: var(--accent); }
</style>
</head>
<body>
  <header class="hero">
    <div class="wrap">
      <p class="eyebrow">A joke LLM benchmark</p>
      <h1>CatBotBench</h1>
      <p class="lead">
        Five absurdly specific questions about <em>Discord Cat Bot</em>, thrown at
        a pile of language models. None of them have any business knowing this stuff,
        so the results are exactly as embarrassing as you'd expect.
        Five questions, five points. Higher is better. Good luck out there.
      </p>
    </div>
  </header>

  <main class="wrap">
    <section id="scores">
      <h2>Model scores</h2>
      <p class="section-sub">Percent correct, lowest to highest. Top line is the max (5/5).</p>
      <div class="chart" id="chart"></div>
      <div class="labels" id="labels"></div>
    </section>

    <section id="questions">
      <h2>The questions</h2>
      <p class="section-sub">What every model was asked. Tap to reveal the real answer.</p>
      <div id="qlist"></div>
    </section>
  </main>

  <footer>
    <div class="wrap">
      CatBotBench &middot; a deeply unserious evaluation &middot;
      <a href="https://github.com/tallrocksawakesadhearts/catbotbench">source</a>
    </div>
  </footer>

<script id="bench-data" type="application/json">__DATA__</script>
<script>
  const data = JSON.parse(document.getElementById('bench-data').textContent);

  const chart = document.getElementById('chart');
  const labels = document.getElementById('labels');
  data.models.forEach(m => {
    const pct = (m.score / m.total) * 100;
    const parts = m.model.split('/');
    const name = parts.slice(1).join('/') || m.model;
    const col = document.createElement('div');
    col.className = 'col';
    col.style.setProperty('--bar-color', m.color || '#ff9f43');
    col.innerHTML = `
      <div class="bar" data-h="${pct}">
        <span class="score-num">${Math.round(pct)}%</span>
      </div>`;
    chart.appendChild(col);

    const lb = document.createElement('div');
    lb.className = 'label-block';
    const logoHtml = m.logo
      ? `<img class="logo" src="logos/${m.logo}" alt="" loading="lazy">`
      : '';
    lb.innerHTML = `${logoHtml}<div class="model-name" title="${m.model}">${name}</div>`;
    labels.appendChild(lb);
  });
  requestAnimationFrame(() => {
    document.querySelectorAll('.bar').forEach(el => { el.style.height = el.dataset.h + '%'; });
  });

  const qlist = document.getElementById('qlist');
  data.questions.forEach((q, i) => {
    const d = document.createElement('details');
    d.innerHTML = `
      <summary>
        <span>${i+1}. ${q.q.replace(/</g,'&lt;')}</span>
        <span class="q-meta">${q.correct}/${q.total} correct</span>
      </summary>
      <div class="q-body">
        <div class="label">Answer</div>
        <div class="answer">${q.a.replace(/</g,'&lt;')}</div>
      </div>`;
    qlist.appendChild(d);
  });
</script>
</body>
</html>
"""

    OUT.write_text(PAGE.replace("__DATA__", data_json), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(models)} models, {len(questions)} questions)")


if __name__ == "__main__":
    main()
