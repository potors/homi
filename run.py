import tree, gen, readline
from lexer import Lexer
from parser import Grammar, GRAMMAR, SLRParser
from tree import parse_source, pretty
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

tree = parse_source(s)
print(pretty(tree))

print(gen.generate(tree))
