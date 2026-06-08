from typing import Any
from tree import (
    AutomationFile, Automation,
    WhenRule, IfRule, DoRule, Property, PropertyRule,
    BoolValue, IdValue, StrValue, ListValue, Dict,
    BinOp, UnaryOp, NumLiteral,
)


def _val(node: Any) -> Any:
    match node:
        case BoolValue(value=v):    return v
        case IdValue(name=n):       return n
        case StrValue(raw=r):       return r.strip('"')
        case NumLiteral(raw=r):     return float(r) if '.' in r else int(r)
        case ListValue(items=its):  return [_val(i) for i in its]
        case Dict(props=[]):        return {}
        case Dict(props=ps):        return {p.name: _val(p.value) for p in ps}
        case BinOp(op=op, left=l, right=r): return f"{_val(l)} {op} {_val(r)}"
        case UnaryOp(op=op, operand=o):     return f"{op}{_val(o)}"
        case _:                     return str(node)


def _emit_value(val: Any, indent: int) -> str:
    pad = "  " * indent

    if isinstance(val, dict):
        if not val:
            return "{}"

        lines = []
        for k, v in val.items():
            if isinstance(v, list) and v:
                rendered = _emit_value(v, indent)
                lines.append(f"{pad}{k}:\n{rendered}")
            elif isinstance(v, (dict)) and v:
                rendered = _emit_value(v, indent + 1)
                lines.append(f"{pad}{k}:\n{rendered}")
            else:
                rendered = _emit_value(v, indent + 1)
                lines.append(f"{pad}{k}: {rendered}")

        return "\n".join(lines)

    if isinstance(val, list):
        if not val:
            return "[]"

        lines = []

        for item in val:
            rendered = _emit_value(item, indent + 1)

            if isinstance(item, dict) and item:
                # first key on same line as '-'
                items_lines = rendered.strip().split("\n")
                lines.append(f"{pad}- {items_lines[0].strip()}")

                for l in items_lines[1:]:
                    lines.append(f"{pad}  {l.strip()}")
            else:
                lines.append(f"{pad}- {rendered}")

        return "\n".join(lines)

    if isinstance(val, bool):
        return "true" if val else "false"

    if isinstance(val, str):
        # quote if contains special chars or empty
        if not val or any(c in val for c in ':{}[]|>&*!,#?@`\'"'):
            return f"'{val}'"

        return val

    return str(val)


def _emit_mapping(d: dict, indent: int) -> str:
    pad = "  " * indent
    lines = []

    for k, v in d.items():
        if isinstance(v, list) and v:
            # HA style: list items at same indent as key
            rendered = _emit_value(v, indent)
            lines.append(f"{pad}{k}:\n{rendered}")
        elif isinstance(v, dict) and v:
            rendered = _emit_value(v, indent + 1)
            lines.append(f"{pad}{k}:\n{rendered}")
        else:
            rendered = _emit_value(v, indent + 1)
            lines.append(f"{pad}{k}: {rendered}")

    return "\n".join(lines)


def _automation_to_yaml(auto: Automation, indent: int = 0) -> str:
    pad = "  " * indent

    triggers   = []
    conditions = []
    actions    = []
    top_props  = {}

    for rule in auto.rules:
        match rule:
            case WhenRule(event=ev, args=Dict(props=ps)):
                entry = {"trigger": ev}
                entry.update({p.name: _val(p.value) for p in ps})
                triggers.append(entry)

            case IfRule():
                # IfRule wraps a condition node; extract Id + Dict from NegatedCondition->CallNegation
                from tree import CallNegation, NotNegation
                neg = rule.condition

                # unwrap NegatedCondition
                if hasattr(neg, 'negation'): neg = neg.negation

                # unwrap NotNegation chain
                while isinstance(neg, NotNegation):
                    neg = neg.inner

                if isinstance(neg, CallNegation):
                    entry = {"condition": neg.name}
                    entry.update({p.name: _val(p.value) for p in neg.args.props})
                    conditions.append(entry)

            case DoRule(action=act, args=Dict(props=ps)):
                entry = {"action": act}
                entry.update({p.name: _val(p.value) for p in ps})
                actions.append(entry)

            case Property(name=n, value=v) | PropertyRule(name=n, value=v):
                top_props[n] = _val(v)

    lines = []

    def seq(key, items):
        if not items:
            return

        lines.append(f"{pad}{key}:")
        base = "  " * (indent + 1)  # indentation used by _emit_mapping

        for item in items:
            item_lines = _emit_mapping(item, indent + 1).split("\n")
            # strip base indent, re-add pad + list marker or continuation
            lines.append(f"{pad}- {item_lines[0][len(base):]}")

            for l in item_lines[1:]:
                lines.append(f"{pad}  {l[len(base):]}")

    seq("triggers",   triggers)
    seq("conditions", conditions)
    seq("actions",    actions)

    for k, v in top_props.items():
        if isinstance(v, list) and v:
            rendered = _emit_value(v, indent + 1)
            lines.append(f"{pad}{k}:\n{rendered}")
        elif isinstance(v, dict) and v:
            rendered = _emit_value(v, indent + 2)
            lines.append(f"{pad}{k}:\n{rendered}")
        else:
            rendered = _emit_value(v, indent + 1)
            lines.append(f"{pad}{k}: {rendered}")

    return "\n".join(lines)


def generate(file: AutomationFile) -> str:
    blocks = []

    for auto in file.automations:
        name = auto.name.strip('"')
        header = f"- alias: {name}"
        body = _automation_to_yaml(auto, indent=1)
        blocks.append(header + "\n" + body)

    return "\n".join(blocks)


if __name__ == "__main__":
    from tree import parse_source

    src = input('> ')
    # src = 'automation "ass" {'
    tree = parse_source(src)
    print(generate(tree))
