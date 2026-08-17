PYTHON ?= .venv/bin/python

.PHONY: validate-data prepare-data rebuild-index test regression annotation-pool evaluate-retrieval translations run-api run-ui run-annotation

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

translations:
	$(PYTHON) -m scripts.build_translation_cache

run-api:
	.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

run-ui:
	.venv/bin/streamlit run demo_v2.py --server.port 8501

run-annotation:
	.venv/bin/streamlit run annotation_app.py --server.port 8502
