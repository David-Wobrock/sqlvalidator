from sqlvalidator.grammar.lexer import (
    ExpressionParser,
    FromStatementParser,
    SQLStatementParser,
    WhereClauseParser,
)
from sqlvalidator.grammar.sql import (
    Addition,
    Alias,
    AnalyticsClause,
    ArithmaticOperator,
    Array,
    BooleanCondition,
    CastFunctionCall,
    ChainedColumns,
    Column,
    Condition,
    CountFunctionCall,
    DateTimePart,
    ExceptClause,
    FunctionCall,
    GroupByClause,
    Index,
    Integer,
    Interval,
    Join,
    LimitClause,
    Null,
    OnClause,
    OrderByClause,
    OrderByItem,
    Parenthesis,
    SelectStatement,
    String,
    Table,
    Type,
    Unnest,
    UsingClause,
    WhereClause,
    WindowFrameClause,
)
from sqlvalidator.grammar.tokeniser import to_tokens


def test_simple_function_parsing():
    actual, _ = ExpressionParser.parse(to_tokens("test(col)"))
    expected = FunctionCall("test", Column("col"))
    assert actual == expected


def test_simple_function_parsing_no_args():
    actual, _ = ExpressionParser.parse(to_tokens("test()"))
    expected = FunctionCall("test")
    assert actual == expected


def test_simple_function_multiple_params():
    actual, _ = ExpressionParser.parse(to_tokens("test(col, 'Test')"))
    expected = FunctionCall("test", Column("col"), String("Test", quotes="'"))
    assert actual == expected


def test_nested_functions():
    actual, _ = ExpressionParser.parse(to_tokens("test(foo(col))"))
    expected = FunctionCall("test", FunctionCall("foo", Column("col")))
    assert actual == expected


def test_nested_date_functions():
    actual, _ = ExpressionParser.parse(
        to_tokens("DATE(TIMESTAMP_TRUNC(CAST(date AS TIMESTAMP), MONTH))")
    )
    expected = FunctionCall(
        "DATE",
        FunctionCall(
            "TIMESTAMP_TRUNC",
            CastFunctionCall(
                Column("date"),
                Type("TIMESTAMP"),
            ),
            Type("MONTH"),
        ),
    )
    assert actual == expected


def test_string_value():
    actual, _ = ExpressionParser.parse(to_tokens("'VAL'"))
    expected = String("VAL", quotes="'")
    assert actual == expected


def test_string_value_double_quotes():
    actual, _ = ExpressionParser.parse(to_tokens('"val"'))
    expected = String("val", quotes='"')
    assert actual == expected


def test_string_value_back_quotes():
    actual, _ = ExpressionParser.parse(to_tokens("`val`"))
    expected = String("val", quotes="`")
    assert actual == expected


def test_aliased_column():
    actual, _ = ExpressionParser.parse(to_tokens("col AS column_name"))
    expected = Alias(Column("col"), alias=Column("column_name"), with_as=True)
    assert actual == expected


def test_aliased_string_without_as():
    actual, _ = ExpressionParser.parse(to_tokens("'col' column_name"))
    expected = Alias(String("col", quotes="'"), alias="column_name", with_as=False)
    assert actual == expected


def test_integer():
    actual, _ = ExpressionParser.parse(to_tokens("2"))
    expected = Integer(2)
    assert actual == expected


def test_negative_integer():
    actual, _ = ExpressionParser.parse(to_tokens("-2"))
    expected = Integer(-2)
    assert actual == expected


def test_addition():
    actual, _ = ExpressionParser.parse(to_tokens("2+4"))
    expected = Addition(Integer(2), Integer(4))
    assert actual == expected


def test_chained_addition():
    actual, _ = ExpressionParser.parse(to_tokens("2+4+5"))
    expected = Addition(Integer(2), Addition(Integer(4), Integer(5)))
    assert actual == expected


def test_conditional_expression():
    actual, _ = ExpressionParser.parse(to_tokens("field = 4"))
    expected = Condition(Column("field"), "=", Integer(4))
    assert actual == expected


def test_parenthesis():
    actual, _ = ExpressionParser.parse(to_tokens("(field)"))
    expected = Parenthesis(Column("field"))
    assert actual == expected


def test_multiple_parentheses():
    actual, _ = ExpressionParser.parse(to_tokens("((2))"))
    expected = Parenthesis(Parenthesis(Integer(2)))
    assert actual == expected


