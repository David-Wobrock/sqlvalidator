from sqlvalidator.grammar.tokeniser import (
    get_tokens_until_not_in,
    get_tokens_until_one_of,
    split_with_sep,
    to_tokens,
)


def test_split_with_sep_one_element():
    assert list(split_with_sep("a", ",")) == ["a"]


def test_split_with_sep_one_sep():
    assert list(split_with_sep(",", ",")) == [","]


def test_split_with_sep():
    assert list(split_with_sep("a,b", ",")) == ["a", ",", "b"]


def test_function_tokenizer():
    value = "foo('BAR FOZ')"
    assert list(to_tokens(value)) == ["foo", "(", "'", "BAR FOZ", "'", ")"]


def test_semi_colon():
    value = "select * from t;"
    assert list(to_tokens(value)) == ["select", "*", "from", "t", ";"]


def test_arithmetic():
    value = "2+3*5/7-5"
    assert list(to_tokens(value)) == ["2", "+", "3", "*", "5", "/", "7", "-", "5"]


def test_parenthesis_arithmetic():
    value = "(2+3)"
    assert list(to_tokens(value)) == ["(", "2", "+", "3", ")"]


def test_newlines_and_spaces():
    value = "  \n  (\n \n 2 \n   + \n3)   \n"
    assert list(to_tokens(value)) == ["(", "2", "+", "3", ")"]


def test_equal_predicate():
    value = "x=2"
    assert list(to_tokens(value)) == ["x", "=", "2"]


def test_keep_predicates():
    value = "x >= 2"
    assert list(to_tokens(value)) == ["x", ">=", "2"]


def test_keep_predicates_no_ending():
    value = "x >="
    assert list(to_tokens(value)) == ["x", ">="]


def test_keep_different_predicate():
    value = "x<>2"
    assert list(to_tokens(value)) == ["x", "<>", "2"]


def test_lt():
    value = "x<3"
    assert list(to_tokens(value)) == ["x", "<", "3"]


def test_index():
    value = "x[3]"
    assert list(to_tokens(value)) == ["x", "[", "3", "]"]


def test_chained_columns():
    value = "x.y.z"
    assert list(to_tokens(value)) == ["x", ".", "y", ".", "z"]


def test_keep_tokens_in():
    tokens = iter(["foo", "bar", "baz"])
    assert get_tokens_until_not_in(tokens, ["foo", "bar"]) == (["foo", "bar"], "baz")


def test_keep_tokens_in_parenthesis():
    tokens = iter(["foo", "(", "no", ")", "bar", "baz"])
    assert get_tokens_until_not_in(tokens, ["foo", "bar"]) == (
        ["foo"],
        "(",
    )


def test_get_tokens_until():
    tokens = iter(["foo", "bar", "baz"])
    assert get_tokens_until_one_of(tokens, ["bar"]) == (["foo"], "bar")


def test_get_tokens_until_empty():
    tokens = iter(["foo", "bar", "baz"])
    assert get_tokens_until_one_of(tokens, []) == (["foo", "bar", "baz"], None)


def test_get_tokens_until_with_first():
    tokens = iter(["foo", "bar", "baz"])
    assert get_tokens_until_one_of(tokens, ["bar"], first_token="fib") == (
        ["fib", "foo"],
        "bar",
    )


def test_get_tokens_until_with_keep():
    tokens = iter(["foo", "with", "offset", "offset"])
    assert get_tokens_until_one_of(tokens, ["offset"], keep=[("with", "offset")]) == (
        ["foo", "with", "offset"],
        "offset",
    )


def test_get_tokens_until_with_keep_capitalised():
    tokens = iter(["foo", "WITH", "offset", "offset"])
    assert get_tokens_until_one_of(tokens, ["offset"], keep=[("with", "offset")]) == (
        ["foo", "WITH", "offset"],
        "offset",
    )
