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
import plover.machine
import plover.machine.base
import engine

STROKE_DELIMITER = '/'

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
                json_dict = json.load(f)
        except UnicodeDecodeError:
            with open(dictionary_path, 'r') as f:
                json_dict = json.load(f, conf.ALTERNATIVE_ENCODING)
    else:
        raise ValueError('The value of %s must end with %s.' %
                         (conf.DICTIONARY_FILE_OPTION, conf.JSON_EXTENSION))
    dictionary = {}
    for k, v in json_dict.items():
        dictionary[tuple(k.split(STROKE_DELIMITER))] = v
    return dictionary

def machine_from_config(config):
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
    machine = machine_module.Stenotype(**machine_init)
    return machine

def steno_engine_from_config(config):
    """Creates and configures a single steno pipeline."""

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
    #output = keyboardcontrol.KeyboardEmulation()

    steno_engine = engine.StenoEngine()
    steno_engine.add_translations(dictionary)
    steno_engine.set_logger(logger)
    #steno_engine.set_output(output)  # TODO: This isn't a full output because it has no engine commands.

    # Add hooks for logging.
    log_strokes = config.getboolean(conf.LOGGING_CONFIG_SECTION,
                                    conf.ENABLE_STROKE_LOGGING_OPTION)
    steno_engine.set_log_strokes(log_strokes)
    log_translations = config.getboolean(conf.LOGGING_CONFIG_SECTION,
                                         conf.ENABLE_TRANSLATION_LOGGING_OPTION)
    steno_engine.set_log_translations(log_translations)

    return steno_engine
