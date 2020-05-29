from sqlvalidator import format_sql


def test_format_select_star():
    sql = "select * from table;"
    expected = """
SELECT *
FROM table;
"""
    assert format_sql(sql) == expected.strip()


def test_upper_function_name():
    sql = "select sum(column) FROM table;"
    expected = """
SELECT SUM(column)
FROM table;
"""
    assert format_sql(sql) == expected.strip()


def test_nested_function_name():
    sql = "select ifnull(sum(col), 'NOTHING') from table_stmt;"
    expected = """
SELECT IFNULL(SUM(col), 'NOTHING')
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_no_from_statement():
    sql = "select 1;"
    expected = "SELECT 1;"
    assert format_sql(sql) == expected.strip()


def test_simple_column():
    sql = "select col from table_stmt;"
    expected = """
SELECT col
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_conditional_column():
    sql = "select col = 1 from table_stmt;"
    expected = """
SELECT col = 1
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_conditional_parenthesis_columns():
    sql = "select (col + 1) = 4 as out from table_stmt;"
    expected = """
SELECT (col + 1) = 4 AS out
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_simple_aliased_column():
    sql = "select col alias from table_stmt;"
    expected = """
SELECT col alias
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_simple_aliased_as_column():
    sql = "select col as alias from table_stmt;"
    expected = """
SELECT col AS alias
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_multiple_columns():
    sql = "select col, col2 from table_stmt;"
    expected = """
SELECT
 col,
 col2
FROM table_stmt;
"""
    assert format_sql(sql) == expected.strip()


def test_parenthesis():
    sql = "select (email,id), id from auth_user;"
    expected = """
SELECT
 (email, id),
 id
FROM auth_user;
"""
    assert format_sql(sql) == expected.strip()


def test_basic_arithmetic():
    sql = "select (1+1) add, 2*3, 9/3;"
    expected = """
SELECT
 (1 + 1) add,
 2 * 3,
 9 / 3;
"""
    assert format_sql(sql) == expected.strip()


def test_chained_arithmetic():
    sql = "select 1+1+1, 2*3-5"
    expected = """
SELECT
 1 + 1 + 1,
 2 * 3 - 5
"""
    assert format_sql(sql) == expected.strip()


def test_nested_queries():
    sql = "select field from (select field from table_stmt);"
    expected = """
SELECT field
FROM (
 SELECT field
 FROM table_stmt
);
"""
    assert format_sql(sql) == expected.strip()


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
    assert format_sql(sql) == expected.strip()


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
    assert format_sql(sql) == expected.strip()


def test_assert_no_semi_colon():
    sql = "select * from t"
    expected = """
SELECT *
FROM t
"""
    assert format_sql(sql) == expected.strip()


def test_quoted_from():
    sql = "select * from `table`;"
    expected = """
SELECT *
FROM `table`;
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_boolean_column():
    sql = "select * from t where col"
    expected = """
SELECT *
FROM t
WHERE col
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_boolean_equal():
    sql = "select * from t where col = true"
    expected = """
SELECT *
FROM t
WHERE col = TRUE
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_boolean_is():
    sql = "select * from t where col is true"
    expected = """
SELECT *
FROM t
WHERE col IS TRUE
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_str():
    sql = "select * from t where col = 'test'"
    expected = """
SELECT *
FROM t
WHERE col = 'test'
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_columns():
    sql = "select * from t where col = col2"
    expected = """
SELECT *
FROM t
WHERE col = col2
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_parenthesis_expression():
    sql = "select * from t where (col + 1) = col2"
    expected = """
SELECT *
FROM t
WHERE (col + 1) = col2
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_boolean():
    sql = "select * from t where col = 1 and col2=4"
    expected = """
SELECT *
FROM t
WHERE col = 1 AND col2 = 4
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_parenthesis_boolean():
    sql = "select * from t where (col = 1 and (col2=4))"
    expected = """
SELECT *
FROM t
WHERE (col = 1 AND (col2 = 4))
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_multiple_parenthesis_booleans():
    sql = (
        "select * from t where (col = 1 and col2=4) or (col = 2 and (col =6 or col=9))"
    )
    expected = """
SELECT *
FROM t
WHERE (col = 1 AND col2 = 4) OR (col = 2 AND (col = 6 OR col = 9))
"""
    assert format_sql(sql) == expected.strip()


def test_where_clause_multiple_booleans():
    sql = "select * from t where col = 1 and col2=4 And col = 2 and col =6 or (col=9)"
    expected = """
SELECT *
FROM t
WHERE col = 1 AND col2 = 4 AND col = 2 AND col = 6 OR (col = 9)
"""
    assert format_sql(sql) == expected.strip()


def test_boolean_conditions_select_where():
    sql = "select (col+1) = 3 AND col2=4 from t where (col+1) = 3 AND col2=4"
    expected = """