def test_parenthesis_conditional():
    actual, _ = ExpressionParser.parse(to_tokens("(field+3) = 4"))
    expected = Condition(
        Parenthesis(Addition(Column("field"), Integer(3))), "=", Integer(4)
    )
    assert actual == expected


def test_parenthesis_multiple_elements():
    actual, _ = ExpressionParser.parse(to_tokens("(field,other_field,3,'test')"))
    expected = Parenthesis(
        Column("field"), Column("other_field"), Integer(3), String("test", quotes="'")
    )
    assert actual == expected


def test_from_subquery():
    actual = FromStatementParser.parse(to_tokens("(select field from table_stmt)"))
    expected = Parenthesis(
        SelectStatement(
            expressions=[Column("field")],
            from_statement=Table(Column("table_stmt")),
            semi_colon=False,
        )
    )
    assert actual == expected


def test_where_clause():
    actual, _ = WhereClauseParser.parse(to_tokens("col = 3"))
    expected = WhereClause(Condition(Column("col"), "=", Integer(3)))
    assert actual == expected


def test_boolean_where_clause():
    actual, _ = WhereClauseParser.parse(to_tokens("col = 3 and field = 5"))
    expected = WhereClause(
        BooleanCondition(
            "and",
            Condition(Column("col"), "=", Integer(3)),
            Condition(Column("field"), "=", Integer(5)),
        )
    )
    assert actual == expected


def test_between_where_clause():
    actual, _ = WhereClauseParser.parse(to_tokens("col between 3 and 5"))
    expected = WhereClause(
        Condition(
            Column("col"),
            "between",
            BooleanCondition(
                "and",
                Integer(3),
                Integer(5),
            ),
        )
    )
    assert actual == expected


def test_where_different_predicate():
    actual, _ = WhereClauseParser.parse(to_tokens("col <> 3"))
    expected = WhereClause(
        Condition(Column("col"), "<>", Integer(3)),
    )
    assert actual == expected


def test_parenthesis_boolean_where_clause():
    actual, _ = WhereClauseParser.parse(
        to_tokens("(col = 3 and field = 5) or (f2 or f3)")
    )
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
    actual, _ = WhereClauseParser.parse(to_tokens("(col + 1) = col2"))
    expected = WhereClause(
        Condition(Parenthesis(Addition(Column("col"), Integer(1))), "=", Column("col2"))
    )
    assert actual == expected


