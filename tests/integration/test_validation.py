from typing import List, Optional

import sqlvalidator


def assert_valid_sql(sql: str):
    sql_query = sqlvalidator.parse(sql)
    assert sql_query.is_valid() is True, sql_query.errors


def assert_invalid_sql(sql: str, expected_errors: Optional[List[str]] = None):
    sql_query = sqlvalidator.parse(sql)
    assert sql_query.is_valid() is False, (
        "No errors found, but expected: {}".format(expected_errors)
        if expected_errors
        else "No errors found, but expected some"
    )
    if expected_errors:
        assert sql_query.errors == expected_errors


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


def test_missing_chained_columns():
    sql = """
    select a.x, b.y
    from (
    select o from table) a
    JOIN (other_table) b
    USING (o)
    """
    assert_invalid_sql(sql, ["The column x was not found in alias a"])


def test_missing_table_alias_chained_columns():
    sql = """
    select a.x, b.y
    from (
    select x from table) a
    JOIN (select x, y from other_table) c
    USING (x)
    """
    assert_invalid_sql(sql, ["The column y was not found in alias b"])


def test_chained_columns_from_join():
    sql = """
    select a.x, b.y
    from (
    select x from table) a
    JOIN (other_table) b
    USING (x)
    """
    assert_valid_sql(sql)


def test_partition_by_with_order_by():
    sql = """
SELECT
 DENSE_RANK() OVER (
  PARTITION BY f
  ORDER BY col ASC
 ) AS dr
FROM t
"""
    assert_valid_sql(sql)


def test_chained_column_is_nested_field():
    sql = """
SELECT
 StructField.Id,
 StructField.Name
FROM Table
"""
    assert_valid_sql(sql)


def test_chained_column_is_table_alias():
    sql = """
SELECT
 StructField.Id,
 StructField.Name
FROM Table StructField
    """

    assert_valid_sql(sql)


def test_chained_column_is_not_table_alias():
    sql = """
SELECT
 StructField.Id,
 StructField.Name
FROM Table A
    """

    assert_valid_sql(sql)


def test_know_fields_from_alias():
    sql = """
SELECT
 ANY_VALUE(sq_1__x) f_0,
 sq_1__field1 f_1
FROM (
 SELECT
  sq_1.field1 sq_1__field1,
  sq_1.x sq_1__x,
  sq_1.x_hash sq_1__x_hash
 FROM (
  SELECT *
  FROM `{table}`
  WHERE code <> 0
 ) sq_1
)
GROUP BY sq_1__x_hash
"""
    assert_valid_sql(sql)


def test_specified_field_from_alias_subquery():
    sql = """
SELECT
 sq_1__field f_1
FROM (
 SELECT
  sq_1.field sq_1__field
 FROM (
  SELECT x field
  FROM `test_1.top_orphan_segments_2_3`
 ) sq_1
)
"""
    assert_valid_sql(sql)


def test_subquery_field_is_boolean_and_can_where():
    sql = """
      SELECT *
      FROM first_table a
      LEFT JOIN (
       SELECT
        field = 0 field_alias,
       FROM other_table
      ) b
      ON a.id = b.id
      WHERE b.field_alias
     )
"""
    assert_valid_sql(sql)


def test_subquery_field_is_not_boolean_and_cannot_where():
    sql = """
      SELECT *
      FROM first_table a
      LEFT JOIN (
       SELECT
        3 field_alias,
       FROM other_table
      ) b
      ON a.id = b.id
      WHERE b.field_alias
     )
"""

    assert_invalid_sql(
        sql, ["The argument of WHERE must be type boolean, not type int"]
    )


def test_unknown_type_subquery_field_and_allow_where():
    sql = """
      SELECT *
      FROM first_table a
      LEFT JOIN (
       SELECT *
       FROM other_table
      ) b
      ON a.id = b.id
      WHERE b.field
     )
"""
    assert_valid_sql(sql)


def test_outer_query_uses_field_without_alias():
    sql = """
select n
from (
 select name n
 from trees_tree
) a;
"""
    assert_valid_sql(sql)


def test_outer_query_uses_field_without_alias_exists_once():
    sql = """
select n
from (
 select name n
 from trees_tree
) a, (
 select name
 from trees_tree
) b;
"""
    assert_valid_sql(sql)


def test_ambiguous_not_aliased_field():
    sql = """
select n
from (
 select name n
 from trees_tree
) a, (
 select name n
 from trees_tree
) b;
"""
    assert_invalid_sql(sql, ['column "n" is ambiguous'])


def test_between_condition_is_valid():
    sql = """
    SELECT *
     FROM t
    WHERE
      f BETWEEN 200 AND 299
    """
    assert_valid_sql(sql)


def test_select_star_replace():
    sql = """
SELECT * REPLACE ("x" AS col)
FROM t
"""
    assert_valid_sql(sql)


def test_select_star_unknown_column():
    sql = """
SELECT * REPLACE ("x" AS col)
FROM (select field from t)
"""
    assert_invalid_sql(sql)


def test_tab_as_token_separator():
    sql = "\tSELECT * FROM\ttable"
    assert_valid_sql(sql)
