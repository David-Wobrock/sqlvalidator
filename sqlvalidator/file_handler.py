import os
import sys
import tokenize
from typing import IO, List, Optional, Set, Tuple

from . import sql_validator

NO_SQLFORMAT_COMMENT = "nosqlformat"
NO_SQLVALIDATION_COMMENT = "nosqlvalidation"

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


class InputSQLAnalyseInfo:
    def __init__(
        self,
        num_changed_files: int = 0,
        num_changed_sql: int = 0,
        num_invalid_files: int = 0,
        num_invalid_sql: int = 0,
        seen_files: Optional[Set[str]] = None,
    ):
        self.num_changed_files = num_changed_files
        self.num_changed_sql = num_changed_sql
        self.num_invalid_files = num_invalid_files
        self.num_invalid_sql = num_invalid_sql
        self.seen_files = seen_files or set()

    def update(self, other_sql_analyse_info):
        self.num_changed_files += other_sql_analyse_info.num_changed_files
        self.num_changed_sql += other_sql_analyse_info.num_changed_sql
        self.num_invalid_files += other_sql_analyse_info.num_invalid_files
        self.num_invalid_sql += other_sql_analyse_info.num_invalid_sql
        self.seen_files |= other_sql_analyse_info.seen_files


def handle_inputs(
    src_inputs: List[str],
    format_input: bool,
    check_input_format: bool,
    validate_input: bool,
    verbose_validate_input: bool,
):
    inputs_info = InputSQLAnalyseInfo()

    for src_input in src_inputs:
        single_input_info = handle_one_input(
            src_input,
            format_input,
            check_input_format,
            validate_input,
            verbose_validate_input,
            inputs_info.seen_files,
        )
        inputs_info.update(single_input_info)

    if format_input or check_input_format:
        print_format_summary(
            inputs_info.num_changed_files,
            inputs_info.num_changed_sql,
            check_input_format,
        )
    if validate_input:
        print_validation_summary(
            inputs_info.num_invalid_files, inputs_info.num_invalid_sql
        )

    if (check_input_format and inputs_info.num_changed_sql > 0) or (
        validate_input and inputs_info.num_invalid_sql > 0
    ):
        sys.exit(1)


def handle_one_input(
    src_input: str,
    format_input: bool,
    check_input_format: bool,
    validate_input_format: bool,
    verbose_validate_input_format: bool,
    seen_files: Set[str],
) -> InputSQLAnalyseInfo:

    if os.path.isdir(src_input):
        result_info = analyse_dir(
            src_input,
            format_input,
            check_input_format,
            validate_input_format,
            verbose_validate_input_format,
            seen_files,
        )
    elif os.path.isfile(src_input):
        try:
            result_info = analyse_file(
                src_input,
                format_input,
                check_input_format,
                validate_input_format,
                verbose_validate_input_format,
                seen_files,
            )
        except RecursionError:
            print("could not analyse {}".format(src_input))
            result_info = InputSQLAnalyseInfo()
        except Exception as e:
            print("error analysing {} ({}: {})".format(src_input, type(e).__name__, e))
            result_info = InputSQLAnalyseInfo()
    else:
        print("Error: Invalid input")
        result_info = InputSQLAnalyseInfo()
    return result_info


def analyse_dir(
    dirname: str,
    format_input: bool,
    check: bool,
    validate: bool,
    verbose_validate: bool,
    seen_files: Set[str],
) -> InputSQLAnalyseInfo:
    seen_files = seen_files or set()
    result_infos = InputSQLAnalyseInfo(seen_files=seen_files)

    for root, _, files in os.walk(dirname):
        for filename in files:
            if filename.endswith(".py"):
                abs_filename = os.path.join(root, filename)
                try:
                    file_result_info = analyse_file(
                        abs_filename,
                        format_input,
                        check,
                        validate,
                        verbose_validate,
                        result_infos.seen_files,
                    )
                    result_infos.update(file_result_info)
                except RecursionError:
                    print("could not analyse {}".format(abs_filename))
                except Exception as e:
                    print(
                        "error analysing {} ({}: {})".format(
                            abs_filename, type(e).__name__, e
                        )
                    )

    return result_infos


