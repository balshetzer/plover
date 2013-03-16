# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Functions that implement some English orthographic rules."""

CONSONANTS = 'bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
VOWELS = 'aeiouAEIOU'
W = 'wW'
Y = 'yY'
PLURAL_SPECIAL = 'sxzSXZ'

add_s = {}
add_ed = {}
add_ing = {}
add_er = {}
add_est = {}

def initialize_tables():
    import plover.config as conf
    import os
    path = os.path.join(conf.ASSETS_DIR, 'infl.txt')
    f = open(path)
    lines = f.readlines()
    
    for line in lines:
        first, second = line.split(':', 1)
        word_part = first.split()
        word = word_part[0]
        part = word_part[1][0]
        inflections = [x.split()[0].strip(',~<!?') for x in second.split('|')]

        if part == 'N':
            if inflections[0] != word and inflections[0].endswith('s'):
                add_s[word] = inflections[0]
        elif part == 'A':
            if len(inflections) != 2:
                continue
            if inflections[0] != word and inflections[0].endswith('er'):
                add_er[word] = inflections[0]
            if inflections[1] != word and inflections[1].endswith('est'):
                add_est[word] = inflections[1]
        elif part == 'V':
            if len(inflections) != 3 and len(inflections) != 4:
                continue
            if inflections[0] != word and inflections[0].endswith('ed'):
                add_ed[word] = inflections[0]
            if inflections[-2] != word and inflections[-2].endswith('ing'):
                add_ing[word] = inflections[-2]
            if inflections[-1] != word and inflections[-1].endswith('s'):
                add_s[word] = inflections[-1]

try:
    initialize_tables()
except Exception as e:
    print e

def _add_s_suffix(word):
    """Use rules to append s to a word."""
    if len(word) < 2:
        return word + 's'
    a = word[-2]
    b = word[-1]
    if b in PLURAL_SPECIAL:
        return word + 'es'
    elif b in Y and a in CONSONANTS:
        return word[:-1] + 'ies'
    return word + 's'

def add_s_suffix(word):
    """Form the plural of a word or the present tense of a verb by adding an s.

    Argument:

    word -- A singular noun or noun phrase.

    """
    return add_s.get(word, _add_s_suffix(word))

def _add_ed_suffix(word):
    """Use rules to add ed to a word."""
    return _prep_for_simple_suffix(word) + 'ed'

def add_ed_suffix(word):
    """Form the past tense of a verb by adding 'ed'.

    Argument:

    word -- The infinitive form of a verb.

    """
    return add_ed.get(word, _add_ed_suffix(word))

def _add_er_suffix(word):
    """Use rules to add er suffix to the end of a word."""
    return _prep_for_simple_suffix(word) + 'er'

def add_er_suffix(word):
    """Add an -er suffix to the end of a word.

    Argument:

    word -- An adjective or verb.

    """
    return add_er.get(word, _add_er_suffix(word))

def _add_ing_suffix(word):
    """Use rules to add er to a word."""
    if word and word[-1] in Y: # See _prep_for_simple_suffix special case.
        return word + 'ing'
    return _prep_for_simple_suffix(word) + 'ing'
    
def add_ing_suffix(word):
    """Add an -ing suffix to the end of a word.

    Argument:

    word -- The infinitive form of a verb.

    """
    return add_ing.get(word, _add_ing_suffix(word))

def _add_est_suffix(word):
    """Use rules to add est to a word."""
    return _prep_for_simple_suffix(word) + 'est'

def add_est_suffix(word):
    """Add an -est suffix to the end of a word.

    Argument:

    word -- The infinitive form of a verb.

    """
    return add_est.get(word, _add_est_suffix(word))

def _prep_for_simple_suffix(word):
    num_chars = len(word)
    if num_chars < 2:
        return word
    if num_chars >= 3:
        third_to_last = word[-3]
    else:
        third_to_last = ''
    second_to_last = word[-2]
    last = word[-1]
    if second_to_last in VOWELS or second_to_last in CONSONANTS:
        if last in VOWELS:
            if third_to_last and (third_to_last in VOWELS or
                                  third_to_last in CONSONANTS):
                return word[:-1]
        elif (last in CONSONANTS and
              last not in W and
              second_to_last in VOWELS and
              third_to_last and
              third_to_last not in VOWELS):
            return word + last
        elif last in Y and second_to_last in CONSONANTS:
            return word[:-1] + 'i' # Special case doesn't work for 'ing' suffix.
    return word
