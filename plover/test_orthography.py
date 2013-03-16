# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for orthography.py."""

import orthography
import unittest

class OrthographyTestCase(unittest.TestCase):

    def check(self, f, cases):
        for input, output in cases:
            self.assertEquals(f(input), output)

    def test_add_s_suffix(self):
        cases = [('', 's'), ('em', 'ems'), ('person', 'persons'), 
                 ('lady', 'ladies'), ('cherry', 'cherries'), 
                 ('dress', 'dresses')]
        self.check(orthography.add_s_suffix, cases)

    def test_add_ed_suffix(self):
        cases = [('', 'ed'), ('carry', 'carried'), ('blame', 'blamed'), 
                 ('ban', 'banned'), ('sully', 'sullied'), ('equip', 'equipped')]
        self.check(orthography.add_ed_suffix, cases)

    def test_add_er_suffix(self):
        cases = [('', 'er'), ('carry', 'carrier'), ('tame', 'tamer'), 
                 ('run', 'runner'), ('sully', 'sullier')]
        self.check(orthography.add_er_suffix, cases)

    def test_add_ing_suffix(self):
        cases = [('', 'ing'), ('begin', 'beginning'), ('test', 'testing'), 
                 ('worry', 'worrying'), ('blame', 'blaming')]
        self.check(orthography.add_ing_suffix, cases)
        
    def test_add_est_suffix(self):
        cases = [('', 'est'), ('large', 'largest'), ('big', 'biggest')]
        self.check(orthography.add_est_suffix, cases)

if __name__ == '__main__':
    unittest.main()