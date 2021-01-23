from typing import Optional

STRING_SPLIT_TOKENS = ("'", '"', "`")
WHITESPACE_SPLIT_TOKENS = (" ", "\n")
KEPT_SPLIT_TOKENS = (
    ",",
    ";",
    "(",
    ")",
    "[",
    "]",
    "+",
    "-",
    "*",
    "/",
    "=",
    "<",
    ">",
    ".",
)
MERGE_TOKENS = ("<>", "<=", ">=")


def lower(s: Optional[str]) -> Optional[str]:
    return s.lower() if s else s


def get_tokens_until_closing_parenthesis(tokens):
    argument_tokens = []
    next_token = next(tokens, None)
    count_parenthesis = 0
    while next_token is not None and not (next_token == ")" and count_parenthesis == 0):
        argument_tokens.append(next_token)
        if next_token == "(":
            count_parenthesis += 1
        elif next_token == ")":
            count_parenthesis -= 1
        next_token = next(tokens, None)

    return argument_tokens


def get_tokens_until_one_of(tokens, stop_words, first_token=None, keep=None):
    argument_tokens = [first_token] if first_token is not None else []
    keep = keep or []

    next_token = next(tokens, None)
    count_parenthesis = 0 if first_token != "(" else 1
    count_square_brackets = 0 if first_token != "[" else 1
    while next_token is not None and not (
        lower(next_token) in stop_words
        and count_parenthesis <= 0
        and count_square_brackets <= 0
        and (
            not argument_tokens
            or (lower(argument_tokens[-1]), lower(next_token)) not in keep
        )
    ):
        argument_tokens.append(next_token)
        if next_token == "(":
            count_parenthesis += 1
        elif next_token == ")":
            count_parenthesis -= 1
        elif next_token == "[":
            count_square_brackets += 1
        elif next_token == "]":
            count_square_brackets -= 1
        next_token = next(tokens, None)

    return argument_tokens, next_token


def get_tokens_until_not_in(tokens, kept_words, first_token=None):
    argument_tokens = [first_token] if first_token is not None else []
    next_token = next(tokens, None)
    while next_token is not None and lower(next_token) in kept_words:
        argument_tokens.append(next_token)
        next_token = next(tokens, None)

    return argument_tokens, next_token


def split_with_sep(s: str, sep: str):
    splitted = s.split(sep)
    for word in splitted[:-1]:
        if word:
            yield word
        yield sep
    if splitted[-1]:
        yield splitted[-1]


def merge_stream(s, goals):
    for element in s:
        matching_goals = [g for g in goals if g.startswith(element)]
        if not matching_goals:
            yield element
            continue
        next_element = next(s, None)
        if not next_element:
            yield element
            continue

        twice_matching_goals = [
            g for g in matching_goals if (element + next_element) == g
        ]
        if len(twice_matching_goals) > 1:
            raise ValueError("Should not reach here")
        elif twice_matching_goals:
            yield twice_matching_goals[0]
        else:
            yield element
            yield next_element


def _split_on_string_token(token: str, value: str):
    split_result = split_with_sep(value, token)
    in_str = False
    for elem in split_result:
        if elem == token:
            in_str = not in_str
            yield elem
        elif in_str is True:
            yield elem
        else:
            yield from split_tokens(elem)


def _split_on_whitespace_token(token: str, value: str):
    for elem in value.split(token):
        if elem:
            yield from split_tokens(elem)


def _split_on_kept_token(token: str, value: str):
    for elem in split_with_sep(value, token):
        yield from split_tokens(elem)


def split_tokens(value: str):
    for string_token in STRING_SPLIT_TOKENS:
        if string_token in value:
            yield from _split_on_string_token(string_token, value)
            return

    for whitespace_token in WHITESPACE_SPLIT_TOKENS:
        if whitespace_token in value:
            yield from _split_on_whitespace_token(whitespace_token, value)
            return

    for kept_token in KEPT_SPLIT_TOKENS:
        if kept_token in value and value != kept_token:
            yield from _split_on_kept_token(kept_token, value)
            return

    yield value


def to_tokens(value: str):
    tokens = split_tokens(value)
    yield from merge_stream(tokens, MERGE_TOKENS)
