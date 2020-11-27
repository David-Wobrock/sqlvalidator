from io import StringIO

from sqlvalidator import file_formatter


def test_format_file():
    file_content = "'''select id from table_stmt;'''#sqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "'''\nSELECT id\nFROM table_stmt;\n'''#sqlformat"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_format_file_multilines():
    file_content = "'select id from table_stmt'  #sqlformat"
    input_file = StringIO(file_content)
    _, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "'''\nSELECT id\nFROM table_stmt\n'''  #sqlformat"
    assert new_content == expected_file_content


def test_format_file_multiline_sql():
    file_content = "'''\nselect\n   id  \n   from table_stmt\n;\n'''#sqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "'''\nSELECT id\nFROM table_stmt;\n'''#sqlformat"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_format_file_multiline_sql_with_prefix():
    file_content = "r'''\nselect\n   id  \n   from table_stmt\n;\n'''#sqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "r'''\nSELECT id\nFROM table_stmt;\n'''#sqlformat"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_missing_formatting_comment():
    file_content = "'select id from table_stmt'"
    input_file = StringIO(file_content)
    _, new_content = file_formatter.get_formatted_file_content(input_file)
    assert new_content == file_content


def test_format_sql_string_with_strformat_call():
    file_content = "'select id from {}'.format(__file__) # sqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content = file_formatter.get_formatted_file_content(input_file)
    expected_file_content = "'''\nSELECT id\nFROM {}\n'''.format(__file__) # sqlformat"
    assert num_changed_sql == 1
    assert new_content == expected_file_content
