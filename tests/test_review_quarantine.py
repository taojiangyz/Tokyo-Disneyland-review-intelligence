import json

from qdrant_client import QdrantClient, models

from app.services import review_quarantine
from app.services.rag_service import build_filter


def test_exclusion_applies_before_limit_and_preserves_filters():
    client = QdrantClient(':memory:')
    try:
        client.create_collection('test', vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE))
        records = [
            ('221035459', 'KR', 5, [1., 0.]),
            ('eligible', 'KR', 4, [0.9, 0.1]),
            ('other_market', 'CN', 5, [1., 0.]),
            ('low_rating', 'KR', 1, [1., 0.]),
        ]
        client.upsert('test', points=[models.PointStruct(id=i, vector=vector, payload={'review_id':rid,'region':region,'rating':rating}) for i,(rid,region,rating,vector) in enumerate(records)])
        result = client.query_points('test', query=[1.,0.], query_filter=build_filter(regions=['KR'], min_rating=4), limit=1).points
        assert [p.payload['review_id'] for p in result] == ['eligible']
        unrestricted = client.query_points('test', query=[1.,0.], query_filter=build_filter(), limit=10).points
        assert '221035459' not in [p.payload['review_id'] for p in unrestricted]
        assert client.count('test').count == 4  # Quarantine never deletes source points.
    finally:
        client.close()


def test_release_is_reversible_without_rebuilding_index(tmp_path, monkeypatch):
    path = tmp_path / 'quarantine.json'
    monkeypatch.setattr(review_quarantine, 'QUARANTINE_PATH', path)
    for status, expected in [('excluded',['one']),('released',[])]:
        path.write_text(json.dumps({'reviews':[{'review_id':'one','status':status}]}))
        assert review_quarantine.excluded_review_ids() == expected
    assert build_filter() is None