def test_multiple_args_boolean_condition():
    actual, _ = WhereClauseParser.parse(to_tokens("(col = 1 and col2=4 and col3=4)"))
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
    actual, _ = WhereClauseParser.parse(
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


def test_where_clause_keeps_generator_intact():
    tokens = to_tokens("col = 3 group by col")
    actual, next_token = WhereClauseParser.parse(tokens)
    expected = WhereClause(Condition(Column("col"), "=", Integer(3)))
    assert actual == expected
    assert next_token == "group"
    assert list(tokens) == ["by", "col"]


def test_where_clause_keeps_generator_intact_is_null_condition():
    tokens = to_tokens("col is null group by col")
    actual, next_token = WhereClauseParser.parse(tokens)
    expected = WhereClause(Condition(Column("col"), "is", Null()))
    assert actual == expected
    assert next_token == "group"
    assert list(tokens) == ["by", "col"]


def test_consecutive_parenthesis():
    actual, _ = ExpressionParser.parse(to_tokens("((col+1) = 3 AND col2=4)"))
    expected = Parenthesis(
        BooleanCondition(
            "AND",
            Condition(
                Parenthesis(Addition(Column("col"), Integer(1))), "=", Integer(3)
            ),
            Condition(
                Column("col2"),
                "=",
                Integer(4),
            ),
        )
    )
    assert actual == expected


def test_select_all():
    actual = SQLStatementParser.parse(to_tokens("SELECT ALL 1"))
    expected = SelectStatement(
        select_all=True, expressions=[Integer(1)], semi_colon=False
    )
    assert actual == expected


def test_select_distinct():
    actual = SQLStatementParser.parse(to_tokens("SELECT DISTINCT 1"))
    expected = SelectStatement(
        select_distinct=True, expressions=[Integer(1)], semi_colon=False
    )
    assert actual == expected


def test_select_distinct_on():
    actual = SQLStatementParser.parse(to_tokens("SELECT DISTINCT ON (col) col"))
    expected = SelectStatement(
        select_distinct=True,
        select_distinct_on=[Column("col")],
        expressions=[Column("col")],
        semi_colon=False,
    )
    assert actual == expected


def test_group_by_without_from():
    actual = SQLStatementParser.parse(to_tokens("SELECT 1 GROUP BY 2"))
    expected = SelectStatement(
        expressions=[Integer(1)],
        group_by_clause=GroupByClause(Integer(2)),
        semi_colon=False,
    )
    assert actual == expected


def test_order_by_clause():
    actual = SQLStatementParser.parse(to_tokens("SELECT col FROM t ORDER BY col, 2"))
    expected = SelectStatement(
        expressions=[Column("col")],
        from_statement=Table(Column("t")),
        order_by_clause=OrderByClause(
            OrderByItem(Column("col")), OrderByItem(Integer(2))
        ),
        semi_colon=False,
    )
    assert actual == expected


def test_limit_parentheses():
    actual = SQLStatementParser.parse(to_tokens("SELECT 1 LIMIT (((3)))"))
    expected = SelectStatement(
        expressions=[Integer(1)],
        limit_clause=LimitClause(
            limit_all=False,
            expression=Parenthesis(Parenthesis(Parenthesis(Integer(3)))),
        ),
        semi_colon=False,
    )
    assert actual == expected


def test_subquery():
    actual = SQLStatementParser.parse(
        to_tokens(
            "SELECT col"
            " from (select count(*) col"
            " from table group by x) WHERE col > 10 ORDER BY col DESC;"
        )
    )
    expected = SelectStatement(
        expressions=[Column("col")],
        from_statement=Parenthesis(
            SelectStatement(
                expressions=[
                    Alias(CountFunctionCall(Column("*")), "col", with_as=False)
                ],
                from_statement=Table(Column("table")),
                group_by_clause=GroupByClause(Column("x")),
                semi_colon=False,
            )
        ),
        where_clause=WhereClause(Condition(Column("col"), ">", Integer(10))),
        order_by_clause=OrderByClause(OrderByItem(Column("col"), has_desc=True)),
        semi_colon=True,
    )
    assert actual == expected


def test_parse_date_function():
    actual, _ = ExpressionParser.parse(to_tokens("DATE('2020-01-01')"))
    expected = FunctionCall("DATE", String("2020-01-01", quotes="'"))
    assert actual == expected


def test_parse_date_function_condition():
    actual, _ = ExpressionParser.parse(to_tokens("col >= DATE('2020-01-01')"))
    expected = Condition(
        Column("col"), ">=", FunctionCall("DATE", String("2020-01-01", quotes="'"))
    )
    assert actual == expected


def test_index_access():
    actual, _ = ExpressionParser.parse(to_tokens("array[0]"))
    expected = Index(Column("array"), [Integer(0)])
    assert actual == expected


def test_index_access_alias():
    actual, _ = ExpressionParser.parse(to_tokens("array[0] alias"))
    expected = Alias(Index(Column("array"), [Integer(0)]), with_as=False, alias="alias")
    assert actual == expected


def test_index_function_access():
    actual, _ = ExpressionParser.parse(to_tokens("array[index(0)]"))
    expected = Index(Column("array"), [FunctionCall("index", Integer(0))])
    assert actual == expected


def test_multiple_indices_access():
    actual, _ = ExpressionParser.parse(to_tokens("array[index(0), 'foo'] alias"))
    expected = Alias(
        Index(
            Column("array"),
            [FunctionCall("index", Integer(0)), String("foo", quotes="'")],
        ),
        with_as=False,
        alias="alias",
    )
    assert actual == expected


def test_index_access_right_hand():
    actual, _ = ExpressionParser.parse(to_tokens("field = array[0]"))
    expected = Condition(
        Column("field"),
        "=",
        Index(Column("array"), [Integer(0)]),
    )
    assert actual == expected


def test_nested_joins():
    sql = """
SELECT COALESCE(sq_1.col, sq_2.col) f0_

FROM (SELECT ANY_VALUE(col) col,
LAST_VALUE(ANY_VALUE(col2)) OVER (PARTITION BY ANY_VALUE(col) ORDER BY SUM(clicks) ASC, SUM(metric) ASC RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) last,
hash
FROM (SELECT *
FROM `events`
WHERE _TABLE_SUFFIX BETWEEN '20200410' AND '20200510')
JOIN
(SELECT * EXCEPT (hash)
FROM (SELECT *,
ROW_NUMBER() OVER (PARTITION BY hash) AS rn
FROM `test-table`
WHERE _TABLE_SUFFIX BETWEEN '20200401' AND '20200501')
WHERE rn = 1)
USING (hash)
GROUP BY hash) sq_1

FULL OUTER JOIN

(SELECT ANY_VALUE(col) col,
hash
FROM (SELECT *
FROM `events`
WHERE _TABLE_SUFFIX BETWEEN '20200310' AND '20200410')
JOIN
(SELECT * EXCEPT (hash),
FROM (SELECT *,
ROW_NUMBER() OVER (PARTITION BY hash) AS rn
FROM `test-table`
WHERE _TABLE_SUFFIX BETWEEN '20200301' AND '20200401')
WHERE rn = 1)
USING (hash)
GROUP BY hash) sq_2

ON sq_1.hash = sq_2.hash
WHERE sq_1.last = 1
GROUP BY f0_
"""  # noqa
    actual = SQLStatementParser.parse(to_tokens(sql))
    expected = SelectStatement(
        expressions=[
            Alias(
                FunctionCall(
                    "COALESCE",
                    ChainedColumns(Column("sq_1"), Column("col")),
                    ChainedColumns(Column("sq_2"), Column("col")),
                ),
                "f0_",
                with_as=False,
            )
        ],
        from_statement=Join(
            "FULL OUTER JOIN",
            left_from=Alias(
                Parenthesis(
                    SelectStatement(
                        expressions=[
                            Alias(
                                FunctionCall("ANY_VALUE", Column("col")),
                                "col",
                                with_as=False,
                            ),
                            Alias(
                                AnalyticsClause(
                                    FunctionCall(
                                        "LAST_VALUE",
                                        FunctionCall("ANY_VALUE", Column("col2")),
                                    ),
                                    partition_by=[
                                        FunctionCall("ANY_VALUE", Column("col"))
                                    ],
                                    order_by=OrderByClause(
                                        OrderByItem(
                                            FunctionCall("SUM", Column("clicks")),
                                            has_asc=True,
                                        ),
                                        OrderByItem(
                                            FunctionCall("SUM", Column("metric")),
                                            has_asc=True,
                                        ),
                                    ),
                                    frame_clause=WindowFrameClause(
                                        "RANGE",
                                        "BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING",  # noqa
                                    ),
                                ),
                                "last",
                                with_as=False,
                            ),
                            Column("hash"),
                        ],
                        from_statement=Join(
                            join_type="JOIN",
                            left_from=Parenthesis(
                                SelectStatement(
                                    expressions=[Column("*")],
                                    from_statement=Table(String("events", quotes="`")),
                                    where_clause=WhereClause(
                                        Condition(
                                            Column("_TABLE_SUFFIX"),
                                            "BETWEEN",
                                            BooleanCondition(
                                                "and",
                                                String("20200410", quotes="'"),
                                                String("20200510", quotes="'"),
                                            ),
                                        )
                                    ),
                                    semi_colon=False,
                                )
                            ),
                            right_from=Parenthesis(
                                SelectStatement(
                                    expressions=[
                                        ExceptClause(Column("*"), [Column("hash")])
                                    ],
                                    from_statement=Parenthesis(
                                        SelectStatement(
                                            expressions=[
                                                Column("*"),
                                                Alias(
                                                    AnalyticsClause(
                                                        FunctionCall("ROW_NUMBER"),
                                                        partition_by=[Column("hash")],
                                                        order_by=None,
                                                        frame_clause=None,
                                                    ),
                                                    Column("rn"),
                                                    with_as=True,
                                                ),
                                            ],
                                            from_statement=Table(
                                                String("test-table", quotes="`")
                                            ),
                                            where_clause=WhereClause(
                                                Condition(
                                                    Column("_TABLE_SUFFIX"),
                                                    "BETWEEN",
                                                    BooleanCondition(
                                                        "and",
                                                        String("20200401", quotes="'"),
                                                        String("20200501", quotes="'"),
                                                    ),
                                                )
                                            ),
                                            semi_colon=False,
                                        )
                                    ),
                                    where_clause=WhereClause(
                                        Condition(Column("rn"), "=", Integer(1))
                                    ),
                                    semi_colon=False,
                                )
                            ),
                            on=None,
                            using=UsingClause(Parenthesis(Column("hash"))),
                        ),
                        group_by_clause=GroupByClause(Column("hash")),
                        semi_colon=False,
                    )
                ),
                "sq_1",
                with_as=False,
            ),
            right_from=Alias(
                Parenthesis(
                    SelectStatement(
                        expressions=[
                            Alias(
                                FunctionCall("ANY_VALUE", Column("col")),
                                "col",
                                with_as=False,
                            ),
                            Column("hash"),
                        ],
                        from_statement=Join(
                            join_type="JOIN",
                            left_from=Parenthesis(
                                SelectStatement(
                                    expressions=[Column("*")],
                                    from_statement=Table(String("events", quotes="`")),
                                    where_clause=WhereClause(
                                        Condition(
                                            Column("_TABLE_SUFFIX"),
                                            "BETWEEN",
                                            BooleanCondition(
                                                "and",
                                                String("20200310", quotes="'"),
                                                String("20200410", quotes="'"),
                                            ),
                                        )
                                    ),
                                    semi_colon=False,
                                )
                            ),
                            right_from=Parenthesis(
                                SelectStatement(
                                    expressions=[
                                        ExceptClause(Column("*"), [Column("hash")])
                                    ],
                                    from_statement=Parenthesis(
                                        SelectStatement(
                                            expressions=[
                                                Column("*"),
                                                Alias(
                                                    AnalyticsClause(
                                                        FunctionCall("ROW_NUMBER"),
                                                        partition_by=[Column("hash")],
                                                        order_by=None,
                                                        frame_clause=None,
                                                    ),
                                                    Column("rn"),
                                                    with_as=True,
                                                ),
                                            ],
                                            from_statement=Table(
                                                String("test-table", quotes="`")
                                            ),
                                            where_clause=WhereClause(
                                                Condition(
                                                    Column("_TABLE_SUFFIX"),
                                                    "BETWEEN",
                                                    BooleanCondition(
                                                        "and",
                                                        String("20200301", quotes="'"),
                                                        String("20200401", quotes="'"),
                                                    ),
                                                )
                                            ),
                                            semi_colon=False,
                                        ),
                                    ),
                                    where_clause=WhereClause(
                                        Condition(Column("rn"), "=", Integer(1))
                                    ),
                                    semi_colon=False,
                                )
                            ),
                            on=None,
                            using=UsingClause(Parenthesis(Column("hash"))),
                        ),
                        group_by_clause=GroupByClause(Column("hash")),
                        semi_colon=False,
                    )
                ),
                "sq_2",
                with_as=False,
            ),
            on=OnClause(
                Condition(
                    ChainedColumns(Column("sq_1"), Column("hash")),
                    "=",
                    ChainedColumns(Column("sq_2"), Column("hash")),
                )
            ),
            using=None,
        ),
        where_clause=WhereClause(
            Condition(ChainedColumns(Column("sq_1"), Column("last")), "=", Integer(1))
        ),
        group_by_clause=GroupByClause(Column("f0_")),
        semi_colon=False,
    )
    assert actual == expected


def test_boolean_condition_as_expression():
    sql = "field is not null and col > 0"
    actual, _ = ExpressionParser.parse(to_tokens(sql))
    expected = BooleanCondition(
        "and",
        Condition(
            Column("field"),
            "is not",
            Null(),
        ),
        Condition(
            Column("col"),
            ">",
            Integer(0),
        ),
    )
    assert actual == expected


def test_select_boolean_condition_expression():
    sql = "select field is not null and col > 0 from t;"
    actual = SQLStatementParser.parse(to_tokens(sql))
    expected = SelectStatement(
        expressions=[
            BooleanCondition(
                "and",
                Condition(
                    Column("field"),
                    "is not",
                    Null(),
                ),
                Condition(
                    Column("col"),
                    ">",
                    Integer(0),
                ),
            )
        ],
        from_statement=Table(Column("t")),
    )
    assert actual == expected


def test_unnest():
    sql = "unnest(table)"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        FunctionCall("unnest", Column("table")),
        with_offset=False,
        with_offset_as=False,
        offset_alias=None,
    )
    assert actual == expected


