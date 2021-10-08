import pytest
from sqlvalidator.testing import assert_valid_sql, assert_invalid_sql


def test_assert_valid_sql():
    sql = "SELECT field2 FROM (SELECT field1 FROM table)"
    with pytest.raises(AssertionError):
        assert_valid_sql(sql)


def test_assert_invalid_sql():
    sql = "SELECT * FROM table"
    with pytest.raises(AssertionError):
        assert_invalid_sql(sql)


def test_select_star_from():
    sql = "SELECT * FROM table"
    assert_valid_sql(sql)


def test_select_field_from():
    sql = "SELECT field FROM table"
    assert_valid_sql(sql)


def test_nested_select():
    sql = "SELECT field FROM (SELECT * FROM table)"
    assert_valid_sql(sql)


def test_no_from():
    sql = "SELECT 1, 'test'"
    assert_valid_sql(sql)


def test_nested_select_without_field():
    sql = "SELECT field2 FROM (SELECT field1 FROM table)"
    assert_invalid_sql(sql)


def test_nested_select_with_star():
    sql = "SELECT * FROM (SELECT field1 FROM table)"
    assert_valid_sql(sql)


def test_no_from_with_field():
    sql = "SELECT field"
    assert_invalid_sql(sql)


def test_where_without_from():
    sql = "SELECT 1 WHERE col = 3"
    assert_invalid_sql(sql)


def test_where_parenthesis_without_from():
    sql = "SELECT 1 WHERE (col = 3)"
    assert_invalid_sql(sql)


def test_where_boolean_condition():
    sql = (
        "SELECT field1 FROM (SELECT field1 FROM table) WHERE field1 = 3 and field2 = 4"
    )
    assert_invalid_sql(sql)


def test_where_constant_columns():
    sql = "SELECT 1 WHERE 'test' = 't' and 4 > 5"
    assert_valid_sql(sql)


def test_nested_select_without_where_field():
    sql = "SELECT field1 FROM (SELECT field1 FROM table) WHERE field2 = 3"
    assert_invalid_sql(sql)


def test_where_clause_returns_boolean():
    sql = "SELECT 1 WHERE 'test' LIKE '%t%'"
    assert_valid_sql(sql)


def test_where_clause_not_boolean_but_string():
    sql = "SELECT 1 WHERE 'test'"
    assert_invalid_sql(sql)


def test_where_clause_not_boolean_but_integer():
    sql = "SELECT 1 WHERE 5"
    assert_invalid_sql(sql)


def test_group_without_by():
    sql = "SELECT 1 GROUP 1"
    assert_invalid_sql(sql)


def test_group_by_existing_position():
    sql = "SELECT 1 GROUP BY 1"
    assert_valid_sql(sql)


def test_group_by_unknown_position():
    sql = "SELECT 1 GROUP BY 2"
    assert_invalid_sql(sql)


def test_group_by_unknown_position_parenthesis():
    sql = "SELECT 1 GROUP BY ((2));"
    assert_invalid_sql(sql)


def test_group_by_negative_position():
    sql = "SELECT 1 GROUP BY -1;"
    assert_invalid_sql(sql)


def test_group_by_unknown_column():
    sql = "SELECT 1 GROUP BY x"
    assert_invalid_sql(sql)


def test_group_by_implicit_column():
    sql = "SELECT COUNT(y) FROM 'table' GROUP BY x"
    assert_valid_sql(sql)


def test_group_by_known_column_star():
    sql = "SELECT COUNT(y) FROM (select * from 'table') GROUP BY x"
    assert_valid_sql(sql)


def test_group_by_known_column():
    sql = "SELECT COUNT(y) FROM (select x, y from 'table') GROUP BY x"
    assert_valid_sql(sql)


def test_group_by_unknown_column_with_from():
    sql = "SELECT COUNT(y) FROM (select y from 'table') GROUP BY x"
    assert_invalid_sql(sql)


def test_having_non_boolean_constant():
    sql = "SELECT 2 HAVING 1;"
    assert_invalid_sql(sql)


def test_having_condition_constants():
    sql = "SELECT 2 HAVING 1 = 1;"
    assert_valid_sql(sql)


def test_having_unknown_column():
    sql = "SELECT 1 HAVING x"
    assert_invalid_sql(sql)