def analyse_file(
    filename: str,
    format_input: bool,
    check: bool,
    validate: bool,
    verbose_validate: bool,
    seen_files: Set[str],
) -> InputSQLAnalyseInfo:
    abs_filename = os.path.abspath(filename)
    if abs_filename in seen_files:
        return InputSQLAnalyseInfo()
    seen_files.add(abs_filename)

    with open(filename, "r") as file:
        (
            count_changed_sql,
            new_content,
            count_has_errors,
            errors_locations,
        ) = compute_file_content(
            file, format_input or check, validate or verbose_validate
        )

    file_changed = count_changed_sql > 0
    if file_changed:
        starting_text = None
        if format_input:
            with open(filename, "w") as f:
                f.write(new_content)
            starting_text = "reformatted"
        elif check:
            starting_text = "would reformat"

        if starting_text is not None:
            print(
                "{} {} ({} changed SQL)".format(
                    starting_text, filename, count_changed_sql
                )
            )

    file_has_invalid_sql = count_has_errors > 0
    if file_has_invalid_sql and (validate or verbose_validate):
        print(
            "invalid queries in {} ({} invalid SQL)".format(filename, count_has_errors)
        )
        if verbose_validate:
            for error_lineno, errors in errors_locations:
                print("L{} - {}".format(error_lineno, ", ".join(errors)))

    return InputSQLAnalyseInfo(
        num_changed_files=1 if file_changed else 0,
        num_changed_sql=count_changed_sql,
        num_invalid_files=1 if file_has_invalid_sql else 0,
        num_invalid_sql=count_has_errors,
        seen_files=seen_files,
    )


def compute_file_content(
    file: IO, should_format: bool, should_validate: bool
) -> Tuple[int, str, int, list]:
    count_changed_sql = 0
    count_has_errors = 0
    errors_locations = []
    tokens = []

    def handle_string_token(
        token_generator, token_type, token_value, starting, ending, line
    ):
        nonlocal tokens
        nonlocal count_changed_sql
        nonlocal count_has_errors
        nonlocal errors_locations

        if not is_select_string(token_value):
            tokens.append((token_type, token_value, starting, ending, line))
            return

        following_tokens = []
        # Find if the next comment without a string in-between if there is one
        next_token, next_token_value, next_starting, next_ending, next_line = next(
            token_generator, (None, None, None, None, None)
        )
        if next_token is None:
            formatted_sql, sql_query = handle_sql_string(token_value)
            tokens.append((token_type, formatted_sql, starting, ending, line))
            tokens += following_tokens
            if formatted_sql != token_value:
                count_changed_sql += 1
            if not sql_query.is_valid():
                count_has_errors += 1
                errors_locations.append((starting[0], sql_query.errors))
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

        needs_format = should_format and NO_SQLFORMAT_COMMENT not in next_token_value
        needs_validate = (
            should_validate and NO_SQLVALIDATION_COMMENT not in next_token_value
        )
        if next_token != tokenize.COMMENT or needs_format or needs_validate:
            formatted_sql, sql_query = handle_sql_string(token_value)
            if (
                formatted_sql != token_value
                and NO_SQLFORMAT_COMMENT not in next_token_value
            ):
                tokens.append((token_type, formatted_sql, starting, ending, line))
                count_changed_sql += 1
            else:
                tokens.append((token_type, token_value, starting, ending, line))
            if (
                not sql_query.is_valid()
                and NO_SQLVALIDATION_COMMENT not in next_token_value
            ):
                count_has_errors += 1
                errors_locations.append((starting[0], sql_query.errors))

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
    return count_changed_sql, formatted_file_content, count_has_errors, errors_locations


def handle_sql_string(sql_string: str) -> Tuple[str, sql_validator.SQLQuery]:
    """
    Read a SQL string as input, potentially with quotes or not,
    and analyse it in order to get the formatter content and know if it is valid.
    """
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

    sql_query = sql_validator.SQLQuery(sql_string_without_quotes)
    formatted_sql = sql_query.format()

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
    return quoted_sql, sql_query


def is_select_string(token_value: str) -> bool:
    cleaned_value = token_value.lower().lstrip(" \n'\"`ufbr")
    lines = cleaned_value.splitlines()
    if not lines:
        return False
    return lines[0].split(" ", maxsplit=1)[0] == "select"


def print_format_summary(num_changed_files: int, changed_sql: int, check: bool):
    content = "would be reformatted" if check else "reformatted"

    if changed_sql > 0:
        num_files_str = "{} file{}".format(
            num_changed_files, "s" if num_changed_files > 1 else ""
        )
        details = "{} changed SQL queries".format(changed_sql)

        print("{} {} ({}).".format(num_files_str, content, details))
    else:
        print("No file {}.".format(content))


def print_validation_summary(num_invalid_sql_files: int, num_invalid_sql_queries: int):
    if num_invalid_sql_queries > 0:
        print(
            "{} file{} detected with invalid SQL ({} invalid SQL quer{}).".format(
                num_invalid_sql_files,
                "s" if num_invalid_sql_files > 1 else "",
                num_invalid_sql_queries,
                "ies" if num_invalid_sql_queries > 1 else "y",
            )
        )
    else:
        print("No invalid queries found.")
