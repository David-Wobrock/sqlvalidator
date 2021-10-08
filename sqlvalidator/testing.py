import sqlvalidator


def assert_valid_sql(sql):
    sql_query = sqlvalidator.parse(sql)
    assert sql_query.is_valid() is True, sql_query.errors


def assert_invalid_sql(sql):
    sql_query = sqlvalidator.parse(sql)
    assert sql_query.is_valid() is False
