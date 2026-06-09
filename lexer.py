import re

EOF = "$"

class Token:
    def __init__(self, typ: str, val: str, pos: int | None = None):
        self.type = typ
        self.value = val
        self.pos = pos
        self.ln = 0
        self.col = 0

    def __str__(self):
        return f"Token{ f"[{self.ln}:{self.col}]" if self.pos is not None else "" }({ self.type!r }, { self.value!r })"

    def __repr__(self):
        return self.type

class Lexer:
    def __init__(self, terminals: set[str]):
        self.terminals = sorted(terminals, key=len, reverse=True)

    def token(self, text: str) -> Token | None:
        match = lambda x: (re.search(x, text) or [None])[0]

        if symbol := match(r'^".*"'):
            return Token("Str", symbol)

        if symbol := match(r'^0[xob][0-9a-fA-F]+'):
            return Token("Num", symbol)

        if symbol := match(r'^\d+\.\d+'):
            return Token("Num", symbol)

        if symbol := match(r'^\d+'):
            return Token("Num", symbol)

        if symbol := match(r'^[a-zA-Z0-9-_\.]+'):
            if symbol in self.terminals:
                return Token(symbol, symbol)

            return Token("Id", symbol)

        for term in self.terminals:
            if text[:len(term)] == term:
                return Token(term, term)


    def tokenize(self, text: str) -> list[Token]:
        tokens: list[Token] = []

        pos = 0
        line = 0
        col = 0
        while len(text) > 0:
            if text[0] == '\n':
                text = text[1:]
                line += 1
                col = 0
                continue

            if text[0].isspace():
                text = text[1:]
                pos += 1
                col += 1
                continue

            if text.startswith('#'):
                end = text.find('\n')
                text = text[end:]
                line += 1
                pos += end
                col += end
                continue

            token = self.token(text)
            if not token:
                # skip invalid char (wtf?)
                if len(text) > 0:
                    text = text[1:]
                    pos += 1
                    col += 1
                    continue

                break

            token.pos = pos
            token.ln = line
            token.col = col

            pos += len(token.value)
            col += len(token.value)

            tokens.append(token)
            text = text[len(token.value):]

        tokens.append(Token(EOF, EOF))
        return tokens

if __name__ == "__main__":
    import sys

    src = sys.stdin.read()
    lexer = Lexer({ sym for sym in 'automation { } when if do ( ) and or not true false [ ] + - * / % **'.split(' ') })
    tokens = lexer.tokenize(src)

    for token in tokens:
        print(token)
