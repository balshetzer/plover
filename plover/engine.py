# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Configuration, initialization, and control of the Plover steno pipeline.

This module's single class, StenoEngine, encapsulates the
configuration, initialization, and control (starting and stopping) of
a complete stenographic processing pipeline, from reading stroke keys
from a stenotype machine to outputting translated English text to the
screen. Configuration parameters are read from a user-editable
configuration file. In addition, application log files are maintained
by this module. This module does not provide a graphical user
interface.

"""

# TODO: The application switches between modes:
# write mode: inputs to the machine are translated and output
# command only mode: inputs are discarded unless it triggers a command
# dict editing raw stroke mode: inputs are recorded as raw strokes and only rendered in the lhs of the dict editor. except for some strokes which are interpreted as commands.
# dict editing translation mode: inputs are recorded as either raw translations or normal outputs but are only rendered in the rhs of dict editing. except for some strokes which are interpreted as commands.

# TODO: If the UI is to make changes while the machine is also sending updates
# (from another thread) then we need some thread safety here.

import formatting
import translation

class StenoEngine(object):
    """Top-level class for using a stenotype machine for text input.

    This class combines all the non-GUI pieces needed to use a stenotype
    machine as a general purpose text entry device. The entire pipeline
    consists of the following elements:

    machine: Typically an instance of the Stenotype class from one of
    the submodules of plover.machine. This object is responsible for
    monitoring a particular type of hardware for stenotype output and
    passing that output on to the translator.

    translator: Typically an instance of the plover.steno.Translator
    class. This object converts raw steno keys into strokes and
    strokes into translations. The translation objects are then passed
    on to the formatter.

    formatter: Typically an instance of the
    plover.formatting.Formatter class. This object converts
    translation objects into printable English text that can be
    displayed to the user. Orthographic and lexical rules, such as
    capitalization at the beginning of a sentence and pluralizing a
    word, are taken care of here. The formatted text is then passed on
    to the output.

    output: Typically an instance of the
    plover.oslayer.keyboardcontrol.KeyboardEmulation class. This object
    displays text on the screen.

    In addition to the above pieces, a logger records timestamped
    strokes and translations. Many of these pieces can be configured
    by the user via a configuration file, which is by default located
    at ~/.config/plover/plover.cfg and will be automatically generated
    with reasonable default values if it doesn't already exist.

    """
    
    def __init__(self):
        """Creates and configures a single steno pipeline."""
        self._logger = None
        self._is_logging_strokes = False
        self._is_logging_translations = False

        # Construct the stenography capture-translate-format-display pipeline.
        self._translator = translation.Translator()
        # hack
        self._translator.set_undo_length(30)
        self._formatter = formatting.Formatter()
        self._translator.add_listener(self._formatter.format)

    def process_stroke(self, stroke):
        if self._is_logging_strokes:
            self._log_stroke(stroke)
        self._translator.translate(stroke)

    def add_translation(self, key, value):
        self._translator.add_translation(key, value)

    def add_translations(self, dictionary):
        self._translator.add_translations(dictionary)

    def remove_translations(self, keys):
        self._translator.remove_translations(keys)
        
    def set_output(self, output):
        self._formatter.set_output(output)

    def set_log_strokes(self, yes):
        self._is_logging_strokes = yes

    def set_log_translations(self, yes):
        if yes and not self._is_logging_translations:
            self._is_logging_translations = True
            self._translator.add_listener(self._log_translation)
        if not yes and self._is_logging_translations:
            self._is_logging_translations = False
            self._translator.remove_listener(self._log_translation)

    def set_logger(self, logger):
        self._logger = logger

    def _log_stroke(self, stroke):
        if self._logger:
            self._logger.info('Stroke(%s)' % ' '.join(stroke.steno_keys))

    def _log_translation(self, undo, do, prev):
        if self._logger:
            self._logger.info((undo, do, prev))
