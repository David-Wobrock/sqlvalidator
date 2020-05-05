import pytest

from sqlvalidator.grammar.lexer import (
    to_tokens,
    split_with_sep,
    ExpressionParser,
    FromStatementParser,
)
from sqlvalidator.grammar.sql import (
    FunctionCall,
    Column,
    Alias,
    String,
    Integer,
    Parenthesis,
    Addition,
    SelectStatement,
    Table,
)


def test_split_with_sep_one_element():
    assert list(split_with_sep("a", ",")) == ["a"]


def test_split_with_sep_one_sep():
    assert list(split_with_sep(",", ",")) == [","]


def test_split_with_sep():
    assert list(split_with_sep("a,b", ",")) == ["a", ",", "b"]


def test_tokenizer():
    value = "foo('BAR FOZ')"
    assert list(to_tokens(value)) == ["foo", "(", "'", "BAR FOZ", "'", ")"]


def test_simple_function_parsing():
    assert ExpressionParser.parse(to_tokens("test(col)")) == FunctionCall(
        "test", Column("col")
    )


def test_simple_function_parsing_no_args():
    assert ExpressionParser.parse(to_tokens("test()")) == FunctionCall("test")


def test_simple_function_multiple_params():
    assert ExpressionParser.parse(to_tokens("test(col, 'Test')")) == FunctionCall(
        "test", Column("col"), String("Test", quotes="'")
    )


def test_nested_functions():
    assert ExpressionParser.parse(to_tokens("test(foo(col))")) == FunctionCall(
        "test", FunctionCall("foo", Column("col"))
    )


def test_string_value():
    assert ExpressionParser.parse(to_tokens("'VAL'")) == String("VAL", quotes="'")


def test_string_value_double_quotes():
    assert ExpressionParser.parse(to_tokens('"val"')) == String("val", quotes='"')


def test_string_value_back_quotes():
    assert ExpressionParser.parse(to_tokens("`val`")) == String("val", quotes="`")


def test_aliased_column():
    assert ExpressionParser.parse(to_tokens("col AS column_name")) == Alias(
        Column("col"), alias="column_name", with_as=True
    )


def test_aliased_string_without_as():
    assert ExpressionParser.parse(to_tokens("'col' column_name")) == Alias(
        String("col", quotes="'"), alias="column_name", with_as=False
    )


def test_integer():
    assert ExpressionParser.parse(to_tokens("2")) == Integer(2)


@pytest.mark.skip()
def test_addition():
    assert ExpressionParser.parse(to_tokens("2*4")) == Addition(Integer(2), Integer(4))


def test_parenthesis():
    assert ExpressionParser.parse(to_tokens("(field)")) == Parenthesis(Column("field"))


def test_parenthesis_multiple_elements():
    assert ExpressionParser.parse(
        to_tokens("(field,other_field,3,'test')")
    ) == Parenthesis(
        Column("field"), Column("other_field"), Integer(3), String("test", quotes="'")
    )


def test_from_subquery():
    assert FromStatementParser.parse(
        to_tokens("(select field from table_stmt)")
    ) == Parenthesis(
        SelectStatement(
            expressions=[Column("field")], from_statement=Table("table_stmt")
        )
    )
