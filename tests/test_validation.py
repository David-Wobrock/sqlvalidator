import pytest

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


@pytest.mark.skip("all sql statements are valid, validation not implemented yet")
def test_nested_select_without_field():
    sql = "SELECT field2 FROM (SELECT field1 FROM table)"
    assert_invalid_sql(sql)


@pytest.mark.skip("all sql statements are valid, validation not implemented yet")
def test_nested_select_with_start():
    sql = "SELECT * FROM (SELECT field1 FROM table)"
    assert_invalid_sql(sql)
