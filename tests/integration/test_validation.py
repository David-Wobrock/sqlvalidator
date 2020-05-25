import sqlvalidator


def assert_valid_sql(sql):
    sql_query = sqlvalidator.parse(sql)
    assert sql_query.is_valid() is True


def assert_invalid_sql(sql):
    sql_query = sqlvalidator.parse(sql)
    assert sql_query.is_valid() is False


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


def test_nested_select_with_start():
    sql = "SELECT * FROM (SELECT field1 FROM table)"
    assert_invalid_sql(sql)


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
