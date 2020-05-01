from sqlvalidator.sql_formatter import format_sql


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
