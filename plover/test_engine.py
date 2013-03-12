# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for engine.py."""

import engine
import unittest


class Stroke(object):
    def __init__(self, rtfcre, is_correction=False):
        self.rtfcre = rtfcre
        self.is_correction = is_correction
        
    def __eq__(self, other):
        return isinstance(other, Stroke) and self.rtfcre == other.rtfcre
        
    def __ne__(self, other):
        return not not self.__eq__(other)

BACKSPACE = 'b'
STRING = 's'
COMBO = 'c'
COMMAND = 'e'

class Output(object):
    def __init__(self):
        self._output = []
    
    def send_backspaces(self, n):
        self._output.append((BACKSPACE, n))

    def send_string(self, s):
        self._output.append((STRING, s))

    def send_key_combination(self, c):
        self._output.append((COMBO, c))

    def send_engine_command(self, c):
        self._output.append((COMMAND, c))
        
    def get(self):
        return self._output

class TextOutput(object):
    def __init__(self):
        self._output = ''

    def send_backspaces(self, n):
        if n > len(self._output):
            raise Exception('Too many backspaces.')
        if n:
            self._output = self._output[:-n]

    def send_string(self, s):
        self._output += s

    def send_key_combination(self, c):
        raise Exception('Key combos not supported.')

    def send_engine_command(self, c):
        raise Exception('Engine commands not supported.')
        
    def get(self):
        return self._output

class EngineTestCase(unittest.TestCase):
    
    def test_engine_raw(self):
        output = Output()
        e = engine.StenoEngine()
        e.set_output(output)
        e.process_stroke(Stroke('T'))
        self.assertEqual(output.get(), [(STRING, ' T')])
        e.process_stroke(Stroke('T'))
        self.assertEqual(output.get(), [(STRING, ' T'), (STRING, ' T')])
        
    def test_engine_combo(self):
        output = Output()
        e = engine.StenoEngine()
        e.set_output(output)
        e.add_translation(('S',), '{#mycombo}')
        e.process_stroke(Stroke('S'))
        self.assertEqual(output.get(), [(COMBO, 'mycombo')])
        
    def test_engine_command(self):
        output = Output()
        e = engine.StenoEngine()
        e.set_output(output)
        e.add_translation(('S',), '{PLOVER:mycommand}')
        e.process_stroke(Stroke('S'))
        self.assertEqual(output.get(), [(COMMAND, 'mycommand')])
        
    def test_engine_translation(self):
        output = Output()
        e = engine.StenoEngine()
        e.set_output(output)
        e.add_translation(('S',), 'hello')
        e.process_stroke(Stroke('S'))
        self.assertEqual(output.get(), [(STRING, ' hello')])
        
    def test_engine_undo(self):
        output = Output()
        e = engine.StenoEngine()
        e.set_output(output)
        e.add_translation(('S',), 'hello')
        e.process_stroke(Stroke('S'))
        self.assertEqual(output.get(), [(STRING, ' hello')])
        e.process_stroke(Stroke('*', True))
        self.assertEqual(output.get(), [(STRING, ' hello'), (BACKSPACE, 6)])
        
    def test_engine_undo_tail(self):
        output = TextOutput()
        e = engine.StenoEngine()
        # TODO: This is hacky.
        e._translator.set_undo_length(1)
        e.set_output(output)
        e.add_translation(('S',), 'make')
        e.add_translation(('T',), '{^ing}')
        e.process_stroke(Stroke('S'))
        self.assertEqual(output.get(), ' make')
        e.process_stroke(Stroke('T'))
        self.assertEqual(output.get(), ' making')
        e.process_stroke(Stroke('*', True))
        self.assertEqual(output.get(), ' make')
        e.process_stroke(Stroke('*', True))
        self.assertEqual(output.get(), ' make')  # No more undo buffer.
        e.process_stroke(Stroke('T'))
        self.assertEqual(output.get(), ' making')  # But tail keeps state.

if __name__ == '__main__':
    unittest.main()