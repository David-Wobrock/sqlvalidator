from sqlvalidator.grammar.sql import (
    SelectStatement,
    FunctionCall,
    Column,
    Alias,
    String,
    Integer,
    Parenthesis,
    Table,
    ArithmaticOperator,
)
from sqlvalidator.grammar.tokeniser import (
    get_tokens_until_one_of,
    get_tokens_until_closing_parenthesis,
)


class ParsingError(Exception):
    pass


class SQLStatementParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if next_token == "select":
            return SelectStatementParser.parse(tokens)
        raise ParsingError


class SelectStatementParser:
    keywords = ("from", ";")

    @classmethod
    def parse(cls, tokens):
        expression_tokens, next_token = get_tokens_until_one_of(tokens, cls.keywords)
        expressions = ExpressionListParser.parse(iter(expression_tokens))

        if next_token == "from":
            from_statement = FromStatementParser.parse(tokens)
            next_token = next(tokens, None)
        else:
            from_statement = None

        semi_colon = bool(next_token and next_token == ";")
        return SelectStatement(
            expressions=expressions,
            from_statement=from_statement,
            semi_colon=semi_colon,
        )


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
            if next_token and next_token in ("+", "-", "*", "/"):
                left_hand = expression
                symbol = next_token
                right_hand = ExpressionParser.parse(tokens)
                expression = ArithmaticOperator(symbol, left_hand, right_hand)
                next_token = next(tokens, None)

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
            and next_token != ";"
        ):
            if next_token == "as":
                with_as = True
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            return Alias(expression, alias, with_as)
        return expression