def test_having_unknown_column_parenthesis():
    sql = "SELECT 1 HAVING ((x))"
    assert_invalid_sql(sql)


def test_having_multiple_unknown_column_parenthesis():
    sql = "SELECT 1 HAVING 1=1 and ((x))"
    assert_invalid_sql(sql)


def test_order_without_by():
    sql = "SELECT 1 ORDER 1"
    assert_invalid_sql(sql)


def test_order_by_known_position():
    sql = "SELECT 1 ORDER BY ((1))"
    assert_valid_sql(sql)


def test_order_by_unknown_position():
    sql = "SELECT 1 ORDER BY 2"
    assert_invalid_sql(sql)


def test_order_by_unknown_column():
    sql = "SELECT 1 ORDER BY x"
    assert_invalid_sql(sql)


def test_order_by_unknown_column_parenthesis():
    sql = "SELECT 1 ORDER BY (x)"
    assert_invalid_sql(sql)


def test_order_by_known_column():
    sql = "SELECT COUNT(y) FROM (select x, y from 'table') ORDER BY x"
    assert_valid_sql(sql)


def test_order_by_unknown_column_with_from():
    sql = "SELECT COUNT(y) FROM (select y from 'table') ORDER BY x"
    assert_invalid_sql(sql)


def test_limit_integer():
    sql = "SELECT 1 LIMIT 3"
    assert_valid_sql(sql)


def test_limit_zero():
    sql = "SELECT 1 LIMIT 0;"
    assert_valid_sql(sql)


def test_limit_negative_integer():
    sql = "SELECT 1 LIMIT -3"
    assert_invalid_sql(sql)


def test_limit_integer_parenthesis():
    sql = "SELECT 1 LIMIT (((3)))"
    assert_valid_sql(sql)


def test_limit_column():
    sql = "SELECT 1 LIMIT x"
    assert_invalid_sql(sql)


def test_limit_column_with_from():
    sql = "SELECT 1 from table LIMIT x;"
    assert_invalid_sql(sql)


def test_limit_multiple_integers():
    sql = "SELECT 1 from table LIMIT 1, 2;"
    assert_invalid_sql(sql)


def test_offset():
    sql = "SELECT 1 from table OFFSET 1;"
    assert_valid_sql(sql)


def test_offset_parenthesis():
    sql = "SELECT 1 from table OFFSET ((1));"
    assert_valid_sql(sql)


def test_offset_negative():
    sql = "SELECT 1 from table OFFSET -1;"
    assert_invalid_sql(sql)


def test_offset_variable():
    sql = "SELECT 1 from table OFFSET (x)"
    assert_invalid_sql(sql)


def test_group_by_alias():
    sql = "SELECT x + y f0 FROM (select x, y from table) GROUP BY f0"
    assert_valid_sql(sql)


def test_invalid_join_missing_using_or_on():
    sql = "SELECT field FROM table JOIN other_table"
    assert_invalid_sql(sql)


def test_functioncall_expressions_missing_from_subquery():
    sql = """
    select APPROX_COUNT_DISTINCT(IF(field <> 0, column , NULL)) f_0
    from (
    select x from table)
    """
    assert_invalid_sql(sql)


def test_functioncall_expressions_in_subquery():
    sql = """
    select APPROX_COUNT_DISTINCT(IF(field <> 0, column , NULL)) f_0
    from (
    select field, (a+b) * x column from table)
    """
    assert_valid_sql(sql)


def test_functioncall_expressions_in_subquery_star():
    sql = """
    select APPROX_COUNT_DISTINCT(IF(field <> 0, column , NULL)) f_0
    from (
    select * from table)
    """
    assert_valid_sql(sql)


def test_missing_nested_subquery_columns():
    sql = """
    select x
    from (
    select x from (select field, column from table))
    """
    assert_invalid_sql(sql)


def test_nested_subquery_columns():
    sql = """
    select x
    from (
    select x from (select x from table))
    """
    assert_valid_sql(sql)


def test_nested_subquery_columns_star():
    sql = """
    select x
    from (
    select * from (select x from table))
    """
    assert_valid_sql(sql)


def test_missing_nested_subquery_columns_star():
    sql = """
    select x
    from (
    select * from (select field from table))
    """
    assert_invalid_sql(sql)
