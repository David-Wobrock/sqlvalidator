import pytest

from sqlvalidator.sql_formatter import format_sql


def test_format_select_star():
    sql = "select * from table_stmt;"
    expected = """
SELECT *
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


def test_upper_function_name():
    sql = "select sum(column) from table_stmt;"
    expected = """
SELECT SUM(column)
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


@pytest.mark.skip(
    "'table' should be lower case, but upper case because it is a symbol and not correctly understood"
)
def test_format_from_symbol():
    sql = "select * from table;"
    expected = """
SELECT *
FROM table;
"""
    assert expected.strip() == format_sql(sql)


def test_nested_function_name():
    sql = "select ifnull(sum(col), 'NOTHING') from table_stmt;"
    # TODO: SUM should be capitalised
    expected = """
SELECT IFNULL(sum(col), 'NOTHING')
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)
