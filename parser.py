from collections import defaultdict
from lexer import Token, EOF
from dataclasses import dataclass

GRAMMAR = '''FILE -> AUTOMATION'
            AUTOMATION' -> AUTOMATIONS
            AUTOMATION' -> ε
            AUTOMATION -> automation Str { }
            AUTOMATION -> automation Str { RULES }
            AUTOMATIONS -> AUTOMATIONS AUTOMATION
            AUTOMATIONS -> AUTOMATION
            RULE -> when Id DICT
            RULE -> if CONDITION
            RULE -> do Id DICT
            RULE -> PROPERTY
            RULES -> RULES RULE
            RULES -> RULE
            CONDITION -> ( CONDITION ) CHAIN
            CONDITION -> NEGATION CHAIN
            CHAIN -> and CONDITION
            CHAIN -> or CONDITION
            CHAIN -> ε
            NEGATION -> not NEGATION
            NEGATION -> Id DICT
            PROPERTY -> Id VALUE
            PROPERTIES -> PROPERTIES PROPERTY
            PROPERTIES -> PROPERTY
            VALUE -> true
            VALUE -> false
            VALUE -> Id
            VALUE -> Str
            VALUE -> LIST
            VALUE -> DICT
            VALUE -> EXPR
            VALUES -> VALUES VALUE
            VALUES -> VALUE
            LIST -> [ ]
            LIST -> [ VALUES ]
            DICT -> { }
            DICT -> { PROPERTIES }
            EXPR -> EXPR + EXPR¹
            EXPR -> EXPR - EXPR¹
            EXPR -> EXPR¹
            EXPR¹ -> EXPR¹ * EXPR²
            EXPR¹ -> EXPR¹ / EXPR²
            EXPR¹ -> EXPR¹ % EXPR²
            EXPR¹ -> EXPR²
            EXPR² -> EXPR³ ** EXPR²
            EXPR² -> EXPR³
            EXPR³ -> + EXPR³
            EXPR³ -> - EXPR³
            EXPR³ -> ( EXPR )
            EXPR³ -> Num'''

def rules(text: str) -> list[tuple[str, list[str]]]:
    rules = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line[0] == '#':
            continue

        lhs, _, rhs = line.partition('->')
        name = lhs.strip()
        rule = rhs.strip()

        if not name or not rule:
            continue

        if rule == 'ε' or rule == '':
            rules.append((name, []))
        else:
            rules.append((name, rule.split(' ')))

    return rules

class Grammar:
    def __init__(self, text: str):
        self.rules = rules(text)
        self.start = self.rules[0][0]

        self.nonterminals = { lhs for lhs, _ in self.rules }

        self.terminals = set()
        for _, rule in self.rules:
            for sym in rule:
                if sym in self.nonterminals:
                    continue

                self.terminals.add(sym)

        self.terminals.add(EOF)

    def first(self, symbols: list[str], visiting: set[str] = set()) -> set[str]:
        result = set()

        for sym in symbols:
            f = self._first_sym(sym, visiting)

            result |= f - { 'ε' }

            if 'ε' not in f:
                break
        else:
            result.add('ε')

        return result

    def _first_sym(self, sym: str, visiting: set[str] = set()) -> set[str]:
        if sym not in self.nonterminals:
            return { sym }

        if sym in visiting:
            return set()

        visiting = visiting | { sym }

        result = set()
        for lhs, rhs in self.rules:
            if lhs != sym:
                continue

            if not rhs:
                result.add('ε')
                continue

            result |= self.first(rhs, visiting)

        return result

    def follow(self) -> dict[str, set[str]]:
        follow: dict[str, set[str]] = defaultdict(set)

        follow[self.start].add(EOF)

        changed = True
        while changed:
            changed = False

            for name, symbols in self.rules:
                for i, symbol in enumerate(symbols):
                    if symbol not in self.nonterminals:
                        continue

                    beta = symbols[i + 1:]
                    first_beta = self.first(beta)

                    before = len(follow[symbol])
                    follow[symbol] |= first_beta - { 'ε' }

                    if 'ε' in first_beta:
                        follow[symbol] |= follow[name]

                    if len(follow[symbol]) != before:
                        changed = True

        return dict(follow)