def test_unnest_with_alias():
    sql = "unnest(table) t"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        Alias(FunctionCall("unnest", Column("table")), with_as=False, alias="t"),
        with_offset=False,
        with_offset_as=False,
        offset_alias=None,
    )
    assert actual == expected


def test_unnest_with_as_alias():
    sql = "unnest(table) as t"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        Alias(FunctionCall("unnest", Column("table")), with_as=True, alias="t"),
        with_offset=False,
        with_offset_as=False,
        offset_alias=None,
    )
    assert actual == expected


def test_unnest_with_offset():
    sql = "unnest(table) with offset"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        FunctionCall("unnest", Column("table")),
        with_offset=True,
        with_offset_as=False,
        offset_alias=None,
    )
    assert actual == expected


def test_unnest_with_offset_alias():
    sql = "unnest(table) with offset o"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        FunctionCall("unnest", Column("table")),
        with_offset=True,
        with_offset_as=False,
        offset_alias="o",
    )
    assert actual == expected


def test_unnest_with_offset_as_alias():
    sql = "unnest(table) with offset as o"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        FunctionCall("unnest", Column("table")),
        with_offset=True,
        with_offset_as=True,
        offset_alias="o",
    )
    assert actual == expected


def test_unnest_alias_with_offset_as_alias():
    sql = "unnest(table) t with offset as o"
    actual = FromStatementParser.parse(to_tokens(sql))
    expected = Unnest(
        Alias(FunctionCall("unnest", Column("table")), with_as=False, alias="t"),
        with_offset=True,
        with_offset_as=True,
        offset_alias="o",
    )
    assert actual == expected


