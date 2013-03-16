# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for formatting.py."""

import formatting
import unittest

def action(**kwargs):
    return formatting._Action(**kwargs)

class CaptureOutput(object):
    def __init__(self):
        self.instructions = []
    
    def send_backspaces(self, n):
        self.instructions.append(('b', n))
        
    def send_string(self, s):
        self.instructions.append(('s', s))
        
    def send_key_combination(self, c):
        self.instructions.append(('c', c))
        
    def send_engine_command(self, c):
        self.instructions.append(('e', c))

class MockTranslation(object):
    def __init__(self, rtfcre='', english=None, is_correction=False, formatting=None):
        self.rtfcre = rtfcre
        self.english = english
        self.is_correction = is_correction
        self.formatting = formatting
        
    def __str__(self):
        return str(self.__dict__)
        
def translation(**kwargs):
    return MockTranslation(**kwargs)

class FormatterTestCase(unittest.TestCase):

    def check(self, f, cases):
        for input, output in cases:
            self.assertEqual(f(input), output)
            
    def check_arglist(self, f, cases):
        for inputs, expected in cases:
            actual = f(*inputs)
            if actual != expected:
                print actual, '!=', expected
            self.assertEqual(actual, expected)

    def test_formatter(self):
        output = CaptureOutput()
        formatter = formatting.Formatter()
        formatter.set_output(output)
        t = translation(formatting=[action(text='hello')])
        formatter.format([t], [], None)
        self.assertEqual(output.instructions, [('b', 5)])
        
        del output.instructions[:]
        t = translation(rtfcre=('S'), english='hello')
        p = translation(rtfcre=('T'), english='a', 
                        formatting=[action(text='f')])
        formatter.format([], [t], p)
        self.assertEqual(output.instructions, [('s', ' hello')])
        self.assertEqual(t.formatting, [action(text=' hello', word='hello')])
        
        del output.instructions[:]
        t = translation(rtfcre=('S'), english='hello')
        formatter.format([], [t], None)
        self.assertEqual(output.instructions, [('s', ' hello')])
        self.assertEqual(t.formatting, [action(text=' hello', word='hello')])
        
        del output.instructions[:]
        t = translation(rtfcre=('ST-T',))
        formatter.format([], [t], None)
        self.assertEqual(output.instructions, [('s', ' ST-T')])
        self.assertEqual(t.formatting, [action(text=' ST-T')])
        
        del output.instructions[:]
        t = translation(rtfcre=('ST-T',))
        formatter.format([], [t], translation(formatting=[action(text='hi')]))
        self.assertEqual(output.instructions, [('s', ' ST-T')])
        self.assertEqual(t.formatting, [action(text=' ST-T')])
        
        del output.instructions[:]
        t = translation(english='rest')
        formatter.format([translation(formatting=[action(text='test', 
                                                         word='test')])],
                         [t],
                         translation(formatting=[action(capitalize=True)]))
        self.assertEqual(t.formatting, [action(text=' Rest', word='Rest')])
        self.assertEqual(output.instructions, [('b', 4), ('s', ' Rest')])
        
        del output.instructions[:]
        t = translation(english='rest')
        formatter.format(
            [translation(formatting=[action(text='test', word='test'),
                                     action(text='testing', word='testing', replace='test')])],
            [t],
            translation(formatting=[action(capitalize=True)]))
        self.assertEqual(
            t.formatting, [action(text=' Rest', word='Rest')])
        self.assertEqual(output.instructions, [('b', 7), ('s', 'test'), ('b', 4), ('s', ' Rest')])
        # TODO: break up tests into smaller tests
        # TODO: add tests for raw strokes

    def test_format_raw(self):
        output = CaptureOutput()
        actions = formatting._format_raw('1', None, output)
        self.assertEqual(actions, 
                         [action(text=' 1', word='1', glue=True)])
        self.assertEqual(output.instructions, [('s', ' 1')])
        
        output = CaptureOutput()
        actions = formatting._format_raw(
            '1', [action(text='hi', word='hi')], output)
        self.assertEqual(
            actions, [action(text=' 1', word='1', glue=True)])
        self.assertEqual(output.instructions, [('s', ' 1')])
        
        output = CaptureOutput()
        actions = formatting._format_raw(
            '1', [action(text='hi', word='hi', glue=True)], output)
        self.assertEqual(actions, 
                         [action(text='1', word='hi1', glue=True)])
        self.assertEqual(output.instructions, [('s', '1')])
        
        output = CaptureOutput()
        actions = formatting._format_raw(
            '1-9', [action(text='hi', word='hi', glue=True)], output)
        self.assertEqual(actions, 
                         [action(text='19', word='hi19', glue=True)])
        self.assertEqual(output.instructions, [('s', '19')])
        
        output = CaptureOutput()
        actions = formatting._format_raw(
            'ST-PL', [action(text='hi', word='hi')], output)
        self.assertEqual(actions, [action(text=' ST-PL')])
        self.assertEqual(output.instructions, [('s', ' ST-PL')])
        
        output = CaptureOutput()
        actions = formatting._format_raw(
            'ST-PL', None, output)
        self.assertEqual(actions, [action(text='ST-PL')])
        self.assertEqual(output.instructions, [('s', 'ST-PL')])

    def test_format_translation(self):
        output = CaptureOutput()
        actions = formatting._format_translation('  hello', None, output)
        self.assertEqual(actions, 
                         [action(text=' hello', word='hello')])
        self.assertEqual(output.instructions, [('s', ' hello')])
        
        output = CaptureOutput()
        actions = formatting._format_translation(
            '  hello', [action(text='b', word='b')], output)
        self.assertEqual(actions, 
                         [action(text=' hello', word='hello')])
        self.assertEqual(output.instructions, [('s', ' hello')])

    def test_undo(self):
        cases = [
        ([action(text='hello')], [('b', 5)]),
        ([action(text='ladies', replace='lady')], [('b', 6), ('s', 'lady')]),
        ]
        for input, expected in cases:
            output = CaptureOutput()
            formatting._undo(input, output)
            self.assertEqual(output.instructions, expected)

    def test_get_last_action(self):
        self.assertEqual(formatting._get_last_action(None), action())
        self.assertEqual(formatting._get_last_action([]), action())
        actions = [action(text='hello'), action(text='world')]
        self.assertEqual(formatting._get_last_action(actions), actions[-1])

    def test_render_actions(self):
        cases = [
        ([action(text='test')], [('s', 'test')]),
        ([action(combo='test')], [('c', 'test')]),
        ([action(command='test')], [('e', 'test')]),
        ([action(replace='test')], [('b', 4)]),
        ([action(replace='lady', text='ladies')], 
         [('b', 4), ('s', 'ladies')]),
        ]
        for input, expected in cases:
            output = CaptureOutput()
            formatting._render_actions(input, output)
            self.assertEqual(output.instructions, expected)

    def test_action(self):
        self.assertNotEqual(action(word='test'), 
                            action(word='test', attach=True))
        self.assertEqual(action(text='test'), action(text='test'))
        self.assertEqual(action(text='test', word='test').copy_state(),
                         action(word='test'))
    
    def test_translation_to_actions(self):
        cases = [
        (('test', action()), 
         [action(text=' test', word='test')]),
        
        (('{^^}', action()), [action(attach=True)]),
         
        (('1-9', action()), 
         [action(word='1-9', text=' 1-9')]),
         
        (('32', action()), 
         [action(word='32', text=' 32', glue=True)]),
         
        (('', action(text=' test', word='test', attach=True)),
         [action(word='test', attach=True)]),
         
        (('  ', action(text=' test', word='test', attach=True)),
         [action(word='test', attach=True)]),
         
        (('{^} {.} hello {.} {#ALT_L(Grave)}{^ ^}', action()),
         [action(attach=True), 
          action(text='.', capitalize=True), 
          action(text=' Hello', word='Hello'), 
          action(text='.', capitalize=True), 
          action(combo='ALT_L(Grave)', capitalize=True),
          action(text=' ', attach=True)
         ]),
         
         (('{-|} equip {^s}', action()),
          [action(capitalize=True),
           action(text=' Equip', word='Equip'),
           action(text='s', word='Equips'),
          ]),

        (('{-|} equip {^ed}', action()),
         [action(capitalize=True),
          action(text=' Equip', word='Equip'),
          action(text='ped', word='Equipped'),
         ]),
        ]
        self.check_arglist(formatting._translation_to_actions, cases)
    
    def test_atom_to_action(self):
        cases = [
        (('{^ed}', action(word='test')), 
         action(text='ed', replace='', word='tested')),
         
        (('{^ed}', action(word='carry')), 
         action(text='ied', replace='y', word='carried')),
          
        (('{^er}', action(word='test')), 
         action(text='er', replace='', word='tester')),
         
        (('{^er}', action(word='carry')), 
         action(text='ier', replace='y', word='carrier')),
                 
        (('{^ing}', action(word='test')), 
         action(text='ing', replace='', word='testing')),

        (('{^ing}', action(word='begin')), 
         action(text='ning', replace='', word='beginning')),
        
        (('{^ing}', action(word='parade')), 
         action(text='ing', replace='e', word='parading')),
                 
        (('{^s}', action(word='test')), 
         action(text='s', replace='', word='tests')),
                 
        (('{,}', action(word='test')), action(text=',')),
         
        (('{:}', action(word='test')), action(text=':')),
         
        (('{;}', action(word='test')), action(text=';')),
         
        (('{.}', action(word='test')), 
         action(text='.', capitalize=True)),
         
        (('{?}', action(word='test')),
         action(text='?', capitalize=True)),

        (('{!}', action(word='test')),
         action(text='!', capitalize=True)),

        (('{-|}', action(word='test')),
         action(capitalize=True, word='test')),
          
        (('{PLOVER:test_command}', action(word='test')),
         action(word='test', command='test_command')),
          
        (('{&glue_text}', action(word='test')),
         action(text=' glue_text', word='glue_text', glue=True)),

        (('{&glue_text}', action(word='test', glue=True)),
         action(text='glue_text', word='testglue_text', glue=True)),
           
        (('{&glue_text}', action(word='test', attach=True)),
         action(text='glue_text', word='testglue_text', glue=True)),
           
        (('{^attach_text}', action(word='test')),
         action(text='attach_text', word='testattach_text')),
          
        (('{^attach_text^}', action(word='test')),
         action(text='attach_text', word='testattach_text', attach=True)),
          
        (('{attach_text^}', action(word='test')),
         action(text=' attach_text', word='attach_text', attach=True)),
                
        (('{#ALT_L(A)}', action(word='test')), 
         action(combo='ALT_L(A)', word='test')),
         
        (('text', action(word='test')), 
         action(text=' text', word='text')),

        (('text', action(word='test', glue=True)), 
         action(text=' text', word='text')),
         
        (('text', action(word='test', attach=True)), 
         action(text='text', word='text')),
         
        (('text', action(word='test', capitalize=True)), 
         action(text=' Text', word='Text')),

        (('some text', action(word='test')), 
         action(text=' some text', word='text')),

        ]
        self.check_arglist(formatting._atom_to_action, cases)
    
    def test_get_meta(self):
        cases = [('', None), ('{abc}', 'abc'), ('abc', None)]
        self.check(formatting._get_meta, cases)
    
    def test_apply_glue(self):
        cases = [('abc', '{&abc}'), ('1', '{&1}')]
        self.check(formatting._apply_glue, cases)
    
    def test_unescape_atom(self):
        cases = [('', ''), ('abc', 'abc'), (r'\{', '{'), (r'\}', '}'), 
                 (r'\{abc\}}{', '{abc}}{')]
        self.check(formatting._unescape_atom, cases)
    
    def test_get_engine_command(self):
        cases = [('', None), ('{PLOVER:command}', 'command')]
        self.check(formatting._get_engine_command, cases)
    
    def test_capitalize(self):
        cases = [('', ''), ('abc', 'Abc'), ('ABC', 'ABC')]
        self.check(formatting._capitalize, cases)
    
    def test_rightmost_word(self):
        cases = [('', ''), ('abc', 'abc'), ('a word', 'word'), 
                 ('word.', 'word.')]
        self.check(formatting._rightmost_word, cases)

if __name__ == '__main__':
    unittest.main()
