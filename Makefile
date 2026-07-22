.PHONY: data eval serve clean

PORT ?= 8000

data:
	python3 gen_data.py

eval:
	python3 benchmark/run.py $(ARGS)

serve: data
	@echo "serving at http://localhost:$(PORT)"
	python3 -m http.server $(PORT)

clean:
	rm -f data.json
