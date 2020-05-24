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


def get_tokens_until_one_of(tokens, stop_words):
    argument_tokens = []
    next_token = next(tokens, None)
    while next_token is not None and next_token not in stop_words:
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


def to_tokens(value: str):
    split_on_quotes = split_with_sep(value, "'")
    in_str = False
    for elem in split_on_quotes:
        if elem == "'":
            in_str = not in_str
            yield elem
        elif in_str is True:
            yield elem
        else:
            split_on_quotes2 = split_with_sep(elem, '"')
            in_str2 = False
            for elem2 in split_on_quotes2:
                if elem2 == '"':
                    in_str2 = not in_str2
                    yield elem2
                elif in_str2 is True:
                    yield elem2
                else:
                    split_on_quotes3 = split_with_sep(elem2, "`")
                    in_str3 = False
                    for elem3 in split_on_quotes3:
                        if elem3 == "`":
                            in_str3 = not in_str3
                            yield elem3
                        elif in_str3 is True:
                            yield elem3
                        else:
                            for w1 in elem3.split(" "):
                                for w2 in split_with_sep(w1, ","):
                                    for w3 in split_with_sep(w2, ";"):
                                        for w4 in split_with_sep(w3, "("):
                                            for w5 in split_with_sep(w4, ")"):
                                                for w6 in split_with_sep(w5, "+"):
                                                    for w7 in split_with_sep(w6, "-"):
                                                        for w8 in split_with_sep(
                                                            w7, "*"
                                                        ):
                                                            for w9 in split_with_sep(
                                                                w8, "/"
                                                            ):
                                                                for (
                                                                    w10
                                                                ) in split_with_sep(
                                                                    w9, "="
                                                                ):
                                                                    yield w10.lower()
