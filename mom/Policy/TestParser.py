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

    def test_whitespace(self):
        pol = """
        (+ 1 
        2)  (- 10 2)
        """
        self.verify(pol, [ 3, 8 ])
        
    def test_string(self):
        pol = """
        "foo" "bar"
        (+ "Hello " "World!")
        (+ (* 3 "Hey ") "!")
        """
        self.verify(pol, [ "foo", "bar", "Hello World!", "Hey Hey Hey !" ])

    def test_basic_math(self):
        pol = """
        10
        (* 0 1)
        (+ 1 2)
        (/ 11 2)
        (* 3 6)
        (- 1 9)
        (* (- 8 6) 9)
        (>> (<< 1 4) 2)
        """
        self.verify(pol, [ 10, 0, 3, 5, 18, -8, 18, 4 ])
        
    def test_compare(self):
        pol = """
        (< 5 4)
        (> 1 0)
        (<= 10 10)
        (>= 2 (/ 10 2))
        (== (+ 1 2) (/ 9 3))
        (!= "foo" "foo")
        """
        self.verify(pol, [ False, True, True, False, True, False ])
        
    def test_vars(self):
        pol = """
        (defvar foo "bar")
        (defvar a 5)
        (defvar b 6)
        (+ a b)
        (set a 8)
        (+ a b)
        (* foo 2)
        """
        self.verify(pol, [ 'bar', 5, 6, 11, 8, 14, "barbar" ])
        
    def test_funcs(self):
        pol = """
        (def foo () 10)
        (def bar (a)
            (* 2 a))
        (/ (foo) (bar 5))
        (def baz (b)
            (- 2 (bar b)))
        (baz 12)
        """
        self.verify(pol, [ 'foo', 'bar', 1, 'baz',  -22])

    def test_let(self):
        pol = """
        (def foo (a) (+ 2 a))
        (let ((a 1) (b 2)) (foo a))
        """
        self.verify(pol, [ 'foo', 3 ])
        
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
        self.verify(pol, [ 1, 0, 'f', 4, 0, "yes" ])

    def test_scope(self):
        pol = """
        (defvar a 10)
        (def foo (b) (set a b))
        (foo 2)
        a
        (def foo (b) (defvar a b))
        (foo 4)
        a
        (set a 5)
        (let ((a 4)) a)
        a
        (if (== a 5) (defvar a 4) 0)
        a
        """
        self.verify(pol, [ 10, 'foo', 2, 2, 'foo', 4, 2, 5, 4, 5, 4, 4 ]) 

if __name__ == '__main__':
    unittest.main()
