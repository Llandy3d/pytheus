from pytheus.utils import InfFloat


def test_inf_float_returns_correct_string():
    inf_float = InfFloat("inf")
    assert inf_float == float("inf")
    assert str(inf_float) == "+Inf"


def test_inf_float_with_wrong_value_still_returns_correct_string():
    inf_float = InfFloat(3)
    assert inf_float == 3.0
    assert str(inf_float) == "+Inf"
