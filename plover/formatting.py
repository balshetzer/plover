# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""This module converts translations to printable text."""

# TODO: Change dictionary so all actions are only in {} and the text is
# outside. This applies to & and ^. Maybe introduce { } for introducing
# whitespace.

# TODO: Make empty glue illegal. also empty attach. Unit test what happens now.

# TODO: create various formatters:
# - plover commands only for turning on while off (or just disconnect text output, like now)
# - raw strokes only for stroke side of create new dict entry UI
# - raw translations for translation side of new dict entry UI

# TODO: Initialize plover with Attach and capitalize.

import re
import orthography
from os.path import commonprefix

class Formatter(object):
    def __init__(self):
        self._output = NullOutput()
    
    def set_output(self, output):
        self._output = output
        
    def format(self, undo, do, prev):
        def last(pt):
            return _get_last_action(pt.formatting if pt else None)
        last_action = last(prev)
        for t in do:
            if t.english:
                t.formatting = _translation_to_actions(t.english, last_action)
            else:
                t.formatting = _raw_to_actions(t.rtfcre[0], last_action)
            last_action = last(t)
        old = [a for t in undo for a in t.formatting]
        new = [a for t in do for a in t.formatting]
        
        min_length = min(len(old), len(new))
        for i in xrange(min_length):
            if old[i] != new[i]:
                break
        else:
            i = min_length

        _undo(old[i:], self._output)
        _render_actions(new[i:], self._output)

class NullOutput(object):
    """An output class that does nothing."""
    def send_backspaces(self, n):
        pass
        
    def send_string(self, s):
        pass
        
    def send_key_combination(self, c):
        pass
        
    def send_engine_command(self, c):
        pass

# TODO: This is no longer used. Move tests to formatter.format and delete
def _format_raw(stroke, last_actions, output):
    last_action = _get_last_action(last_actions)
    # If a raw stroke is composed of digits then remove the dash (if 
    # present) and glue it to any neighboring digits. Otherwise, just 
    # output the raw stroke as is.
    no_dash = stroke.replace('-', '', 1)
    if no_dash.isdigit():
        actions = _translation_to_actions(no_dash, last_action)
    else:
        space = SPACE if last_actions else NO_SPACE
        actions = [_Action(text=(space + stroke))]
    _render_actions(actions, output)
    return actions

# TODO: This is not used. delete and move tests.
def _format_translation(translation, last_actions, output):
    last_action = _get_last_action(last_actions)
    actions = _translation_to_actions(translation, last_action)
    _render_actions(actions, output)
    return actions

def _undo(actions, output):
    for a in reversed(actions):
        if a.text:
            output.send_backspaces(len(a.text))
        if a.replace:
            output.send_string(a.replace)

def _get_last_action(last_actions):
    if last_actions:
        return last_actions[-1]
    else:
        return _Action()

def _render_actions(actions, output):
    for a in actions:
        if a.replace:
            output.send_backspaces(len(a.replace))
        if a.text:
            output.send_string(a.text)
        if a.combo:
            output.send_key_combination(a.combo)
        if a.command:
            output.send_engine_command(a.command)

class _Action(object):
    def __init__(self, attach=False, glue=False, word='', capitalize=False,
                text='', replace='', combo='', command=''):
        # State variables
        self.attach = attach
        self.glue = glue
        self.word = word
        self.capitalize = capitalize
                
        # Instruction variables
        self.text = text
        self.replace = replace
        self.combo = combo
        self.command = command
        
    def copy_state(self):
        a = _Action()
        a.attach = self.attach
        a.glue = self.glue
        a.word = self.word
        a.capitalize = self.capitalize
        return a
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
        
    def __str__(self):
        pairs = []
        for k, v in self.__dict__.items():
            pairs.append('%s=%s' % (k, str(v)))
        return ', '.join(pairs)
        
    def __repr__(self):
        return str(self)


META_ESCAPE = '\\'
RE_META_ESCAPE = '\\\\'
META_START = '{'
META_END = '}'
META_ESC_START = META_ESCAPE + META_START
META_ESC_END = META_ESCAPE + META_END

META_RE = re.compile(r"""(?:%s%s|%s%s|[^%s%s])+ # One or more of anything
                                                # other than unescaped { or }
                                                #
                                              | # or
                                                #
                     %s(?:%s%s|%s%s|[^%s%s])*%s # Anything of the form {X}
                                                # where X doesn't contain
                                                # unescaped { or }
                      """ % (RE_META_ESCAPE, META_START, RE_META_ESCAPE,
                             META_END, META_START, META_END,
                             META_START,
                             RE_META_ESCAPE, META_START, RE_META_ESCAPE,
                             META_END, META_START, META_END,
                             META_END),
                     re.VERBOSE)

# A more human-readable version of the above RE is:
#
# re.compile(r"""(?:\\{|\\}|[^{}])+ # One or more of anything other than
#                                   # unescaped { or }
#                                   #
#                                 | # or
#                                   #
#              {(?:\\{|\\}|[^{}])*} # Anything of the form {X} where X
#                                   # doesn't contain unescaped { or }
#             """, re.VERBOSE)

