from lumen.eval.cost import estimate_cost


def test_estimate_cost_sonnet_mtok() -> None:
    assert estimate_cost(1_000_000, 0, "claude-sonnet-4-5") == 3.0
    assert estimate_cost(0, 1_000_000, "claude-sonnet-4-5") == 15.0
    assert estimate_cost(1_000_000, 1_000_000, "claude-sonnet-4-5") == 18.0


def test_estimate_cost_unknown_model_falls_back() -> None:
    v = estimate_cost(1_000_000, 1_000_000, "some-other-model")
    assert v == 18.0
