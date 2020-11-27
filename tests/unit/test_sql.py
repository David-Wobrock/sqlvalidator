from sqlvalidator.grammar.sql import (
    BooleanCondition,
    Column,
    Condition,
    Integer,
    transform,
)


def test_boolean_condition():
    sql = BooleanCondition(
        "and",
        Condition(Column("col"), "=", Integer(1)),
        Condition(Column("col2"), "=", Integer(4)),
    )
    expected = """
col = 1 AND col2 = 4
"""
    assert transform(sql) == expected.strip()
