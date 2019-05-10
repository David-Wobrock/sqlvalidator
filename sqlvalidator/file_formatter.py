import os
import sys
import tokenize
from typing import Tuple

from sqlvalidator import sql_formatter


SQLFORMAT_COMMENT = "sqlformat"


def format_file(filename: str, check: bool) -> int:
    count_changed_sql = 0
    tokens = []

    def handle_string_token(
        token_generator, token_type, token_value, starting, ending, line
    ):
        nonlocal tokens
        nonlocal count_changed_sql

        following_tokens = []

        # Find if the next comment without a string in-between
        next_token, next_token_value, next_starting, next_ending, next_line = next(
            token_generator, (None, None, None, None, None)
        )
        if next_token is None:
            tokens.append((token_type, token_value, starting, ending, line))
            return
        following_tokens.append(
            (next_token, next_token_value, next_starting, next_ending, next_line)
        )
        while next_token != tokenize.COMMENT and next_token != tokenize.STRING:
            next_token, next_token_value, next_starting, next_ending, next_line = next(
                token_generator, (None, None, None, None, None)
            )
            if next_token is None:
                tokens.append((token_type, token_value, starting, ending, line))
                tokens += following_tokens
                return
            following_tokens.append(
                (next_token, next_token_value, next_starting, next_ending, next_line)
            )

        if next_token == tokenize.COMMENT and SQLFORMAT_COMMENT in next_token_value:
            formatted_sql = sql_formatter.format_sql(token_value)
            tokens.append((token_type, formatted_sql, starting, ending, line))
            tokens += following_tokens

            if formatted_sql != token_value:
                count_changed_sql += 1
        elif next_token == tokenize.STRING:
            tokens.append((token_type, token_value, starting, ending, line))
            tokens += following_tokens[:-1]
            handle_string_token(
                token_generator,
                next_token,
                next_token_value,
                next_starting,
                next_ending,
                next_line,
            )
        else:
            tokens.append((token_type, token_value, starting, ending, line))
            tokens += following_tokens

    with open(filename, "r") as f:
        token_generator = tokenize.generate_tokens(f.readline)
        for token_type, token_value, starting, ending, line in token_generator:
            if token_type == tokenize.STRING:
                handle_string_token(
                    token_generator, token_type, token_value, starting, ending, line
                )
            else:
                tokens.append((token_type, token_value, starting, ending, line))

        if count_changed_sql > 0:
            if not check:
                output = tokenize.untokenize(tokens)
                with open(filename, "w") as f:
                    f.write(output)
                starting_text = "reformatted"
            else:
                starting_text = "would reformat"

            print(
                "{} {} ({} changed SQL)".format(
                    starting_text, filename, count_changed_sql
                )
            )

        return count_changed_sql


def format_dir(dirname: str, check: bool) -> Tuple[int, int]:
    changed_files, total_changed_sql = 0, 0
    for root, _, files in os.walk(dirname):
        for filename in files:
            if filename.endswith(".py"):
                abs_filename = os.path.join(root, filename)
                try:
                    changed_sql = format_file(abs_filename, check)
                    total_changed_sql += changed_sql
                    if changed_sql:
                        changed_files += 1
                except RecursionError:
                    print("could not format {}".format(filename))

    return changed_files, total_changed_sql


def print_summary(num_changed_files: int, changed_sql: int, check: bool):
    content = "would be reformatted" if check else "reformatted"

    if changed_sql > 0:
        num_files_str = "{} file{}".format(
            num_changed_files, "s" if num_changed_files > 1 else ""
        )
        details = "{} changed SQL queries".format(changed_sql)

        print("{} {} ({}).".format(num_files_str, content, details))
    else:
        print("No file {}.".format(content))


def handle_input(src_input: str, format_input=True, check_input=False):
    assert format_input != check_input

    if os.path.isfile(src_input):
        num_files = 1
        changed_sql = format_file(src_input, check_input)
        print_summary(num_files, changed_sql, check_input)
        if changed_sql > 0:
            sys.exit(1)

    elif os.path.isdir(src_input):
        num_files, changed_sql = format_dir(src_input, check_input)
        print_summary(num_files, changed_sql, check_input)
        if changed_sql > 0:
            sys.exit(1)

    else:
        print("Error: Invalid input")
