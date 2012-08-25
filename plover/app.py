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

# Import standard library modules.
import os
import logging
import logging.handlers
try :
    import simplejson as json
except ImportError :
    import json

# Import plover modules.
import plover.config as conf
import plover.formatting as formatting
import plover.oslayer.keyboardcontrol as keyboardcontrol
import plover.steno as steno
import plover.machine
import plover.machine.base
import plover.machine.sidewinder
import plover.dictionary

def load_dict(config):
    # Load the dictionary. The dictionary path can be either
    # absolute or relative to the configuration directory.
    dictionary_filename = config.get(conf.DICTIONARY_CONFIG_SECTION,
                                     conf.DICTIONARY_FILE_OPTION)
    dictionary_path = os.path.join(conf.CONFIG_DIR, dictionary_filename)
    if not os.path.isfile(dictionary_path):
        raise ValueError('Invalid configuration value for %s: %s' %
                         (conf.DICTIONARY_FILE_OPTION, dictionary_path))
    dictionary_extension = os.path.splitext(dictionary_path)[1]
    if dictionary_extension == conf.JSON_EXTENSION:
        try:
            with open(dictionary_path, 'r') as f:
                dictionary = json.load(f)
        except UnicodeDecodeError:
            with open(dictionary_path, 'r') as f:
                dictionary = json.load(f, conf.ALTERNATIVE_ENCODING)
    else:
        raise ValueError('The value of %s must end with %s.' %
                         (conf.DICTIONARY_FILE_OPTION, conf.JSON_EXTENSION))
    return dictionary

def steno_engine_from_config(config):
    """Creates and configures a single steno pipeline."""

    # Set the machine module and any initialization variables.
    machine_type = config.get(conf.MACHINE_CONFIG_SECTION,
                              conf.MACHINE_TYPE_OPTION)
    machine_module = conf.import_named_module(machine_type, 
                                              plover.machine.supported)
    if machine_module is None:
        raise ValueError('Invalid configuration value for %s: %s' %
                         (conf.MACHINE_TYPE_OPTION, machine_type))
    
    machine_init = {}
    if issubclass(machine_module.Stenotype,
                  plover.machine.base.SerialStenotypeBase):
        serial_params = conf.get_serial_params(machine_type, config)
        machine_init.update(serial_params.__dict__)

    # Set the steno dictionary format module.
    dictionary_format = config.get(conf.DICTIONARY_CONFIG_SECTION,
                                   conf.DICTIONARY_FORMAT_OPTION)
    dictionary_module = conf.import_named_module(dictionary_format,
                                                 plover.dictionary.supported)
    if dictionary_module is None:
        raise ValueError('Invalid configuration value for %s: %s' %
                         (conf.DICTIONARY_FORMAT_OPTION, dictionary_format))

    dictionary = load_dict(config)

    # Initialize the logger.
    log_file = os.path.join(conf.CONFIG_DIR,
                            config.get(conf.LOGGING_CONFIG_SECTION,
                                       conf.LOG_FILE_OPTION))
    logger = logging.getLogger(conf.LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                maxBytes=conf.LOG_MAX_BYTES,
                                                backupCount=conf.LOG_COUNT)
    handler.setFormatter(logging.Formatter(conf.LOG_FORMAT))
    logger.addHandler(handler)

    # Construct the stenography capture-translate-format-display pipeline.
    machine = machine_module.Stenotype(**machine_init)
    output = keyboardcontrol.KeyboardEmulation()

    engine = StenoEngine(machine, dictionary, dictionary_module, logger, output)

    auto_start = config.getboolean(conf.MACHINE_CONFIG_SECTION,
                                   conf.MACHINE_AUTO_START_OPTION)
    engine.set_is_running(auto_start)

    # Add hooks for logging.
    log_strokes = config.getboolean(conf.LOGGING_CONFIG_SECTION,
                                    conf.ENABLE_STROKE_LOGGING_OPTION)
    engine.set_log_strokes(log_strokes)
    log_translations = config.getboolean(conf.LOGGING_CONFIG_SECTION,
                                         conf.ENABLE_TRANSLATION_LOGGING_OPTION)
    engine.set_log_translations(log_translations)

    return engine

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
    
    def __init__(self, machine, dictionary, dictionary_module, logger, output):
        """Creates and configures a single steno pipeline."""
        self.machine = None
        self.logger = logger
        self.output = output

        self.subscribers = []
        self.is_running = False
        self.is_logging_strokes = False
        self.is_logging_translations = False

        # Construct the stenography capture-translate-format-display pipeline.
        # TODO: Rip out the very concept of alternate dictionary formats from this part of plover.

        # TODO: Create a context that holds state for translator and formatter so that
        # when the user switches windows, each window gets its own context? This still
        # wouldn't catch switching fields in one window.
        
        self.translator = steno.Translator(dictionary_module)
        self.formatter = formatting.Formatter(self.translator)
        
        self.add_translations(dictionary)
        self.set_machine(machine)
        
    def set_machine(self, machine):
        if self.machine:
            self.machine.remove_callback(translator.consume_steno_keys)
            if self.is_logging_strokes:
                self.machine.remove_callback(self._log_strokes)
            self.machine.stop_capture()
        self.machine = machine
        if self.machine:
            self.machine.add_callback(self.translator.consume_steno_keys)
            if self.is_logging_strokes:
                self.machine.add_callback(self._log_stroke)
            self.machine.start_capture()
        
    def add_translations(self, dictionary):
        self.translator.add_translations(dictionary)
        
    def remove_translations(self, keys):
        self.translator.remove_translations(keys)
        
    def set_log_strokes(self, yes):
        if yes and not self.is_logging_strokes:
            self.is_logging_strokes = True
            self.machine.add_callback(self._log_stroke)
        if not yes and self.is_logging_strokes:
            self.is_logging_strokes = False
            self.machine.remove_callback(self._log_stroke)
            
    def set_log_translations(self, yes):
        if yes and not self.is_logging_translations:
            self.is_logging_translations = True
            self.translator.add_callback(self._log_translation)
        if not yes and self.is_logging_translations:
            self.is_logging_translations = False
            self.translator.remove_callback(self._log_translation)
            
    def add_callback(self, callback) :
        """Subscribes a function to receive changes of the is_running  state.

        Arguments:

        callback -- A function that takes no arguments.

        """
        self.subscribers.append(callback)

    def remove_callback(self, callback) :
        """Unsubscribes a function from receiving changes of the is_running  
        state.

        Arguments:

        callback -- A function that was previously added using add_callback.

        """
        self.subscribers.remove(callback)

    def set_is_running(self, value):
        self.is_running = value
        if self.is_running:
            self.formatter.text_output = self.output
        else:
            self.formatter.text_output = None
        if self.machine and hasattr(self.machine, 'suppress_keyboard'):
            self.machine.suppress_keyboard(self.is_running)
        for callback in self.subscribers:
            callback()

    def destroy(self):
        """Halts the stenography capture-translate-format-display pipeline.

        Calling this method causes all worker threads involved to
        terminate. This method should be called at least once if the
        start method had been previously called. Calling this method
        more than once or before the start method has been called has
        no effect.

        """
        self.set_is_running(False)
        if self.machine:
            self.machine.stop_capture()

    def set_engine_command_callback(self, callback):
        self.formatter.engine_command_callback = callback

    def _log_stroke(self, steno_keys):
        self.logger.info('Stroke(%s)' % ' '.join(steno_keys))

    def _log_translation(self, translation, overflow):
        self.logger.info(translation)