def test_simple_chained_field():
    actual, _ = ExpressionParser.parse(to_tokens("table.field"))
    expected = ChainedColumns(Column("table"), Column("field"))
    assert actual == expected


def test_chained_field():
    actual, _ = ExpressionParser.parse(
        to_tokens("table.field[offset(0)].subfield[offset(0)]")
    )
    expected = ChainedColumns(
        Column("table"),
        ChainedColumns(
            Index(Column("field"), [FunctionCall("offset", Integer(0))]),
            Index(Column("subfield"), [FunctionCall("offset", Integer(0))]),
        ),
    )
    assert actual == expected


def test_aliased_table():
    actual = FromStatementParser.parse(to_tokens("table as sq_1"))
    expected = Table(
        Alias(Column("table"), with_as=True, alias=Column("sq_1")),
    )
    assert actual == expected


def test_empty_list():
    actual, _ = ExpressionParser.parse(to_tokens("[]"))
    expected = Array()
    assert actual == expected


def test_empty_list_with_alias():
    actual, _ = ExpressionParser.parse(to_tokens("[] x"))
    expected = Alias(Array(), with_as=False, alias="x")
    assert actual == expected


def test_boolean_condition():
    actual, _ = ExpressionParser.parse(to_tokens("f1 IS NOT NULL AND f2 > 0 fnew"))
    expected = Alias(
        BooleanCondition(
            "AND",
            Condition(Column("f1"), "is not", Null()),
            Condition(Column("f2"), ">", Integer(0)),
        ),
        with_as=False,
        alias="fnew",
    )
    assert actual == expected


