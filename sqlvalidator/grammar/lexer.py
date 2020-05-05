from sqlvalidator.grammar.sql import (
    SelectStatement,
    FunctionCall,
    Column,
    Alias,
    String,
    Integer,
    Parenthesis,
    Table,
)


class ParsingError(Exception):
    pass


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
                                    for w3 in w2.strip().split(";"):
                                        for w4 in split_with_sep(w3, "("):
                                            for w5 in split_with_sep(w4, ")"):
                                                yield w5.lower()


class SQLStatementParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if next_token == "select":
            return SelectStatementParser.parse(tokens)
        raise ParsingError


class SelectStatementParser:
    keywords = ("from",)

    @classmethod
    def parse(cls, tokens):
        expression_tokens, next_token = get_tokens_until_one_of(tokens, cls.keywords)
        expressions = ExpressionListParser.parse(iter(expression_tokens))

        if next_token == "from":
            from_statement = FromStatementParser.parse(tokens)
        else:
            from_statement = None
        return SelectStatement(expressions=expressions, from_statement=from_statement)


class FromStatementParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if next_token == "(":
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            argument = SQLStatementParser.parse(iter(argument_tokens))
            expression = Parenthesis(argument)
        else:
            expression = Table(next_token)
        return expression


class ExpressionListParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens, None)

        expressions = []
        expression_tokens = []
        count_parenthesis = 0
        while next_token is not None:
            expression_tokens.append(next_token)
            if next_token == "(":
                count_parenthesis += 1
            elif next_token == ")":
                count_parenthesis -= 1
            next_token = next(tokens, None)
            if next_token is None or (next_token == "," and count_parenthesis == 0):
                expressions.append(ExpressionParser.parse(iter(expression_tokens)))
                expression_tokens = []
                next_token = next(tokens, None)
        return expressions


class ExpressionParser:
    @staticmethod
    def parse(tokens):
        main_token = next(tokens)
        next_token = next(tokens, None)
        if main_token == "'" or main_token == '"' or main_token == "`":
            expression = String(next_token, quotes=main_token)
            next_token = next(tokens)  # final quote
            if main_token != next_token:
                raise ParsingError("Did not find ending quote")
            next_token = next(tokens, None)
        elif main_token.isdigit():
            expression = Integer(main_token)
        elif main_token == "(":
            argument_tokens = [next_token] + get_tokens_until_closing_parenthesis(
                tokens
            )
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = Parenthesis(*arguments)
            next_token = next(tokens, None)
        elif next_token is not None and next_token == "(":
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = FunctionCall(main_token, *arguments)
            next_token = next(tokens, None)
        else:
            expression = Column(main_token)

        if (
            next_token is not None
            and next_token != ")"
            and next_token != "'"
            and next_token != '"'
            and next_token != "`"
        ):
            if next_token == "as":
                with_as = True
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            return Alias(expression, alias, with_as)
        return expression
