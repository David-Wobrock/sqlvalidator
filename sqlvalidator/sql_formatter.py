import re

import sqlparse


def format_sql(sql_string: str) -> str:
    quotes = None
    possible_quotes = ('"""', "'''", "'", '"')
    for possible_quote in possible_quotes:
        if sql_string.startswith(possible_quote) and sql_string.endswith(
            possible_quote
        ):
            quotes = possible_quote
            break

    if quotes is None:
        # No quotes found
        quotes = ""
        sql_without_quotes = sql_string
    else:
        sql_without_quotes = sql_string[len(quotes) : -len(quotes)]

    formatted_sql = "{quotes}{sql}{quotes}".format(
        quotes=quotes,
        sql=sqlparse.format(
            sql_without_quotes,
            reindent=True,
            keyword_case="upper",
            identifier_case="lower",
            indent_width=2,
        ),
    )

    formatted_sql = format_functions(formatted_sql)
    return formatted_sql


def format_functions(sql: str) -> str:
    """
    Format SQL function in a complete SQL query.
    Upper case the function name.
    Lower case the keyword parameters.
    Keep literal as they are.
    Handle nested functions.
    """

    def format_function_fn(match) -> str:
        groups = match.groups()
        formatted_function = groups[0].upper()

        formatted_parameters = []
        for parameter in groups[1].split(","):
            if re.match(r"[A-Z1-9]+", parameter):
                # Keywords are upper cased by sqlparse
                parameter = parameter.strip().lower()
            else:
                parameter = parameter
            formatted_parameters.append(parameter)

        return "{}({})".format(formatted_function, ", ".join(formatted_parameters))

    return re.sub(r"([a-zA-Z1-9_]+)\((.*)\)", format_function_fn, sql)
