# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for orthography.py."""

import orthography
import unittest

class OrthographyTestCase(unittest.TestCase):

    def check(self, f, cases):
        for input, output in cases:
            self.assertEquals(f(input), output)

    def test_pluralize_with_s(self):
        cases = [('', 's'), ('em', 'ems'), ('person', 'persons'), 
                 ('lady', 'ladies'), ('cherry', 'cherries'), 
                 ('dress', 'dresses')]
        self.check(orthography.pluralize_with_s, cases)

    def test_add_ed_suffix(self):
        cases = [('', 'ed'), ('carry', 'carried'), ('blame', 'blamed'), 
                 ('ban', 'banned'), ('sully', 'sullied')]
        self.check(orthography.add_ed_suffix, cases)

    def test_add_er_suffix(self):
        cases = [('', 'er'), ('carry', 'carrier'), ('tame', 'tamer'), 
                 ('run', 'runner'), ('sully', 'sullier')]
        self.check(orthography.add_er_suffix, cases)

    def test_add_ing_suffix(self):
        cases = [('', 'ing'), ('begin', 'beginning'), ('test', 'testing'), 
                 ('worry', 'worrying'), ('blame', 'blaming')]
        self.check(orthography.add_ing_suffix, cases)

if __name__ == '__main__':
    unittest.main()