PYTHON ?= .venv/bin/python

.PHONY: validate-data prepare-data rebuild-index test regression annotation-pool evaluate-retrieval run-api run-ui

validate-data:
	$(PYTHON) src/prepare_data.py --validate-only

prepare-data:
	$(PYTHON) src/prepare_data.py

rebuild-index: prepare-data
	$(PYTHON) src/build_index.py --yes

test:
	$(PYTHON) -m pytest -q

regression:
	$(PYTHON) scripts/run_regression.py

annotation-pool:
	$(PYTHON) scripts/export_annotation_pool.py

evaluate-retrieval:
	$(PYTHON) scripts/evaluate_retrieval.py

run-api:
	.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

run-ui:
	.venv/bin/streamlit run demo_v2.py --server.port 8501
