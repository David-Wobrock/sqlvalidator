from sqlvalidator.grammar.sql import (
    BooleanCondition,
    CastFunctionCall,
    Column,
    Condition,
    Integer,
    Type,
    transform,
)


def test_boolean_condition():
    sql = BooleanCondition(
        "and",
        Condition(Column("col"), "=", Integer(1)),
        Condition(Column("col2"), "=", Integer(4)),
    )
    expected = "col = 1 AND col2 = 4"
    assert transform(sql) == expected.strip()


def test_cast_function_call():
    sql = CastFunctionCall(
        Column("date"),
        Type("date"),
    )
    expected = "CAST(date AS DATE)"
    assert transform(sql) == expected.strip()
