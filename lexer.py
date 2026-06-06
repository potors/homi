import re

EOF = "$"

class Token:
    def __init__(self, typ: str, val: str):
        self.type = typ
        self.value = val

    def __str__(self):
        return f"Token({self.type!r}, {self.value!r})"

    def __repr__(self):
        return self.type

class Lexer:
    def __init__(self, terminals: set[str]):
        self.terminals = sorted(terminals, key=len, reverse=True)

    def token(self, text: str) -> Token | None:
        symbol = text.split(' ')[0]

        if re.match(r'".*"', symbol):
            return Token("Str", symbol)

        if re.match(r'0(x|o|b)\d+', symbol):
            return Token("Num", symbol)

        if re.match(r'\d+\.\d+', symbol):
            return Token("Num", symbol)

        if re.match(r'\d+', symbol):
            return Token("Num", symbol)

        if re.match(r'[a-zA-Z0-9-_\.]+', symbol):
            if symbol in self.terminals:
                return Token(symbol, symbol)

            return Token("Id", symbol)

        for term in self.terminals:
            if symbol.startswith(term):
                return Token(term, term)


    def tokenize(self, text: str) -> list[Token]:
        tokens = []

        text = text.replace('\n', ' ')
        text = text.replace('\t', ' ')

        while len(text) > 0:
            text = text.strip()

            if text.startswith('/*'):
                text = text[text.find('*/') + 2:]
                continue

            token = self.token(text)
            if not token:
                # skip invalid char (wtf?)
                if len(text) > 0:
                    text = text[1:]
                    continue

                break

            tokens.append(token)
            text = text[len(token.value):]

        tokens.append(Token(EOF, EOF))
        return tokens

