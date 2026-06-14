.venv:
	uv venv

.PHONY: sync
sync: .venv
	uv sync

.PHONY: run
run: .venv
	uv run python src/main.py

.PHONY: package
package: .venv
	uv pip install -e .

.PHONY: clean
clean:
	rm -rf .venv