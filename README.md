# [catbotbench](https://staring.13000000.xyz)

🚀🚀🚀✨✨ The **ULTIMATE** true **BENCHMARK** ⚡️⚡️ to **finally** 🚀 END **ALL** 🔥🔥 BENCHMARKS (no it's not) (or is it?) (no really it isn't)

---

Okay no this is just a small (~100 lines) extremely specific evaluator to test whether leading LLMs have [Cat Bot](https://catbot.minkos.lol) in their training data.

Interestingly, the huge ones do! It's heavily outdated, so I'm curious to see more models catch up over the next year or two, and be able to answer even more complex queries.

## Usage

1. Download the repository:

```bash
git clone https://github.com/caryph/catbotbench
cd catbotbench
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create an [OpenRouter](https://openrouter.ai/) API key. Make an `.env` file, paste the key there:

```env
OPENROUTER_KEY=sk-or-v1-...
```

4. Run benchmark:

```bash
python3 benchmark/run.py -m <model>
```

| Flag | Long                  | Description                          |
| ---- | --------------------- | ------------------------------------ |
| `-m` | `--model`             | Model, e.g. `deepseek/deepseek-v4-pro`         |
| `-v` | `--validation-model`  | Judge model (default: `google/gemma-4-31b-it`) |
| `-d` | `--debug`             | Will print out each response (disabled by default) |

5. Configure shown models, provider logos and colors in `config.yml`
6. Run your own WebUI:

```bash
python3 -m http.server 8000
```