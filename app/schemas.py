from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnalyzeRequest(BaseModel):
    query: str = Field(
        min_length=3,
        description="User's review-analysis question",
    )
    region: str | None = Field(
        default=None,
        description="Legacy single-market filter: CN, HK, or KR",
    )
    regions: list[str] = Field(
        default_factory=list,
        description="Optional market filters: CN, HK, and/or KR",
    )
    min_rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    max_rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    date_from: date | None = None
    date_to: date | None = None
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    @model_validator(mode="after")
    def validate_filters(self) -> "AnalyzeRequest":
        allowed_regions = {"CN", "HK", "KR"}
        selected_regions = set(self.regions)

        if self.region:
            selected_regions.add(self.region)

        invalid_regions = selected_regions - allowed_regions

        if invalid_regions:
            invalid = ", ".join(sorted(invalid_regions))
            raise ValueError(f"Unsupported market code(s): {invalid}")

        if (
            self.min_rating is not None
            and self.max_rating is not None
            and self.min_rating > self.max_rating
        ):
            raise ValueError("min_rating cannot exceed max_rating")

        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from cannot be after date_to")

        return self

    def selected_regions(self) -> list[str]:
        values = [*self.regions]

        if self.region and self.region not in values:
            values.append(self.region)

        return values


class EvidenceItem(BaseModel):
    review_id: str
    region: str | None = None
    rating: float | None = None
    review_date: str | None = None
    text: str
    rrf_score: float | None = None
    reranker_score: float | None = None


class AnalyzeResponse(BaseModel):
    query: str
    answer: str
    evidence: list[EvidenceItem]
    filters: dict[str, object]
    trace: dict[str, object]


class MarketMetadata(BaseModel):
    code: str
    label: str
    count: int


class MetadataResponse(BaseModel):
    total_reviews: int
    markets: list[MarketMetadata]
    min_rating: int
    max_rating: int
    min_date: date
    max_date: date
    evidence_count_options: list[int]


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=3)
    mode: Literal["dense", "hybrid", "hybrid_rerank"]
    regions: list[str] = Field(default_factory=list)
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_rating: int | None = Field(default=None, ge=1, le=5)
    date_from: date | None = None
    date_to: date | None = None
    top_k: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_filters(self) -> "RetrieveRequest":
        invalid_regions = set(self.regions) - {"CN", "HK", "KR"}
        if invalid_regions:
            invalid = ", ".join(sorted(invalid_regions))
            raise ValueError(f"Unsupported market code(s): {invalid}")
        if self.min_rating and self.max_rating and self.min_rating > self.max_rating:
            raise ValueError("min_rating cannot exceed max_rating")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")
        return self


class RetrieveResponse(BaseModel):
    query: str
    mode: str
    evidence: list[EvidenceItem]
    filters: dict[str, object]
    trace: dict[str, object]
