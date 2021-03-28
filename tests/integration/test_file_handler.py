from io import StringIO

from sqlvalidator import file_handler


def test_format_file():
    file_content = "'''select id from table_stmt;'''"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    expected_file_content = "'''\nSELECT id\nFROM table_stmt;\n'''"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_format_file_multilines():
    file_content = "'select id from table_stmt'"
    input_file = StringIO(file_content)
    _, new_content, _, _ = file_handler.compute_file_content(input_file, True, False)
    expected_file_content = "'''\nSELECT id\nFROM table_stmt\n'''"
    assert new_content == expected_file_content


def test_format_file_multiline_sql():
    file_content = "'''\nselect\n   id  \n   from table_stmt\n;\n'''"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    expected_file_content = "'''\nSELECT id\nFROM table_stmt;\n'''"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_format_file_multiline_sql_with_prefix():
    file_content = "r'''\nselect\n   id  \n   from table_stmt\n;\n'''"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    expected_file_content = "r'''\nSELECT id\nFROM table_stmt;\n'''"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_format_sql_string_with_strformat_call():
    file_content = "'select id from {}'.format(__file__)"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    expected_file_content = "'''\nSELECT id\nFROM {}\n'''.format(__file__)"
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_no_format_file():
    file_content = "'select id from t'  # nosqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    assert num_changed_sql == 0
    assert new_content == file_content


def test_no_format_sql_string_with_strformat_call():
    file_content = "'select id from {}'.format(__file__)  # nosqlformat"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    assert num_changed_sql == 0
    assert new_content == file_content


def test_two_following_statements():
    file_content = "sql = ('select * from t;', 'select count(*) from t;')"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    expected_file_content = (
        "sql = ('''\nSELECT *\nFROM t;\n''', '''\nSELECT COUNT(*)\nFROM t;\n''')"
    )
    assert num_changed_sql == 2
    assert new_content == expected_file_content


def test_two_following_statements_second_noformat():
    file_content = (
        "sql = (\n'select * from t;', 'select count(*) from t;'  # nosqlformat\n)"
    )
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    expected_file_content = "sql = (\n'''\nSELECT *\nFROM t;\n''', 'select count(*) from t;'  # nosqlformat\n)"  # noqa
    assert num_changed_sql == 1
    assert new_content == expected_file_content


def test_two_following_statements_both_no_format():
    file_content = "sql = (\n'select * from t;'  # nosqlformat\n, 'select count(*) from t;'  # nosqlformat\n)"  # noqa
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    assert num_changed_sql == 0
    assert new_content == file_content


def test_string_starting_with_selected():
    file_content = "'selected string'"
    input_file = StringIO(file_content)
    num_changed_sql, new_content, _, _ = file_handler.compute_file_content(
        input_file, True, False
    )
    assert num_changed_sql == 0
    assert new_content == file_content