class LRItem:
    def __init__(self, lhs: str, rhs: tuple[str, ...], dot: int):
        self.lhs = lhs
        self.rhs = rhs
        self.dot = dot

    @property
    def done(self):
        return self.dot >= len(self.rhs)

    @property
    def next_sym(self):
        return None if self.done else self.rhs[self.dot]

    def __eq__(self, other):
        return (self.lhs, self.rhs, self.dot) == (other.lhs, other.rhs, other.dot)

    def __hash__(self):
        return hash((self.lhs, self.rhs, self.dot))

    def __repr__(self):
        r = list(self.rhs)
        r.insert(self.dot, "·")
        return f"{self.lhs} -> {' '.join(r)}"

@dataclass
class ParseError:
    token: Token
    message: str

class SLRParser:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.follows = grammar.follow()
        self._build_tables()

    def _closure(self, items: frozenset[LRItem]) -> frozenset[LRItem]:
        result = set(items)
        queue = list(items)

        while queue:
            item = queue.pop()
            sym = item.next_sym

            if sym is None or sym not in self.grammar.nonterminals:
                continue

            for lhs, rhs in self.grammar.rules:
                if lhs != sym:
                    continue

                new = LRItem(lhs, tuple(rhs), 0)
                if new not in result:
                    result.add(new)
                    queue.append(new)

        return frozenset(result)

    def _goto(self, items: frozenset[LRItem], sym: str) -> frozenset[LRItem]:
        moved = {LRItem(it.lhs, it.rhs, it.dot + 1)
                 for it in items if not it.done and it.next_sym == sym}

        return self._closure(frozenset(moved))

    def _canonical(self):
        start_item = LRItem(self.grammar.start, tuple(self.grammar.rules[0][1]), 0)
        i0 = self._closure(frozenset([start_item]))
        states = [i0]
        state_index = {i0: 0}
        transitions: dict[tuple[int, str], int] = {}

        queue = [i0]
        while queue:
            state = queue.pop()
            sid = state_index[state]
            syms = {it.next_sym for it in state if not it.done}

            for sym in syms:
                nxt = self._goto(state, str(sym))

                if not nxt:
                    continue

                if nxt not in state_index:
                    state_index[nxt] = len(states)
                    states.append(nxt)
                    queue.append(nxt)

                transitions[(sid, str(sym))] = state_index[nxt]

        return states, transitions

    def _build_tables(self):
        states, transitions = self._canonical()
        self.states = states

        # action[state][terminal] = ('shift', s) | ('reduce', rule_idx) | ('accept',)
        # goto[state][nonterminal] = state
        self.actions: dict[tuple[int, str], tuple] = {}
        self.gotos: dict[tuple[int, str], int] = {}

        rule_list = [(lhs, tuple(rhs)) for lhs, rhs in self.grammar.rules]

        for sid, state in enumerate(states):
            for item in state:
                if not item.done:
                    sym = item.next_sym

                    if sym in self.grammar.terminals:
                        nxt = transitions.get((sid, str(sym)))

                        if nxt is not None:
                            self._set_action(sid, sym, ("shift", nxt))
                else:
                    if item.lhs == self.grammar.start:
                        self._set_action(sid, EOF, ("accept",))
                    else:
                        rule_idx = rule_list.index((item.lhs, item.rhs))

                        for term in self.follows.get(item.lhs, set()):
                            self._set_action(sid, term, ("reduce", rule_idx))

        for (sid, sym), nxt in transitions.items():
            if sym in self.grammar.nonterminals:
                self.gotos[(sid, sym)] = nxt

    def _set_action(self, sid, sym, action):
        key = (sid, sym)

        if key in self.actions and self.actions[key] != action:
            existing = self.actions[key]

            # shift/reduce conflict: always prefer shift
            if action[0] == "shift" and existing[0] == "reduce":
                self.actions[key] = action

            return

        self.actions[key] = action

    def parse(self, tokens: list[Token]) -> list[ParseError]:
        stack: list[int | str] = [0]
        errors: list[ParseError] = []

        # print(tokens)

        i = 0
        while True:
            state = int(stack[-1])

            # hack fix
            if i >= len(tokens):
                # we got past EOF wtf
                errors.append(ParseError(
                    token=Token(EOF, EOF),
                    message=f"unexpected EOF"
                ))

                if '}' in [s for (st, s) in self.actions if st == state]:
                    errors.append(ParseError(
                        token=Token(EOF, EOF),
                        message=f"unclosed {{"
                    ))

                    tokens.append(Token('}', '}'))
                    tokens.append(Token(EOF, EOF))

                    continue

                return errors

            token = tokens[i]

            action = self.actions.get((state, token.type))
            if action is None:
                expected = [s for (st, s) in self.actions if st == state]

                # wrong token only one expected
                if len(expected) == 1:
                    errors.append(ParseError(
                        token=token,
                        message=f"[Transform] Let { token!r } be { expected[0]!r }"
                    ))

                    # this is referenced btw (i hate this language)
                    token.type = expected[0]
                    continue

                # no valid action at all: abort on EOF, otherwise skip token
                if len(expected) == 0:
                    if token.type == EOF:
                        return errors
                    errors.append(ParseError(
                        token=token,
                        message=f"[Ignore] Got {token!r} in dead state"
                    ))
                    tokens.pop(i)
                    continue

                # single expected token -> transform current token
                if len(expected) == 1:
                    errors.append(ParseError(
                        token=token,
                        message=f"[Transform] Let {token!r} be {expected[0]!r}"
                    ))
                    token.type = expected[0]
                    continue

                # multiple expectations: skip token, but never discard EOF
                errors.append(ParseError(
                    token=token,
                    message=f"[Ignore] Got {token!r} instead of {expected!r}"
                ))

                if token.type == EOF:
                    return errors

                tokens.pop(i)
                continue

            match action[0]:
                case "shift":
                    state = action[1]
                    stack.append(token.type)
                    stack.append(state)

                    if token.value is None:
                        continue

                    i += 1

                case "reduce":
                    rule = action[1]
                    name, symbols = self.grammar.rules[rule]

                    if len(symbols) > 0:
                        del stack[-len(symbols) * 2:]

                    prev_state = int(stack[-1])
                    stack.append(name)

                    nxt = self.gotos.get((prev_state, name))
                    if nxt is None:
                        raise ValueError(f"goto undefined state { prev_state } { name!r }")

                    stack.append(nxt)

                case "accept":
                    return errors

if __name__ == '__main__':
    from lexer import Lexer
    import sys

    s = sys.stdin.read()

    lexer = Lexer({ sym for sym in 'automation { } when if do ( ) and or not true false [ ] + - * / % **'.split(' ') })
    tokens = lexer.tokenize(s)

    print('tokens:')
    for token in tokens:
        print(token)

    grammar = Grammar(GRAMMAR)

    print('rules:')
    for rule, symbols in grammar.rules:
        print(2*' ', rule, '->', symbols)

    print('nonterminals:')
    for symbol in grammar.nonterminals:
        print(2*' ', symbol)

    print('terminals:')
    for symbol in grammar.terminals:
        print(2*' ', symbol)

    print('firsts:')
    for rule, symbols in grammar.rules:
        print(2*' ', f'FIRST({ rule }) = { grammar.first(symbols) }')

    print('follows:')
    for rule, symbols in grammar.follow().items():
        print(2*' ', f'FOLLOW({ rule }) = { symbols }')

    parser = SLRParser(grammar)

    try:
        errors = parser.parse(tokens)

        for error in errors:
            print(error)

        for token in tokens:
            print(token)
    except ValueError as e:
        print(e)
