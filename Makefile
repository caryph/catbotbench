.PHONY: eval serve

PORT ?= 8000

eval:
	python3 src/run.py $(ARGS)

serve:
	python3 scripts/gen_site.py
	@echo "serving at http://localhost:$(PORT)"
	python3 -m http.server $(PORT)
