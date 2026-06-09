from typing import Any
from tree import (
    NegatedCondition, ChainedCondition, ParenCondition,
    CallNegation, NotNegation,
)

def _leaf(call: CallNegation) -> dict:
    entry = {"condition": call.name}
    entry.update({p.name: _val_simple(p.value) for p in call.args.props})

    return entry


def _val_simple(node: Any) -> Any:
    from tree import BoolValue, IdValue, StrValue, NumLiteral, ListValue, Dict, BinOp, UnaryOp

    match node:
        case BoolValue(value=v):   return v
        case IdValue(name=n):      return n
        case StrValue(raw=r):      return r.strip('"')
        case NumLiteral(raw=r):    return float(r) if '.' in r else int(r, 0)
        case ListValue(items=its): return [_val_simple(i) for i in its]
        case Dict(props=[]):       return {}
        case Dict(props=ps):       return {p.name: _val_simple(p.value) for p in ps}
        case BinOp(op=op, left=l, right=r): return f"{_val_simple(l)} {op} {_val_simple(r)}"
        case UnaryOp(op=op, operand=o):     return f"{op}{_val_simple(o)}"
        case _:                    return str(node)


def _unwrap_negation(neg):
    count = 0
    node = neg

    # NegatedCondition is the outer wrapper from CONDITION -> NEGATION CHAIN
    if isinstance(node, NegatedCondition):
        node = node.negation

    while isinstance(node, NotNegation):
        count += 1
        node = node.inner

    # node is now CallNegation
    return count, node


def condition_to_yaml(node: Any) -> dict | list:
    match node:
        case NegatedCondition():
            not_count, call = _unwrap_negation(node)
            leaf = _leaf(call)

            # wrap in not conditions as needed
            result = leaf

            for _ in range(not_count):
                result = {"condition": "not", "conditions": [result]}

            return result

        case ChainedCondition(_, op=op):
            # flatten consecutive same-op chains into a list
            items = _flatten_chain(node)
            return {"condition": op, "conditions": items}

        case ParenCondition(inner=inner, chain=chain):
            if chain is None:
                return condition_to_yaml(inner)

            # chain attaches an and/or to the paren group
            # inner is the first condition, chain adds more
            inner_yaml = condition_to_yaml(inner)
            rest_yaml  = condition_to_yaml(chain.condition)

            rest_list  = rest_yaml if isinstance(rest_yaml, list) else [rest_yaml]
            first_list = inner_yaml if isinstance(inner_yaml, list) else [inner_yaml]

            return {"condition": chain.op, "conditions": first_list + rest_list}

        case _:
            return {"condition": str(node)}


def _flatten_chain(node: Any) -> list:
    items = []
    _collect(node, items)

    return items


def _collect(node: Any, out: list):
    match node:
        case ChainedCondition(base=base, op=_, rest=rest):
            _collect(base, out)
            _collect(rest, out)

        case NegatedCondition():
            not_count, call = _unwrap_negation(node)
            leaf = _leaf(call)
            result = leaf

            for _ in range(not_count):
                result = {"condition": "not", "conditions": [result]}

            out.append(result)

        case ParenCondition():
            out.append(condition_to_yaml(node))

        case _:
            out.append({"condition": str(node)})
