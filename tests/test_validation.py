import unittest

import sqlvalidator


class BasicSelectValidationTestCase(unittest.TestCase):
    def assertValidSQL(self, sql):
        sql_query = sqlvalidator.parse(sql)
        self.assertTrue(sql_query.is_valid())

    def assertInvalidSQL(self, sql):
        sql_query = sqlvalidator.parse(sql)
        self.assertFalse(sql_query.is_valid())

    def test_select_star_from(self):
        sql = "SELECT * FROM table"
        self.assertValidSQL(sql)

    def test_select_field_from(self):
        sql = "SELECT field FROM table"
        self.assertValidSQL(sql)

    def test_nested_select(self):
        sql = "SELECT field FROM (SELECT * FROM table)"
        self.assertValidSQL(sql)

    @unittest.skip("all sql statements are valid, validation not implemented yet")
    def test_nested_select_without_field(self):
        sql = "SELECT field2 FROM (SELECT field1 FROM table)"
        self.assertInvalidSQL(sql)

    @unittest.skip("all sql statements are valid, validation not implemented yet")
    def test_nested_select_with_start(self):
        sql = "SELECT * FROM (SELECT field1 FROM table)"
        self.assertValidSQL(sql)
