import pytest

from sqlvalidator import format_sql


def test_format_select_star():
    sql = "select * from table;"
    expected = """
SELECT *
FROM table;
"""
    assert expected.strip() == format_sql(sql)


def test_upper_function_name():
    sql = "select sum(column) FROM table;"
    expected = """
SELECT SUM(column)
FROM table;
"""
    assert expected.strip() == format_sql(sql)


def test_nested_function_name():
    sql = "select ifnull(sum(col), 'NOTHING') from table_stmt;"
    expected = """
SELECT IFNULL(SUM(col), 'NOTHING')
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


def test_no_from_statement():
    sql = "select 1;"
    expected = "SELECT 1;"
    assert expected.strip() == format_sql(sql)


def test_simple_column():
    sql = "select col from table_stmt;"
    expected = """
SELECT col
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


def test_simple_aliased_column():
    sql = "select col alias from table_stmt;"
    expected = """
SELECT col alias
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


def test_simple_aliased_as_column():
    sql = "select col as alias from table_stmt;"
    expected = """
SELECT col AS alias
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


def test_multiple_columns():
    sql = "select col, col2 from table_stmt;"
    expected = """
SELECT
 col,
 col2
FROM table_stmt;
"""
    assert expected.strip() == format_sql(sql)


def test_parenthesis():
    sql = "select (email,id), id from auth_user;"
    expected = """
SELECT
 (email, id),
 id
FROM auth_user;
"""
    assert expected.strip() == format_sql(sql)


@pytest.mark.skip()
def test_basic_arithmetic():
    sql = "select (1+1) add, 2*3, 9/3;"
    expected = """
SELECT
 (1 + 1) add,
 2 * 3,
 9 / 3;
"""
    assert expected.strip() == format_sql(sql)


def test_nested_queries():
    sql = "select field from (select field from table_stmt);"
    expected = """
SELECT field
FROM (
 SELECT field
 FROM table_stmt
);
"""
    assert expected.strip() == format_sql(sql)


def test_nested_queries_multiple_columns():
    sql = "select field, f2 from (select field, f2 from table_stmt);"
    expected = """
SELECT
 field,
 f2
FROM (
 SELECT
  field,
  f2
 FROM table_stmt
);
"""
    assert expected.strip() == format_sql(sql)


def test_two_nested_queries():
    sql = "select field from (select field, f2 from (select * from t));"
    expected = """
SELECT field
FROM (
 SELECT
  field,
  f2
 FROM (
  SELECT *
  FROM t
 )
);
"""
    assert expected.strip() == format_sql(sql)


def test_assert_no_semi_colon():
    sql = "select * from t"
    expected = """
SELECT *
FROM t
"""
    assert expected.strip() == format_sql(sql)
