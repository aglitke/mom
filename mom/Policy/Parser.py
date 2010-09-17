# Memory Overcommitment Manager
# Copyright (C) 2010 Anthony Liguori and Adam Litke, IBM Corporation
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

from spark import GenericScanner, GenericParser

class Token(object):
    def __init__(self, kind, value=None):
        self.kind = kind
        if value == None:
            self.value = kind
        else:
            self.value = value

    def __cmp__(self, rhs):
        return cmp(self.kind, rhs)

    def __repr__(self):
        return '[%s %s]' % (self.kind, self.value)
        
class NumericToken(Token):
    def __init__(self, type, value):
        self.type = type
        Token.__init__(self, 'number', value)

class Scanner(GenericScanner):
    def __init__(self, operators=''):
        self.operators = operators
        GenericScanner.__init__(self)

    def get_re(self, name):
        if name == 'user_op':
            def escape(op):
                nop = ''
                for ch in op:
                    if ch in '+*.':
                        nop += '\\'
                    nop += ch
                return nop
            return ' %s ' % '|'.join(map(escape, self.operators))
        else:
            raise AttributeError(name)

    def tokenize(self, input):
        self.rv = []
        GenericScanner.tokenize(self, input)
        return self.rv
    
    def t_whitespace(self, s):
        r' \s+ '
        pass

    def t_symbol(self, s):
        r' [A-Za-z_][A-Za-z0-9_\-\.]* '
        self.rv.append(Token('symbol', s))

    def t_string(self, s):
        r' "([^"\\]|\\.)*" '
        self.rv.append(Token('string', s))

    def t_single_quote_string(self, s):
        r" '([^'\\]|\\.)*' "
        self.rv.append(Token('string', s))

    def t_float(self, s):
        r' -?(0|([1-9][0-9]*))*(\.[0-9]+)([Ee][+-]?[0-9]+)? '
        self.rv.append(NumericToken('float', s)) 

    def t_integer(self, s):
        r' -?(0(?![0-9Xx])|[1-9][0-9]*)(?![0-9eE]) '
        self.rv.append(NumericToken('integer', s))
        
    def t_integer_with_exponent(self, s):
        r' -?(0(?![0-9Xx])|[1-9][0-9]*)[Ee][+-]?[0-9]+ '
        # Python only recognizes scientific notation on float types
        self.rv.append(NumericToken('float', s))

    def t_hex(self, s):
        r' 0[Xx][0-9A-Fa-f]+ '
        self.rv.append(NumericToken('hex', s))

    def t_octal(self, s):
        r' 0[0-9]+ '
        self.rv.append(NumericToken('octal', s))

    def t_builtin_op(self, s):
        r' [\(\){}\[\]] '
        self.rv.append(Token(s))

    def t_user_op(self, s):
        self.rv.append(Token('operator', s))

class Parser(GenericParser):
    def __init__(self, start='value'):
        GenericParser.__init__(self, start)

    def mklist(self, args):
        if len(args) == 2:
            return []
        return args[1]

    def p_value_list(self, args):
        '''
          value_list ::= value
          value_list ::= value_list value
        '''
        if len(args) == 1:
            return [args[0]]
        return args[0] + [args[1]]

    def p_list(self, args):
        '''
          list ::= ( )
          list ::= ( value_list )
        '''
        return self.mklist(args)

    def p_bracket_list(self, args):
        '''
          bracket_list ::= [ ]
          bracket_list ::= [ value_list ]
        '''
        return self.mklist(args)

    def p_curly_list(self, args):
        '''
          curly_list ::= { }
          curly_list ::= { value_list }
        '''
        return self.mklist(args)

    def p_value(self, args):
        '''
          value ::= operator
          value ::= number
          value ::= operator
          value ::= symbol
          value ::= string
          value ::= single_quote_string
          value ::= list
          value ::= curly_list
          value ::= bracket_list
         '''
        return args[0]

class GenericEvaluator(object):
    operator_map = {}

    def __init__(self):
        pass

    def get_operators(self):
        return self.operator_map.keys()

    def parse_doc(self, doc):
        scanner = Scanner(['...'])
        tokens = scanner.tokenize(doc)
        parser = Parser(start='value_list')
        return parser.parse(tokens)

    # TODO: split up doc parsing...
    # use elipse syntax to indicate repetition in a
    # list.  IOW:
    # (number ...)
    # is a list of zero or more numbers
    # ((symbol value) ...)
    # is a list of zero or more tuples of symbol value
    # (symbol number ...)
    # is a list containing a symbol and zero or more numbers
    def _dispatch(self, fn, args):
        doc = fn.__doc__
        if doc == None:
            args = map(self.eval, args)
        else:
            types = self.parse_doc(doc)
            if len(types) != len(args):
                raise Exception('arity mismatch in doc parsing')
            for i in range(len(types)):
                if types[i].value == 'code':
                    continue
                elif types[i].value == 'symbol':
                    if not isinstance(args[i], Token) or args[i].kind != 'symbol':
                        raise Exception('malformed expression')
                    args[i] = args[i].value
                else:
                    args[i] = self.eval(args[i])
        return fn(*args)

    def eval(self, code):
        if isinstance(code, Token):
            if code.kind == 'number':
                return self.eval_number(code)
            elif code.kind == 'string':
                return code.value[1:-1]
            elif code.kind == 'symbol':
                return self.eval_symbol(code.value)
            else:
                raise Exception('Unexpected token type "%s"' % code.kind)

        node = code[0]
        if not isinstance(node, Token):
            print code
            raise Exception('Expected simple token as arg 1')

        if node.kind == 'symbol':
            name = node.value
        elif node.kind == 'operator':
            name = self.operator_map[node.value]
        else:
            raise Exception('Unexpected token type in arg 1 "%s"' % node.kind)

        if hasattr(self, 'c_%s' % name):
            return self._dispatch(getattr(self, 'c_%s' % name), code[1:])
        elif hasattr(self, "default"):
            return self.default(name, code[1:])
        else:
            raise Exception('Unknown function "%s" with no default handler' % name)

