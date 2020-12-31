import os
import sys
import tokenize
from typing import IO, List, Optional, Set, Tuple

from . import sql_formatter

NO_SQLFORMAT_COMMENT = "nosqlformat"

POSSIBLE_QUOTES = ('"""', "'''", '"', "'")
STRING_PREFIXES = (
    "r",
    "u",
    "ur",
    "R",
    "U",
    "UR",
    "Ur",
    "uR",
    "f",
    "F",
    "fr",
    "Fr",
    "fR",
    "FR",
    "rf",
    "rF",
    "Rf",
    "RF",
    "b",
    "B",
    "br",
    "Br",
    "bR",
    "BR",
    "rb",
    "rB",
    "Rb",
    "RB",
)


def format_sql_string(sql_string):
    quotes = None
    quotes_prefix = None

    for possible_quote in POSSIBLE_QUOTES:
        if sql_string.startswith(possible_quote) and sql_string.endswith(
            possible_quote
        ):
            quotes = possible_quote
            break

    if quotes is None:
        for possible_quote in POSSIBLE_QUOTES:
            for prefix in STRING_PREFIXES:
                if sql_string.startswith(
                    prefix + possible_quote
                ) and sql_string.endswith(possible_quote):
                    quotes = possible_quote
                    quotes_prefix = prefix
                    break
            if quotes_prefix is not None:
                break

    assert quotes is not None, "Could not find quotes"

    if quotes_prefix is not None:
        sql_string = sql_string[len(quotes_prefix) :]
    sql_string_without_quotes = sql_string[len(quotes) : -len(quotes)]
    formatted_sql = sql_formatter.format_sql(sql_string_without_quotes)

    if len(quotes) == 1 and "\n" in formatted_sql:
        # Need to change to triple quotes
        if quotes == "'":
            new_quotes = "'''"
        else:
            new_quotes = '"""'
    else:
        new_quotes = quotes

    if len(new_quotes) == 3 and "\n" in formatted_sql:
        quoted_sql = "{prefix}{quotes}\n{sql}\n{quotes}".format(
            prefix=quotes_prefix or "", quotes=new_quotes, sql=formatted_sql
        )
    else:
        quoted_sql = "{prefix}{quotes}{sql}{quotes}".format(
            prefix=quotes_prefix or "", quotes=new_quotes, sql=formatted_sql
        )
    return quoted_sql


def is_select_string(token_value: str) -> bool:
    cleaned_value = token_value.lower().lstrip(" \n'\"`ufbr")
    lines = cleaned_value.splitlines()
    if not lines:
        return False
    return lines[0].split(" ", maxsplit=1)[0] == "select"


def get_formatted_file_content(file: IO) -> Tuple[int, str]:
    count_changed_sql = 0
    tokens = []

    def handle_string_token(
        token_generator, token_type, token_value, starting, ending, line
    ):
        nonlocal tokens
        nonlocal count_changed_sql

        if not is_select_string(token_value):
            tokens.append((token_type, token_value, starting, ending, line))
            return

        following_tokens = []
        # Find if the next comment without a string in-between if there is one
        next_token, next_token_value, next_starting, next_ending, next_line = next(
            token_generator, (None, None, None, None, None)
        )
        if next_token is None:
            formatted_sql = format_sql_string(token_value)
            tokens.append((token_type, formatted_sql, starting, ending, line))
            tokens += following_tokens
            if formatted_sql != token_value:
                count_changed_sql += 1
            return

        following_tokens.append(
            (next_token, next_token_value, next_starting, next_ending, next_line)
        )
        while (
            next_token
            and next_token != tokenize.COMMENT
            and next_token != tokenize.STRING
        ):
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

        if not (
            next_token == tokenize.COMMENT and NO_SQLFORMAT_COMMENT in next_token_value
        ):
            formatted_sql = format_sql_string(token_value)
            tokens.append((token_type, formatted_sql, starting, ending, line))
            if formatted_sql != token_value:
                count_changed_sql += 1
        else:
            tokens.append((token_type, token_value, starting, ending, line))

        if next_token == tokenize.STRING:
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
            tokens += following_tokens

    token_generator = tokenize.generate_tokens(file.readline)
    for token_type, token_value, starting, ending, line in token_generator:
        if token_type == tokenize.STRING:
            handle_string_token(
                token_generator, token_type, token_value, starting, ending, line
            )
        else:
            tokens.append((token_type, token_value, starting, ending, line))

    formatted_file_content = tokenize.untokenize(tokens)
    return count_changed_sql, formatted_file_content


def format_file(
    filename: str, check: bool, seen_files: Optional[Set[str]] = None
) -> Tuple[int, int, Set[str]]:
    seen_files = seen_files or set()

    abs_filename = os.path.abspath(filename)
    if abs_filename in seen_files:
        return 0, 0, seen_files
    seen_files.add(abs_filename)

    with open(filename, "r") as file:
        count_changed_sql, new_content = get_formatted_file_content(file)

    file_changed = count_changed_sql > 0
    if file_changed:
        if not check:
            with open(filename, "w") as f:
                f.write(new_content)
            starting_text = "reformatted"
        else:
            starting_text = "would reformat"

        print(
            "{} {} ({} changed SQL)".format(starting_text, filename, count_changed_sql)
        )

    num_changed_files = 1 if file_changed else 0
    return num_changed_files, count_changed_sql, seen_files


def format_dir(
    dirname: str, check: bool, seen_files: Optional[Set[str]] = None
) -> Tuple[int, int, Set[str]]:
    seen_files = seen_files or set()
    changed_files, total_changed_sql = 0, 0
    for root, _, files in os.walk(dirname):
        for filename in files:
            if filename.endswith(".py"):
                abs_filename = os.path.join(root, filename)
                try:
                    num_files, changed_sql, seen_files = format_file(
                        abs_filename, check, seen_files
                    )
                    changed_files += num_files
                    total_changed_sql += changed_sql
                except RecursionError:
                    print("could not format {}".format(abs_filename))
                except Exception as e:
                    print(
                        "error formatting {} ({}: {})".format(
                            abs_filename, type(e).__name__, e
                        )
                    )

    return changed_files, total_changed_sql, seen_files


def handle_one_input(
    src_input: str,
    format_input=True,
    check_input=False,
    seen_files: Optional[Set[str]] = None,
) -> Tuple[int, int, Set[str]]:
    assert format_input != check_input
    seen_files = seen_files or set()

    if os.path.isfile(src_input):
        try:
            num_files, changed_sql, seen_files = format_file(
                src_input, check_input, seen_files
            )
        except RecursionError:
            print("could not format {}".format(src_input))
            return 0, 0, set()
        except Exception as e:
            print("error formatting {} ({}: {})".format(src_input, type(e).__name__, e))
            return 0, 0, set()

    elif os.path.isdir(src_input):
        num_files, changed_sql, seen_files = format_dir(
            src_input, check_input, seen_files
        )
    else:
        print("Error: Invalid input")
        num_files, changed_sql, seen_files = 0, 0, set()
    return num_files, changed_sql, seen_files


def handle_inputs(src_inputs: List[str], format_input=True, check_input=False):
    assert format_input != check_input

    total_num_files = 0
    total_changed_sql = 0
    seen_files: Set[str] = set()
    for src_input in src_inputs:
        num_files, changed_sql, new_seen_files = handle_one_input(
            src_input, format_input, check_input, seen_files
        )
        total_num_files += num_files
        total_changed_sql += changed_sql
        seen_files |= new_seen_files

    print_summary(total_num_files, total_changed_sql, check_input)
    if total_changed_sql > 0:
        sys.exit(1)


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
