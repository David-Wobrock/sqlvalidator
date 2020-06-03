from sqlvalidator.grammar.lexer import (
    ExpressionParser,
    FromStatementParser,
    WhereClauseParser,
    SQLStatementParser,
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
    Condition,
    BooleanCondition,
    WhereClause,
    OrderByClause,
    OrderByItem,
)
from sqlvalidator.grammar.tokeniser import to_tokens


def test_simple_function_parsing():
    actual = ExpressionParser.parse(to_tokens("test(col)"))
    expected = FunctionCall("test", Column("col"))
    assert actual == expected


def test_simple_function_parsing_no_args():
    actual = ExpressionParser.parse(to_tokens("test()"))
    expected = FunctionCall("test")
    assert actual == expected


def test_simple_function_multiple_params():
    actual = ExpressionParser.parse(to_tokens("test(col, 'Test')"))
    expected = FunctionCall("test", Column("col"), String("Test", quotes="'"))
    assert actual == expected


def test_nested_functions():
    actual = ExpressionParser.parse(to_tokens("test(foo(col))"))
    expected = FunctionCall("test", FunctionCall("foo", Column("col")))
    assert actual == expected


def test_string_value():
    actual = ExpressionParser.parse(to_tokens("'VAL'"))
    expected = String("VAL", quotes="'")
    assert actual == expected


def test_string_value_double_quotes():
    actual = ExpressionParser.parse(to_tokens('"val"'))
    expected = String("val", quotes='"')
    assert actual == expected


def test_string_value_back_quotes():
    actual = ExpressionParser.parse(to_tokens("`val`"))
    expected = String("val", quotes="`")
    assert actual == expected


def test_aliased_column():
    actual = ExpressionParser.parse(to_tokens("col AS column_name"))
    expected = Alias(Column("col"), alias="column_name", with_as=True)
    assert actual == expected


def test_aliased_string_without_as():
    actual = ExpressionParser.parse(to_tokens("'col' column_name"))
    expected = Alias(String("col", quotes="'"), alias="column_name", with_as=False)
    assert actual == expected


def test_integer():
    actual = ExpressionParser.parse(to_tokens("2"))
    expected = Integer(2)
    assert actual == expected


def test_addition():
    actual = ExpressionParser.parse(to_tokens("2+4"))
    expected = Addition(Integer(2), Integer(4))
    assert actual == expected


def test_chained_addition():
    actual = ExpressionParser.parse(to_tokens("2+4+5"))
    expected = Addition(Integer(2), Addition(Integer(4), Integer(5)))
    assert actual == expected


def test_conditional_expression():
    actual = ExpressionParser.parse(to_tokens("field = 4"))
    expected = Condition(Column("field"), "=", Integer(4))
    assert actual == expected


def test_parenthesis():
    actual = ExpressionParser.parse(to_tokens("(field)"))
    expected = Parenthesis(Column("field"))
    assert actual == expected


def test_parenthesis_conditional():
    actual = ExpressionParser.parse(to_tokens("(field+3) = 4"))
    expected = Condition(
        Parenthesis(Addition(Column("field"), Integer(3))), "=", Integer(4)
    )
    assert actual == expected


def test_parenthesis_multiple_elements():
    actual = ExpressionParser.parse(to_tokens("(field,other_field,3,'test')"))
    expected = Parenthesis(
        Column("field"), Column("other_field"), Integer(3), String("test", quotes="'")
    )
    assert actual == expected


def test_from_subquery():
    actual = FromStatementParser.parse(to_tokens("(select field from table_stmt)"))
    expected = Parenthesis(
        SelectStatement(
            expressions=[Column("field")],
            from_statement=Table("table_stmt"),
            semi_colon=False,
        )
    )
    assert actual == expected


def test_where_clause():
    actual = WhereClauseParser.parse(to_tokens("col = 3"))
    expected = WhereClause(Condition(Column("col"), "=", Integer(3)))
    assert actual == expected


def test_boolean_where_clause():
    actual = WhereClauseParser.parse(to_tokens("col = 3 and field = 5"))
    expected = WhereClause(
        BooleanCondition(
            "and",
            Condition(Column("col"), "=", Integer(3)),
            Condition(Column("field"), "=", Integer(5)),
        )
    )
    assert actual == expected