SELECT (col + 1) = 3 AND col2 = 4
FROM t
WHERE (col + 1) = 3 AND col2 = 4
"""
    assert format_sql(sql) == expected.strip()


def test_parenthesis_boolean_conditions_select_where():
    sql = "select ((col+1) = 3 AND col2=4) from t where ((col+1) = 3 AND col2=4)"
    expected = """
SELECT ((col + 1) = 3 AND col2 = 4)
FROM t
WHERE ((col + 1) = 3 AND col2 = 4)
"""
    assert format_sql(sql) == expected.strip()


def test_distinct_on_one_field():
    sql = "SELECT DISTINCT ON (location) location, time, report FROM weather_reports;"
    expected = """
SELECT DISTINCT ON (location)
 location,
 time,
 report
FROM weather_reports;
"""
    assert format_sql(sql) == expected.strip()


def test_distinct_on_multiple_fields():
    sql = (
        "SELECT DISTINCT ON (location, time) location, time, report "
        "FROM weather_reports;"
    )
    expected = """
SELECT DISTINCT ON (location, time)
 location,
 time,
 report
FROM weather_reports;
"""
    assert format_sql(sql) == expected.strip()


def test_empty_group_by():
    sql = "SELECT * from t group by ()"
    expected = """
SELECT *
FROM t
GROUP BY ()
"""
    assert format_sql(sql) == expected.strip()


def test_group_by():
    sql = "SELECT * from t GROUP BY col"
    expected = """
SELECT *
FROM t
GROUP BY col
"""
    assert format_sql(sql) == expected.strip()


def test_group_by_parenthesis():
    sql = "SELECT * from t GROUP BY (col)"
    expected = """
SELECT *
FROM t
GROUP BY (col)
"""
    assert format_sql(sql) == expected.strip()


def test_group_by_multiple_elements():
    sql = "SELECT * from t GROUP BY col1, col2, col3"
    expected = """
SELECT *
FROM t
GROUP BY
 col1,
 col2,
 col3
"""
    assert format_sql(sql) == expected.strip()


def test_group_by_multiple_elements_parenthesis():
    sql = "SELECT * from t GROUP BY (col1, col2, col3)"
    expected = """
SELECT *
FROM t
GROUP BY (col1, col2, col3)
"""
    assert format_sql(sql) == expected.strip()


def test_where_and_group_by():
    sql = "SELECT count(*) from t where x =3 GROUP BY col1;"
    expected = """
SELECT COUNT(*)
FROM t
WHERE x = 3
GROUP BY col1;
"""
    assert format_sql(sql) == expected.strip()


def test_group_by_parenthesis_rollup():
    sql = "SELECT * from t GROUP BY ROLLUP (col)"
    expected = """
SELECT *
FROM t
GROUP BY ROLLUP (col)
"""
    assert format_sql(sql) == expected.strip()


def test_group_by_multiple_elements_parenthesis_rollup():
    sql = "SELECT * from t GROUP BY ROLLUP (col1, col2, col3);"
    expected = """
SELECT *
FROM t
GROUP BY ROLLUP (col1, col2, col3);
"""
    assert format_sql(sql) == expected.strip()


def test_where_and_having():
    sql = "SELECT count(*) from t where x =3 having (sum(x) > 50);"
    expected = """
SELECT COUNT(*)
FROM t
WHERE x = 3
HAVING (SUM(x) > 50);
"""
    assert format_sql(sql) == expected.strip()


def test_order_by():
    sql = "SELECT * from t order by col"
    expected = """
SELECT *
FROM t
ORDER BY col
"""
    assert format_sql(sql) == expected.strip()


def test_order_by_mutliple_fields():
    sql = "SELECT * from t order by col, 2"
    expected = """
SELECT *
FROM t
ORDER BY
 col,
 2
"""
    assert format_sql(sql) == expected.strip()


def test_order_by_mutliple_fields_order():
    sql = "SELECT * from t order by col DESC, 2 ASC"
    expected = """
SELECT *
FROM t
ORDER BY
 col DESC,
 2 ASC
"""
    assert format_sql(sql) == expected.strip()


def test_limit():
    sql = "SELECT * from t limit 5"
    expected = """
SELECT *
FROM t
LIMIT 5
"""
    assert format_sql(sql) == expected.strip()


def test_limit_all():
    sql = "SELECT * from t limit all"
    expected = """
SELECT *
FROM t
LIMIT ALL
"""
    assert format_sql(sql) == expected.strip()


def test_offset():
    sql = "SELECT * from t offset 5"
    expected = """
SELECT *
FROM t
OFFSET 5
"""
    assert format_sql(sql) == expected.strip()
