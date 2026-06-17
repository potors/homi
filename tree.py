from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from lexer import Token, EOF
from parser import Grammar, SLRParser, GRAMMAR

@dataclass
class AutomationFile:
    automations: list[Automation]

@dataclass
class Automation:
    name: str
    rules: list

@dataclass
class WhenRule:
    event: str
    args: 'Dict'

@dataclass
class IfRule:
    condition: Any

@dataclass
class DoRule:
    action: str
    args: 'Dict'

@dataclass
class PropertyRule:
    name: str
    value: Any

@dataclass
class ChainedCondition:
    base: Any
    op: str
    rest: Any

@dataclass
class NegatedCondition:
    negation: Any

@dataclass
class ParenCondition:
    inner: Any
    chain: Any

@dataclass
class Chain:
    op: str
    condition: Any

@dataclass
class CallNegation:
    name: str
    args: 'Dict'

@dataclass
class NotNegation:
    inner: Any

@dataclass
class BoolValue:
    value: bool

@dataclass
class IdValue:
    name: str

@dataclass
class StrValue:
    raw: str

@dataclass
class ListValue:
    items: list

@dataclass
class Dict:
    props: list

@dataclass
class Property:
    name: str
    value: Any

@dataclass
class BinOp:
    op: str
    left: Any
    right: Any

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class NumLiteral:
    raw: str

# this is an extended parser to build the ast while parsing
# with all the changes the parser itself became outdated lol
class ASTParser(SLRParser):
    def build(self, tokens: list[Token]) -> AutomationFile:
        self._sem: list[Any] = []
        self._result: Any = None

        errors = self._parse_with_sem(tokens)
        for e in errors:
            print(f"[parse] {e.message}")

        root = self._result

        if isinstance(root, list):
            return AutomationFile(automations=root)

        if isinstance(root, Automation):
            return AutomationFile(automations=[root])

        if root is None:
            return AutomationFile(automations=[])

        return AutomationFile(automations=[root])

    def _parse_with_sem(self, tokens: list[Token]):
        stack: list[int | str] = [0]
        errors = []
        sem = self._sem

        i = 0
        while True:
            state = int(stack[-1])

            # hack fix
            if i >= len(tokens):
                # we got past EOF wtf
                errors.append(type('E', (), {
                    'message': f"unexpected EOF"
                }))

                if '}' in [s for (st, s) in self.actions if st == state]:
                    errors.append(type('E', (), {
                        'message': f"unclosed {{"
                    }))

                    tokens.append(Token('}', '}'))
                    tokens.append(Token(EOF, EOF))

                    continue

                return errors

            token = tokens[i]

            action = self.actions.get((state, token.type))
            if action is None:
                expected = [s for (st, s) in self.actions if st == state]

                if len(expected) == 1:
                    errors.append(type('E', (), {
                        'token': token,
                        'message': f"[Transform] {token!r} -> {expected[0]!r}"
                    })())
                    token.type = expected[0]
                    continue

                errors.append(type('E', (), {
                    'token': token,
                    'message': f"[Ignore] {token!r} not in {expected!r}"
                })())
                tokens.pop(i)
                continue

            match action[0]:
                case "shift":
                    sem.append(token)
                    stack.append(token.type)
                    stack.append(action[1])
                    if token.value is not None:
                        i += 1

                case "reduce":
                    rule_idx = action[1]
                    name, syms = self.grammar.rules[rule_idx]
                    n = len(syms)
                    children = sem[-n:] if n else []
                    if n:
                        del sem[-n:]
                        del stack[-n * 2:]

                    node = self._sem_action(name, syms, children)
                    sem.append(node)

                    prev = int(stack[-1])
                    nxt = self.gotos.get((prev, name))
                    if nxt is None:
                        raise ValueError(f"goto undef {prev} {name!r}")
                    stack.append(name)
                    stack.append(nxt)

                case "accept":
                    self._result = sem[-1] if sem else None
                    return errors

    def _sem_action(self, name: str, syms: list[str], ch: list[Any]) -> Any:
        def tv(n):
            x = ch[n]
            return x.value if isinstance(x, Token) else x

        match name:
            case "AUTOMATION'" if not syms:     return []
            case "AUTOMATION'":                 return ch[0]

            case "AUTOMATIONS" if len(syms) == 2:    return ch[0] + [ch[1]]
            case "AUTOMATIONS":                      return [ch[0]]

            case "AUTOMATION" if len(syms) == 4:     return Automation(name=tv(1), rules=[])
            case "AUTOMATION":                       return Automation(name=tv(1), rules=ch[3])

            case "RULES" if len(syms) == 2:          return ch[0] + [ch[1]]
            case "RULES":                            return [ch[0]]

            case "RULE" if syms == ["when","Id","DICT"]:  return WhenRule(event=tv(1), args=ch[2])
            case "RULE" if syms == ["if","CONDITION"]:    return IfRule(condition=ch[1])
            case "RULE" if syms == ["do","Id","DICT"]:    return DoRule(action=tv(1), args=ch[2])
            case "RULE":                                  return ch[0]

            case "CONDITION" if syms == ["(","CONDITION",")","CHAIN"]:
                return ParenCondition(inner=ch[1], chain=ch[3])

            case "CONDITION":
                base = NegatedCondition(negation=ch[0])

                chain = ch[1]
                if chain:
                    return ChainedCondition(base=base, op=chain.op, rest=chain.condition)

                return base

            case "CHAIN" if not syms:                return None
            case "CHAIN":                            return Chain(op=tv(0), condition=ch[1])

            case "NEGATION" if syms == ["not","NEGATION"]:  return NotNegation(inner=ch[1])
            case "NEGATION":                                return CallNegation(name=tv(0), args=ch[1])

            case "PROPERTY":                         return Property(name=tv(0), value=ch[1])
            case "PROPERTIES" if len(syms) == 2:     return ch[0] + [ch[1]]
            case "PROPERTIES":                       return [ch[0]]

            case "VALUE" if syms == ["true"]:        return BoolValue(value=True)
            case "VALUE" if syms == ["false"]:       return BoolValue(value=False)
            case "VALUE" if syms == ["Id"]:          return IdValue(name=tv(0))
            case "VALUE" if syms == ["Str"]:         return StrValue(raw=tv(0))
            case "VALUE":                            return ch[0]

            case "VALUES" if len(syms) == 2:         return ch[0] + [ch[1]]
            case "VALUES":                           return [ch[0]]

            case "LIST" if len(syms) == 2:           return ListValue(items=[])
            case "LIST":                             return ListValue(items=ch[1])

            case "DICT" if len(syms) == 2:           return Dict(props=[])
            case "DICT":                             return Dict(props=ch[1])

            case "EXPR" if len(syms) == 3:           return BinOp(op=tv(1), left=ch[0], right=ch[2])
            case "EXPR":                             return ch[0]

            case "EXPR¹" if len(syms) == 3:          return BinOp(op=tv(1), left=ch[0], right=ch[2])
            case "EXPR¹":                            return ch[0]

            case "EXPR²" if len(syms) == 3:          return BinOp(op="**",  left=ch[0], right=ch[2])
            case "EXPR²":                            return ch[0]

            case "EXPR³" if syms in [["+","EXPR³"],["-","EXPR³"]]:
                return UnaryOp(op=tv(0), operand=ch[1])

            case "EXPR³" if syms == ["(","EXPR",")"]:  return ch[1]
            case "EXPR³":                              return NumLiteral(raw=tv(0))

            case _:
                return ch[0] if len(ch) == 1 else ch

