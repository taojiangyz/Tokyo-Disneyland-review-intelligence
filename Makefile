PYTHON ?= .venv/bin/python

.PHONY: validate-data prepare-data rebuild-index test regression annotation-pool evaluate-retrieval translations topic-labels topic-audit-sample evaluate-topic-labels run-api run-ui run-annotation run-topic-audit docker-up docker-down

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

topic-labels:
	$(PYTHON) scripts/build_topic_labels.py

topic-audit-sample:
	$(PYTHON) scripts/export_topic_audit.py

evaluate-topic-labels:
	$(PYTHON) scripts/evaluate_topic_labels.py

run-api:
	.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

run-ui:
	.venv/bin/streamlit run demo_v2.py --server.port 8501

run-annotation:
	.venv/bin/streamlit run annotation_app.py --server.port 8502

run-topic-audit:
	.venv/bin/streamlit run topic_annotation_app.py --server.port 8504

docker-up:
	docker compose up --build

docker-down:
	docker compose down
