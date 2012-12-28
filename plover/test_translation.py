# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for translation.py."""

import translation
import unittest

class Stroke(object):
    def __init__(self, rtfcre, is_correction=False):
        self.rtfcre = rtfcre
        self.is_correction = is_correction
        
    def __eq__(self, other):
        return isinstance(other, Stroke) and self.rtfcre == other.rtfcre
        
    def __ne__(self, other):
        return not not self.__eq__(other)

def make_trans(d):
    def trans(*args):
        return translation.Translation([Stroke(s) for s in args], d)
    return trans

class TranslatorTestCase(unittest.TestCase):

    def test_translation(self):
        d = translation._Dictionary()
        trans = make_trans(d)
        t = trans('S', 'T')
        self.assertEqual(t.strokes, [Stroke('S'), Stroke('T')])
        self.assertEqual(t.rtfcre, ('S', 'T'))
        
        d[('S', 'T')] = 'text'
        t = trans('S', 'T')
        self.assertEqual(t.strokes, [Stroke('S'), Stroke('T')])
        self.assertEqual(t.rtfcre, ('S', 'T'))
        self.assertEqual(t.english, 'text')

    def test_translator(self):
        # TODO: break up into smaller tests that test one thing?
        
        class Output(object):
            def __init__(self):
                self._output = []
                
            def write(self, undo, do, prev):
                for t in undo:
                    self._output.pop()
                for t in do:
                    if t.english:
                        self._output.append(t.english)
                    else:
                        self._output.append('/'.join(t.rtfcre))
                        
            def get(self):
                return ' '.join(self._output)
                
            def clear(self):
                del self._output[:]
                
        out = Output()        
        t = translation.Translator()
        t.add_listener(out.write)
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 'S')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 'S T')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 'S')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 'S')  # Undo buffer ran out.
        
        t.set_undo_length(3)
        out.clear()
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 'S')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 'S T')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 'S')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), '')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), '')  # Undo buffer ran out.
        
        out.clear()
        t.add_translation(('S',), 't1')
        d = {}
        d[('T',)] = 't2'
        d[('S', 'T')] = 't3'
        t.add_translations(d)
        
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 't1')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 't3')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 't3 t2')
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 't3 t2 t1')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't3 t2')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't3')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't1')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), '')
        
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 't1')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 't3')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 't3 t2')
        
        t.add_translation(('S', 'T', 'T'), 't4')
        t.add_translation(('S', 'T', 'T', 'S'), 't5')
        
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 't5')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't3 t2')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't3')
        t.translate(Stroke('T'))
        self.assertEqual(out.get(), 't4')
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 't5')
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), 't5 t1')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't5')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't4')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't3')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 't1')
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), '')
        
        t.remove_translations(t._dictionary.keys())
        t.translate(Stroke('S'))
        t.translate(Stroke('S'))
        t.translate(Stroke('S'))
        t.translate(Stroke('S'))
        t.translate(Stroke('*', True))
        t.translate(Stroke('*', True))
        t.translate(Stroke('*', True))
        t.translate(Stroke('*', True))
        self.assertEqual(out.get(), 'S')  # Not enough undo to clear output.
        
        out.clear()
        t.remove_listener(out.write)
        t.translate(Stroke('S'))
        self.assertEqual(out.get(), '')

    def test_dictionary(self):
        d = translation._Dictionary()
        self.assertEqual(d.longest_key, 0)
        d[('S',)] = 'a'
        self.assertEqual(d.longest_key, 1)
        d[('S', 'S', 'S', 'S')] = 'b'
        self.assertEqual(d.longest_key, 4)
        d[('S', 'S')] = 'c'
        self.assertEqual(d.longest_key, 4)
        self.assertEqual(d[('S', 'S')], 'c')
        del d[('S', 'S', 'S', 'S')]
        self.assertEqual(d.longest_key, 2)
        del d[('S',)]
        self.assertEqual(d.longest_key, 2)
        d.clear()
        self.assertEqual(d.longest_key, 0)

    def test_translate_stroke(self):    

        class CaptureOutput(object):
            def __init__(self):
                self.output = []

            def callback(self, new, prev):
                self.output.append((new, prev))
                
        
        class CaptureOutput2(object):
            def __init__(self):
                self.output = []

            def callback(self, undo, new, prev):
                self.output.append((undo, new, prev))
                
        d = translation._Dictionary()
        trans = make_trans(d)
        
        state = translation._State()
        s = Stroke('S')
        output = CaptureOutput2()
        translation._translate_stroke(s, state, d, output.callback)
        self.assertEqual(state.translations, [trans('S')])
        self.assertEqual(output.output, [([], [trans('S')], None)])
        
        del output.output[:]
        t = trans('S')
        state.translations = [t]
        translation._translate_stroke(s, state, d, output.callback)
        self.assertEqual(state.translations, [t] * 2)
        self.assertEqual(output.output, [([], [t], t)])
        
        del output.output[:]
        d[('S', 'T', 'T')] = 'nothing'
        t = trans('S', 'T')
        state.translations = [t]
        translation._translate_stroke(s, state, d, output.callback)
        self.assertEqual(state.translations, [t, trans('S')])
        self.assertEqual(output.output, [([], [trans('S')], t)])

        del output.output[:]
        state.translations = [t]
        s = Stroke('T')
        t2 = trans('S', 'T', 'T')
        translation._translate_stroke(s, state, d, output.callback)
        self.assertEqual(state.translations, [t2])
        self.assertEqual(state.translations[0].replaced, [t])
        self.assertEqual(output.output, [([t], [t2], None)])
        self.assertEqual(output.output[0][1][0].english, 'nothing')
        
        del output.output[:]
        correction = Stroke('*', True)
        translation._translate_stroke(correction, state, d, output.callback)
        self.assertEqual(state.translations, [t])
        self.assertEqual(output.output, [([t2], [t], None)])
        
        del output.output[:]
        tail = trans('T', 'A', 'I', 'L')
        state = translation._State()
        state.tail = tail
        translation._translate_stroke(Stroke('S'), state, d, output.callback)
        self.assertEqual(output.output[0][2], tail)

if __name__ == '__main__':
    unittest.main()

