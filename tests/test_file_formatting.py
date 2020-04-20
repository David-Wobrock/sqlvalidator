from io import StringIO

from sqlvalidator import file_formatter


def test_format_file():
    file_content = "'''select id from table_stmt'''#sqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "'''SELECT id\nFROM table_stmt'''#sqlformat"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_format_file_multilines():
    file_content = "'select id from table_stmt'#sqlformat"
    input_file = StringIO(file_content)
    _, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "'''SELECT id\nFROM table_stmt'''#sqlformat"
    assert new_content == expected_file_content


def test_missing_formatting_comment():
    file_content = "'select id from table_stmt'"
    input_file = StringIO(file_content)
    _, new_content = file_formatter.get_formatted_file_content(input_file)
    assert new_content == file_content