class VariableStack(object):
    def __init__(self):
        self.stack = []

    def enter_scope(self):
        self.stack = [{}] + self.stack

    def leave_scope(self):
        self.stack = self.stack[1:]

    def get(self, name):
        for scope in self.stack:
            if scope.has_key(name):
                return scope[name]
        raise Exception("undefined symbol %s" % name)

    def set(self, name, value, alloc=False):
        if alloc:
            self.stack[0][name] = value
            return value

        for scope in self.stack:
            if scope.has_key(name):
                scope[name] = value
                return value

        raise Exception("undefined symbol %s" % name)

class Evaluator(GenericEvaluator):
    operator_map = {'+': 'add', '-': 'sub',
                    '*': 'mul', '/': 'div',
                    '<': 'lt', '>': 'gt',
                    '<=': 'lte', '>=': 'gte',
                    '<<': 'shl', '>>': 'shr',
                    '==': 'eq', '!=': 'neq'}

    def __init__(self):
        GenericEvaluator.__init__(self)
        self.stack = VariableStack()
        self.funcs = {}
        self.stack.enter_scope()

    def eval_symbol(self, name):
        return self.stack.get(name)
        
    def eval_number(self, token):
        if token.type == 'float':
            return float(token.value)
        elif token.type in ('integer', 'hex', 'octal'):
            return int(token.value, 0)
        else:
            raise Exception("Unsupported numeric type for token: %s" % token)

    def default(self, name, args):
        if name == 'eval':
            return map(self.eval, args)

        params, code = self.funcs[name]
        if len(params) != len(args):
            raise Exception('Function "%s" invoked with incorrect arity' % name)

        scope = []
        for i in range(len(params)):
            scope.append([params[i], args[i]])

        return self.eval([Token('symbol', 'let'), scope, code])

    def c_def(self, name, params, code):
        'symbol code code'
        self.funcs[name] = (params, code)
        return name

    def c_set(self, name, value):
        'symbol value'
        return self.stack.set(name, value)

    def c_defvar(self, name, value):
        'symbol value'
        return self.stack.set(name, value, True)

    def c_let(self, syms, code):
        'code code'
        if type(syms) != list:
            raise Exception('Expecting list as arg 1 in let')

        self.stack.enter_scope()
        for sym in syms:
            if type(sym) != list or len(sym) != 2:
                raise Exception('Expecting list of tuples in arg1 of let')
            name, value = sym
            if name.kind != 'symbol':
                raise Exception('Expecting list of (symbol value) in let')
            self.stack.set(name.value, self.eval(value), True)
        result = self.eval(code)
        self.stack.leave_scope()
        return result

    def c_if(self, cond, yes, no):
        'value code code'

        if cond:
            return self.eval(yes)
        else:
            return self.eval(no)

    def c_add(self, x, y):
        return x + y

    def c_sub(self, x, y):
        return x - y

    def c_mul(self, x, y):
        return x * y

    def c_div(self, x, y):
        return x / y

    def c_lt(self, x, y):
        return x < y

    def c_gt(self, x, y):
        return x > y

    def c_lte(self, x, y):
        return x <= y

    def c_gte(self, x, y):
        return x >= y

    def c_eq(self, x, y):
        return x == y

    def c_neq(self, x, y):
        return x != y

    def c_shl(self, x, y):
        return x << y

    def c_shr(self, x, y):
        return x >> y

def eval(e, string):
    scanner = Scanner(e.get_operators())
    tokens = scanner.tokenize(string)
    parser = Parser(start='value_list')
    code = parser.parse(tokens)
    results = []
    for expr in code:
        results.append(e.eval(expr))
    return results

def repl(e):
    while True:
        print '>>>',
        try:
            string = raw_input()
        except EOFError:
            break

        print eval(e, string)[0]

if __name__ == '__main__':
    import sys

    e = Evaluator()

    if len(sys.argv) > 1:
        f = open(sys.argv[1], 'r')
        try:
            lines = f.read()
        finally:
            f.close()
        results = eval(e, lines)
        for result in results:
            print result
    else:
        repl(e)