def test_where_different_predicate():
    actual = WhereClauseParser.parse(to_tokens("col <> 3"))
    expected = WhereClause(Condition(Column("col"), "<>", Integer(3)),)
    assert actual == expected


def test_parenthesis_boolean_where_clause():
    actual = WhereClauseParser.parse(to_tokens("(col = 3 and field = 5) or (f2 or f3)"))
    expected = WhereClause(
        BooleanCondition(
            "or",
            Parenthesis(
                BooleanCondition(
                    "and",
                    Condition(Column("col"), "=", Integer(3)),
                    Condition(Column("field"), "=", Integer(5)),
                )
            ),
            Parenthesis(BooleanCondition("or", Column("f2"), Column("f3"))),
        )
    )
    assert actual == expected


def test_parenthesis_expression_where_clause():
    actual = WhereClauseParser.parse(to_tokens("(col + 1) = col2"))
    expected = WhereClause(
        Condition(Parenthesis(Addition(Column("col"), Integer(1))), "=", Column("col2"))
    )
    assert actual == expected


def test_multiple_args_boolean_condition():
    actual = WhereClauseParser.parse(to_tokens("(col = 1 and col2=4 and col3=4)"))
    expected = WhereClause(
        Parenthesis(
            BooleanCondition(
                "and",
                Condition(Column("col"), "=", Integer(1)),
                BooleanCondition(
                    "and",
                    Condition(Column("col2"), "=", Integer(4)),
                    Condition(Column("col3"), "=", Integer(4)),
                ),
            ),
        )
    )
    assert actual == expected


def test_nested_parenthesis_boolean():
    actual = WhereClauseParser.parse(
        to_tokens("(col = 1 and col2=4) or (col = 2 and (col =6 or col=9))")
    )
    expected = WhereClause(
        BooleanCondition(
            "or",
            Parenthesis(
                BooleanCondition(
                    "and",
                    Condition(Column("col"), "=", Integer(1)),
                    Condition(Column("col2"), "=", Integer(4)),
                )
            ),
            Parenthesis(
                BooleanCondition(
                    "and",
                    Condition(Column("col"), "=", Integer(2)),
                    Parenthesis(
                        BooleanCondition(
                            "or",
                            Condition(Column("col"), "=", Integer(6)),
                            Condition(Column("col"), "=", Integer(9)),
                        )
                    ),
                )
            ),
        )
    )
    assert actual == expected


def test_consecutive_parenthesis():
    actual = ExpressionParser.parse(to_tokens("((col+1) = 3 AND col2=4)"))
    expected = Parenthesis(
        BooleanCondition(
            "and",
            Condition(
                Parenthesis(Addition(Column("col"), Integer(1))), "=", Integer(3)
            ),
            Condition(Column("col2"), "=", Integer(4),),
        )
    )
    assert actual == expected


def test_select_all():
    actual = SQLStatementParser.parse(to_tokens("SELECT ALL 1"))
    expected = SelectStatement(select_all=True, expressions=[Integer(1)])
    assert actual == expected


def test_select_distinct():
    actual = SQLStatementParser.parse(to_tokens("SELECT DISTINCT 1"))
    expected = SelectStatement(select_distinct=True, expressions=[Integer(1)])
    assert actual == expected


def test_select_distinct_on():
    actual = SQLStatementParser.parse(to_tokens("SELECT DISTINCT ON (col) col"))
    expected = SelectStatement(
        select_distinct=True,
        select_distinct_on=[Column("col")],
        expressions=[Column("col")],
    )
    assert actual == expected


def test_group_by_without_from():
    actual = SQLStatementParser.parse(to_tokens("SELECT 1 GROUP BY 2"))
    expected = SelectStatement(expressions=[Integer(1)], group_by_clause=[Integer(2)],)
    assert actual == expected


def test_order_by_clause():
    actual = SQLStatementParser.parse(to_tokens("SELECT col FROM t ORDER BY col, 2"))
    expected = SelectStatement(
        expressions=[Column("col")],
        from_statement=Table("t"),
        order_by_clause=OrderByClause(
            OrderByItem(Column("col")), OrderByItem(Integer(2))
        ),
    )
    assert actual == expected
