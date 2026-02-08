PY=uv run python

.PHONY: test sdk

test:
	uv run pytest

sdk:
	cd src && $(PY) ../scripts/generate_sdks.py
