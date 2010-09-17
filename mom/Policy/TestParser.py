# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
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

import unittest
import Parser

class TestEval(unittest.TestCase):
    def setUp(self):
        self.e = Parser.Evaluator()

    def verify(self, pol, expected):
        results = Parser.eval(self.e, pol)
        self.assertEqual(results, expected)

    def test_comments(self):
        pol = """
        # This is a full-line pound comment
        12 # A partial-line comment with (+ 23 43) keywords
        (+ 3 # An expression with embedded comments
        2)
        """
        results = Parser.eval(self.e, pol)
        self.assertEqual(results, [ 12, 5 ])

    def test_whitespace(self):
        pol = """
        (+ 1 
        2)  (- 10 2)
        """
        self.verify(pol, [ 3, 8 ])
        
    def test_string(self):
        pol = """
        "foo" "bar"
        
        # Operators on strings have the same effect as for Python
        (+ "Hello " "World!")
        (+ (* 3 "Hey ") "!")
        """
        self.verify(pol, [ "foo", "bar", "Hello World!", "Hey Hey Hey !" ])

    def test_basic_math(self):
        pol = """
        10
        00                  # Octal
        .3                  # The leading 0 on a float is not required
        (* 0 1)
        (+ 1 2)
        (/ 11 2)            # Integer division
        (/ 11 2.0)          # Floating point division
        (* 3 6)
        (- 1 9)             # Negative result
        (* (- 8 6) 9)
        (>> (<< 1 4) 2)
        (+ 0xFF 0x1)        # Hex numbers
        (* 011 02)
        (+ 0xa 10)          # Numeric type mixing
        (+ 10.0e3 100e-2)   # Scientific notation for integers and floats
        """
        self.verify(pol, [ 10, 0, 0.3, 0, 3, 5, 5.5, 18, -8, 18, 4, 256, 18, 20,
                           10001.0 ])
        
    def test_compare(self):
        pol = """
        (< 5 4)
        (> 1 0)
        (<= 10 10)
        (>= 2 (/ 10 2))
        (== (+ 1 2) (/ 9 3))
        (!= "foo" "foo")
        (== 0x0 0)
        """
        self.verify(pol, [ False, True, True, False, True, False, True ])
        
    def test_vars(self):
        pol = """
        (defvar foo "bar")
        (defvar a 5)
        (defvar b 6)
        (+ a b)
        (set a 8)
        (+ a b)
        (* foo 2)
        (defvar e3 7)
        (+ 1 e3)        # Make sure e3 is not mistaken for scientific notation
        """
        self.verify(pol, [ 'bar', 5, 6, 11, 8, 14, "barbar", 7, 8 ])
        
    def test_funcs(self):
        pol = """
        (def foo () 10)
        (def bar (a)
            (* 2 a))
        (/ (foo) (bar 5))
        (def baz (b)
            (- 2 (bar b)))
        (baz 12)
        (def foo (a) {
            (def bar (b) (+ b 1))   # Nested function
            (bar a)
        })
        (foo 9)
        """
        self.verify(pol, [ 'foo', 'bar', 1, 'baz',  -22, 'foo', 10 ])

    def test_let(self):
        pol = """
        (def foo (a) (+ 2 a))
        (defvar a 2)
        (let ((a 1) (b 2)) (foo a))
        a                               # Value of 'a' unaffected by let
        """
        self.verify(pol, [ 'foo', 2, 3, 2 ])
        
    def test_if(self):
        pol = """
        (defvar a 1)
        (defvar b 0)
        (def f (cond)
            (if cond
                "yes"
                "no"))
        (if a 4 3)
        (if b 1 0)
        (f (> 2 1))
        """
        self.verify(pol, [ 1, 0, 'f', 4, 0, "yes"])

    def test_scope(self):
        pol = """
        (defvar a 10)
        (def foo (b) (set a b))         # set affects the global 'a'
        (foo 2)
        a
        (def foo (b) (defvar a b))      # defvar creates a local 'a'
        (foo 4)
        a
        (set a 5)
        (let ((a 4)) a)                 # let creates a local 'a'
        a
        (if (== a 5) (defvar a 4) 0)    # if does not create a new scope
        a
        """
        self.verify(pol, [ 10, 'foo', 2, 2, 'foo', 4, 2, 5, 4, 5, 4, 4 ]) 

    def test_multi_statements(self):
        pol = """
        { 10 4 }                # A multi-statement evaluates to the last value
        (def f (a b) {          # Use them for function bodies
            (defvar c (+ a b))
            (set c (+ 1 c))
            c
        })
        (f 4 5)
        
        (defvar q 11)
        (let ((q 2) (r 3)) {            # Use them for let statements
            q r
            (- r q)
        })
        
        (if (== q 11) {                 # Use them in if statements
            "q maintains proper scope"
            (set q 12)
        } {
            "oops, q has the wrong value"
        })
        (- q 10)
        """
        self.verify(pol, [ 4, 'f', 10, 11, 1, 12, 2 ])

if __name__ == '__main__':
    unittest.main()