def _translation_to_actions(translation, last_action):
    actions = []
    # Reduce the translation to atoms. An atom is an
    # irreducible string that is either entirely a single meta
    # command or entirely text containing no meta commands.
    if translation.isdigit():
        # If a translation is only digits then glue it to neighboring digits.
        atoms = [_apply_glue(translation)]
    else:
        atoms = [x.strip() for x in META_RE.findall(translation) if x.strip()]

    if not atoms:
        return [last_action.copy_state()]

    for atom in atoms:
        action = _atom_to_action(atom, last_action)
        actions.append(action)
        last_action = action

    return actions


SPACE = ' '
NO_SPACE = ''
META_STOPS = ('.', '!', '?')
META_COMMAS = (',', ':', ';')
META_ED_SUFFIX = '^ed'
META_ER_SUFFIX = '^er'
META_ING_SUFFIX = '^ing'
META_CAPITALIZE = '-|'
META_PLURALIZE = '^s'
META_GLUE_FLAG = '&'
META_ATTACH_FLAG = '^'
META_KEY_COMBINATION = '#'
META_COMMAND = 'PLOVER:'

# TODO: unittest this
def _raw_to_actions(stroke, last_action):
    # If a raw stroke is composed of digits then remove the dash (if 
    # present) and glue it to any neighboring digits. Otherwise, just 
    # output the raw stroke as is.
    no_dash = stroke.replace('-', '', 1)
    if no_dash.isdigit():
        return _translation_to_actions(no_dash, last_action)
    else:
        return [_Action(text=(SPACE + stroke))]

META_SUFFIX_FUNCTIONS = {META_ED_SUFFIX: orthography.add_ed_suffix,
                         META_ER_SUFFIX: orthography.add_er_suffix,
                         META_ING_SUFFIX: orthography.add_ing_suffix,
                         META_PLURALIZE: orthography.pluralize_with_s}
META_SUFFIX = set(META_SUFFIX_FUNCTIONS.keys())

def _atom_to_action(atom, last_action):
    action = _Action()
    last_word = last_action.word
    last_glue = last_action.glue
    last_attach = last_action.attach
    last_capitalize = last_action.capitalize
    meta = _get_meta(atom)
    if meta is not None:
        meta = _unescape_atom(meta)
        if meta in META_SUFFIX:
            suffix_f = META_SUFFIX_FUNCTIONS[meta]
            new = suffix_f(last_word)
            common = commonprefix([last_word, new])
            action.replace = last_word[len(common):]
            action.text = new[len(common):]
            action.word = new
        elif meta in META_COMMAS:
            action.text = meta
        elif meta in META_STOPS:
            action.text = meta
            action.capitalize = True
        elif meta == META_CAPITALIZE:
            action = last_action.copy_state()
            action.capitalize = True
        elif meta.startswith(META_COMMAND):
            action = last_action.copy_state()
            action.command = meta[len(META_COMMAND):]
        elif meta.startswith(META_GLUE_FLAG):
            action.glue = True
            glue = last_glue or last_attach
            space = NO_SPACE if glue else SPACE
            text = meta[len(META_GLUE_FLAG):]
            if last_capitalize:
                text = _capitalize(text)
            action.text = space + text
            action.word = _rightmost_word(last_word + action.text)
        elif (meta.startswith(META_ATTACH_FLAG) or 
              meta.endswith(META_ATTACH_FLAG)):
            begin = meta.startswith(META_ATTACH_FLAG)
            end = meta.endswith(META_ATTACH_FLAG)
            if begin:
                meta = meta[len(META_ATTACH_FLAG):]
            if end and len(meta) >= len(META_ATTACH_FLAG):
                meta = meta[:-len(META_ATTACH_FLAG)]
            space = NO_SPACE if begin or last_attach else SPACE
            if end:
                action.attach = True
            if last_capitalize:
                meta = _capitalize(meta)
            action.text = space + meta
            action.word = _rightmost_word(last_word + action.text)
        elif meta.startswith(META_KEY_COMBINATION):
            action = last_action.copy_state()
            action.combo = meta[len(META_KEY_COMBINATION):]
    else:
        text = _unescape_atom(atom)
        if last_capitalize:
            text = _capitalize(text)
        space = NO_SPACE if last_attach else SPACE
        action.text = space + text
        action.word = _rightmost_word(text)
    return action

def _get_meta(atom):
    # Return the meta command, if any, without surrounding meta markups.
    if (atom is not None and
        atom.startswith(META_START) and
        atom.endswith(META_END)):
        return atom[len(META_START):-len(META_END)]
    return None

def _apply_glue(s):
    # Mark the given string as a glue stroke.
    return META_START + META_GLUE_FLAG + s + META_END

def _unescape_atom(atom):
    # Replace escaped meta markups with unescaped meta markups.
    return atom.replace(META_ESC_START, META_START).replace(META_ESC_END,
                                                            META_END)

def _get_engine_command(atom):
    # Return the steno engine command, if any, represented by the
    # given atom.
    if (atom and
        atom.startswith(META_START + META_COMMAND) and
        atom.endswith(META_END)):
        return atom[len(META_START) + len(META_COMMAND):-len(META_END)]
    return None

def _capitalize(s):
    if s:
        return s[0].upper() + s[1:]
    else:
        return s

def _rightmost_word(s):
    split = s.split()
    return split[-1] if split else ''
