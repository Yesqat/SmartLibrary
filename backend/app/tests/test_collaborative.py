from uuid import uuid4

from app.ai.recommendations.collaborative import ItemNeighbors
from app.ai.recommendations.evaluate import evaluate


def test_neighbors_require_real_shared_support_and_exclude_consumed():
    a, b, c = uuid4(), uuid4(), uuid4()
    model = ItemNeighbors([{a, b}, {a, b}, {a, c}])
    assert model.rank({a}, 10) == [b]
    assert model.rank({a, b}, 10) == []
    assert model.rank(set(), 10) == []


def test_sparse_evaluation_does_not_invent_metrics():
    result = evaluate({uuid4(): [uuid4(), uuid4(), uuid4()]})
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["metrics"] is None
    assert result["serving_enabled"] is False
