import pytest

from src.lib.json_logic import evaluate


def test_context_validation():
    rule = {
        "and": [
            {"<": [{"var": "temp"}, 110]},
            {"==": [{"var": "pie.filling"}, "apple"]},
        ]
    }

    assert evaluate(
        rule,
        {"temp": 100, "pie": {"filling": "apple"}},
    )

    assert (
        evaluate(
            rule,
            {"temp": 120, "pie": {"filling": "apple"}},
        )
        is False
    )

    with pytest.raises(ValueError) as e:
        evaluate(
            rule,
            {"temp": 100, "pie": {"some": "apple"}},
        )

    assert str(e.value) == "Invalid context: key 'filling' not found"

    rule2 = {"<": [{"var": "rating.0"}, 100]}

    assert evaluate(
        rule2,
        {"rating": [10], "pie": {"some": "apple"}},
    )

    with pytest.raises(ValueError) as e:
        evaluate(
            rule2,
            {"rating": []},
        )

    assert str(e.value) == "Invalid context: key '0': list index out of range"
