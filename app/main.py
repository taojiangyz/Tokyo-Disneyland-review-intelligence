from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EvidenceItem,
    MetadataResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from app.services.gemini_service import GeminiService
from app.services.rag_service import RagService
from app.logging_config import configure_logging


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_service = RagService()
    app.state.gemini_service = GeminiService()

    try:
        yield
    finally:
        app.state.rag_service.close()


app = FastAPI(
    title="New Aladdin API",
    description="Tokyo Disney review analysis API",
    version="0.3.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "new-aladdin-api",
    }


@app.get(
    "/api/v1/metadata",
    response_model=MetadataResponse,
)
def review_metadata(request: Request) -> dict[str, object]:
    rag_service: RagService = request.app.state.rag_service
    return rag_service.get_metadata()


@app.post(
    "/api/v1/retrieve",
    response_model=RetrieveResponse,
)
def retrieve_reviews(
    request_body: RetrieveRequest,
    request: Request,
) -> RetrieveResponse:
    rag_service: RagService = request.app.state.rag_service
    date_from = request_body.date_from.isoformat() if request_body.date_from else None
    date_to = request_body.date_to.isoformat() if request_body.date_to else None
    ranked_results, debug_info = rag_service.retrieve_for_evaluation(
        query=request_body.query,
        mode=request_body.mode,
        regions=request_body.regions,
        min_rating=request_body.min_rating,
        max_rating=request_body.max_rating,
        date_from=date_from,
        date_to=date_to,
        limit=request_body.top_k,
        candidate_limit=request_body.candidate_limit,
    )
    evidence = [
        EvidenceItem(
            review_id=str((point.payload or {}).get("review_id", "")),
            region=(point.payload or {}).get("region"),
            rating=(point.payload or {}).get("rating"),
            review_date=(point.payload or {}).get("review_date"),
            text=str((point.payload or {}).get("text", "")),
            rrf_score=float(point.score),
            reranker_score=(
                float(score) if request_body.mode == "hybrid_rerank" else None
            ),
        )
        for point, score in ranked_results
    ]
    filters = {
        "regions": request_body.regions,
        "min_rating": request_body.min_rating,
        "max_rating": request_body.max_rating,
        "date_from": date_from,
        "date_to": date_to,
    }
    return RetrieveResponse(
        query=request_body.query,
        mode=request_body.mode,
        evidence=evidence,
        filters=filters,
        trace=debug_info,
    )


@app.post(
    "/api/v1/analyze",
    response_model=AnalyzeResponse,
)
def analyze_reviews(
    request_body: AnalyzeRequest,
    request: Request,
) -> AnalyzeResponse:
    request_start = perf_counter()

    rag_service: RagService = (
        request.app.state.rag_service
    )

    date_from = (
        request_body.date_from.isoformat()
        if request_body.date_from
        else None
    )
    date_to = (
        request_body.date_to.isoformat()
        if request_body.date_to
        else None
    )
    selected_regions = request_body.selected_regions()

    ranked_results, debug_info = (
        rag_service.retrieve_for_evaluation(
            query=request_body.query,
            mode="dense",
            regions=selected_regions,
            min_rating=request_body.min_rating,
            max_rating=request_body.max_rating,
            date_from=date_from,
            date_to=date_to,
            limit=request_body.top_k,
        )
    )

    evidence_blocks: list[str] = []

    for point, dense_score in ranked_results:
        payload = point.payload or {}

        evidence_blocks.append(
            "\n".join(
                [
                    f"[{payload.get('review_id')}]",
                    f"Region: {payload.get('region')}",
                    f"Rating: {payload.get('rating')}",
                    f"Date: {payload.get('review_date')}",
                    f"Dense similarity score: {float(dense_score):.4f}",
                    f"Review: {payload.get('text')}",
                ]
            )
        )

    evidence_text = "\n\n".join(evidence_blocks)

    gemini_service: GeminiService = (
        request.app.state.gemini_service
    )

    generation_start = perf_counter()

    generation_status = "completed"

    if not ranked_results:
        answer = (
            "No reviews matched the selected filters, so there is "
            "not enough evidence to answer this question."
        )
        generation_status = "skipped_no_evidence"
    else:
        try:
            answer = gemini_service.generate_answer(
                query=request_body.query,
                evidence_text=evidence_text,
            )
        except Exception:
            logger.exception("Answer generation failed")
            answer = (
                "Answer generation is temporarily unavailable. "
                "The retrieved supporting reviews are still shown below."
            )
            generation_status = "degraded"

    generation_ms = (
        perf_counter() - generation_start
    ) * 1000

    evidence: list[EvidenceItem] = []

    for point, _dense_score in ranked_results:
        payload = point.payload or {}

        evidence.append(
            EvidenceItem(
                review_id=str(
                    payload.get("review_id", "")
                ),
                region=payload.get("region"),
                rating=payload.get("rating"),
                review_date=payload.get("review_date"),
                text=str(payload.get("text", "")),
                rrf_score=float(point.score),
                reranker_score=None,
            )
        )

    filters = {
        "regions": selected_regions,
        "min_rating": request_body.min_rating,
        "max_rating": request_body.max_rating,
        "date_from": date_from,
        "date_to": date_to,
    }

    trace = {
        "intent": {
            "task": "review_analysis",
            "query_language": "zh"
            if any(
                "\u4e00" <= char <= "\u9fff"
                for char in request_body.query
            )
            else "non_zh",
        },
        "filters": filters,
        "retrieval": {
            "mode": "dense",
            "embedding_model": "BAAI/bge-m3",
            "dense_vector": True,
            "sparse_vector": False,
            "fusion_method": None,
            "candidate_limit": request_body.top_k,
            "candidate_count": debug_info["hybrid_candidate_count"],
        },
        "reranking": {
            "enabled": False,
            "model": None,
            "input_count": 0,
            "output_count": (
                debug_info["final_selected_count"]
            ),
            "selected_review_ids": [
                item.review_id for item in evidence
            ],
            "ranking_changes": [],
        },
        "generation": {
            "provider": "Gemini",
            "model": gemini_service.last_model_name,
            "evidence_count": len(evidence),
            "prompt_version": "v1",
            "status": generation_status,
        },
        "timing_ms": {
            **debug_info.get("timing_ms", {}),
            "generation": round(generation_ms, 2),
            "total": round(
                (perf_counter() - request_start) * 1000,
                2,
            ),
        },
    }

    return AnalyzeResponse(
        query=request_body.query,
        answer=answer,
        evidence=evidence,
        filters=filters,
        trace=trace,
    )