def test_chained_columns_with_arithmetic_operator():
    actual, _ = ExpressionParser.parse(
        to_tokens("IF((a.field + b.field) = 200, 'true', 'false') fa")
    )
    expected = Alias(
        FunctionCall(
            "IF",
            *[
                Condition(
                    Parenthesis(
                        ArithmaticOperator(
                            "+",
                            ChainedColumns(Column("a"), Column("field")),
                            ChainedColumns(Column("b"), Column("field")),
                        )
                    ),
                    "=",
                    Integer(200),
                ),
                String("true", quotes="'"),
                String("false", quotes="'"),
            ]
        ),
        with_as=False,
        alias="fa",
    )
    assert actual == expected


def test_function_with_single_comma_string_param():
    actual, _ = ExpressionParser.parse(to_tokens("test(',')"))
    expected = FunctionCall("test", String(",", quotes="'"))
    assert actual == expected


def test_interval_with_single_datetime_part():
    actual, _ = ExpressionParser.parse(to_tokens("INTERVAL -1 MONTH"))
    expected = Interval(Integer(-1), DateTimePart("MONTH"))
    assert actual == expected


def test_interval_with_datetime_part_range():
    actual, _ = ExpressionParser.parse(to_tokens("INTERVAL '8 -20 17' MONTH TO HOUR"))
    expected = Interval(String("8 -20 17", quotes="'"), DateTimePart("MONTH", "HOUR"))
    assert actual == expected


def test_interval_in_function():
    actual, _ = ExpressionParser.parse(
        to_tokens("TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 SECOND)")
    )
    expected = FunctionCall(
        "TIMESTAMP_ADD",
        FunctionCall("CURRENT_TIMESTAMP"),
        Interval(Integer(30), DateTimePart("SECOND")),
    )
    assert actual == expected
