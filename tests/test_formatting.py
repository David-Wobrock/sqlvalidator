import unittest

from sqlvalidator.sql_formatter import format_sql


class SQLFormattingTestCase(unittest.TestCase):
    def test_format_select_star(self):
        sql = "select * from table;"
        expected = """
SELECT *
FROM TABLE;
"""
        self.assertEqual(expected.strip(), format_sql(sql))

    def test_upper_function_name(self):
        sql = "select sum(column) from table;"
        expected = """
SELECT SUM(column)
FROM TABLE;
"""
        self.assertEqual(expected.strip(), format_sql(sql))

    def test_nested_function_name(self):
        sql = "select ifnull(sum(column), 'NOTHING') from table;"
        # TODO: SUM should be capitalised
        expected = """
SELECT IFNULL(sum(column), 'NOTHING')
FROM TABLE;
"""
        self.assertEqual(expected.strip(), format_sql(sql))
