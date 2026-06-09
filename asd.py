import sys

from lexer import Lexer
from parser import Grammar, SLRParser

# s = input("> ") or 'automation Id {\nwhen something # goes bad\n {\nbecames true\n}\n}'
# s = 'automation { hi there }'
s = sys.stdin.read()

lexer = Lexer({ sym for sym in 'automation { } when if do ( ) and or not true false [ ] + - * / % **'.split(' ') })
tokens = lexer.tokenize(s)

print('tokens:')
for token in tokens:
    print(token)

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