def pretty(node: Any, depth: int = 0) -> str:
    pad = "  " * depth
    match node:
        case AutomationFile(automations=autos):
            body = "\n".join(pretty(a, depth+1) for a in autos)
            return f"{pad}AutomationFile\n{body}"

        case Automation(name=n, rules=rs):
            body = "\n".join(pretty(r, depth+1) for r in rs)
            return f"{pad}Automation({n!r})\n{body}"

        case WhenRule(event=e, args=a):
            return f"{pad}When({e!r})\n{pretty(a, depth+1)}"

        case DoRule(action=a, args=d):
            return f"{pad}Do({a!r})\n{pretty(d, depth+1)}"

        case IfRule(condition=c):
            return f"{pad}If\n{pretty(c, depth+1)}"

        case PropertyRule(name=n, value=v):
            return f"{pad}PropertyRule({n!r})\n{pretty(v, depth+1)}"

        case Property(name=n, value=v):
            return f"{pad}.{n} =\n{pretty(v, depth+1)}"

        case Dict(props=ps):
            body = "\n".join(pretty(p, depth+1) for p in ps)
            return f"{pad}Dict\n{body}" if body else f"{pad}Dict{{}}"

        case ListValue(items=its):
            body = "\n".join(pretty(it, depth+1) for it in its)
            return f"{pad}List\n{body}" if body else f"{pad}List[]"

        case BinOp(op=op, left=l, right=r):
            return f"{pad}BinOp({op!r})\n{pretty(l,depth+1)}\n{pretty(r,depth+1)}"

        case UnaryOp(op=op, operand=o):
            return f"{pad}UnaryOp({op!r})\n{pretty(o,depth+1)}"

        case NumLiteral(raw=r):
            return f"{pad}Num({r})"

        case BoolValue(value=v):
            return f"{pad}Bool({v})"

        case IdValue(name=n):
            return f"{pad}Id({n!r})"

        case StrValue(raw=r):
            return f"{pad}Str({r!r})"

        case ChainedCondition(base=b, op=op, rest=rest):
            return f"{pad}Chain({op!r})\n{pretty(b,depth+1)}\n{pretty(rest,depth+1)}"

        case NegatedCondition(negation=n):
            return f"{pad}Negated\n{pretty(n,depth+1)}"

        case ParenCondition(inner=i, chain=c):
            s = f"{pad}Paren\n{pretty(i,depth+1)}"
            if c:
                s += f"\n{pretty(c,depth+1)}"

            return s

        case NotNegation(inner=i):
            return f"{pad}Not\n{pretty(i,depth+1)}"

        case CallNegation(name=n, args=a):
            return f"{pad}Call({n!r})\n{pretty(a,depth+1)}"

        case Chain(op=op, condition=c):
            return f"{pad}Chain({op!r})\n{pretty(c,depth+1)}"

        case None:
            return f"{pad}(empty)"

        case _:
            print(node)
            return f"{pad}unknown :: {node!r}"

def parse_source(source: str) -> AutomationFile:
    from lexer import Lexer

    g = Grammar(GRAMMAR)
    lexer = Lexer(g.terminals)
    tokens = lexer.tokenize(source)

    return ASTParser(g).build(tokens)

if __name__ == "__main__":
    import sys

    src = sys.stdin.read()
    tree = parse_source(src)
    print(pretty(tree))
