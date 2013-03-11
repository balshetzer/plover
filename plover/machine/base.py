# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Base classes for machine types. Do not use directly."""

# TODO: Stop calling the steno variable "RTFCRE".

import serial
import threading
from plover.exception import SerialPortException

STENO_KEY_NUMBERS = { 'S-': '1-',
                      'T-': '2-',
                      'P-': '3-',
                      'H-': '4-',
                      'A-': '5-',
                      'O-': '0-',
                      '-F': '-6',
                      '-P': '-7',
                      '-L': '-8',
                      '-T': '-9'}

STENO_KEY_ORDER = {"#": -1,
                   "S-": 0,
                   "T-": 1,
                   "K-": 2,
                   "P-": 3,
                   "W-": 4,
                   "H-": 5,
                   "R-": 6,
                   "A-": 7,
                   "O-": 8,
                   "*": 9,     # Also 10, 11, and 12 for some machines.
                   "-E": 13,
                   "-U": 14,
                   "-F": 15,
                   "-R": 16,
                   "-P": 17,
                   "-B": 18,
                   "-L": 19,
                   "-G": 20,
                   "-T": 21,
                   "-S": 22,
                   "-D": 23,
                   "-Z": 24}

IMPLICIT_HYPHEN = set(('A-', 'O-', '5-', '0-', '-E', '-U', '*'))

class Stroke(object):
    """A standardized data model for stenotype machine strokes.

    This class standardizes the representation of a stenotype chord. A
    stenotype chord can be any sequence of stenotype keys that can be
    simultaneously pressed. Nearly all stenotype machines offer the same set of
    keys that can be combined into a chord, though some variation exists due to
    duplicate keys. This class accounts for such duplication, imposes the
    standard stenographic ordering on the keys, and combines the keys into a
    single string (called RTFCRE for historical reasons) according to a
    particular dictionary format.

    """

    def __init__(self, steno_keys) :
        """Create a steno stroke by formatting steno keys.

        Arguments:

        steno_keys -- A sequence of pressed keys.

        """
        # Remove duplicate keys and save local versions of the input 
        # parameters.
        steno_keys_set = set(steno_keys)
        steno_keys = list(steno_keys_set)

        # Order the steno keys so comparisons can be made.
        steno_keys.sort(key=lambda x: STENO_KEY_ORDER[x])
         
        # Convert strokes involving the number bar to numbers.
        if '#' in steno_keys:
            numeral = False
            for i, e in enumerate(steno_keys):
                if e in STENO_KEY_NUMBERS:
                    steno_keys[i] = STENO_KEY_NUMBERS[e]
                    numeral = True
            if numeral:
                steno_keys.remove('#')
        
        if steno_keys_set & IMPLICIT_HYPHEN:
            self.rtfcre = ''.join(key.strip('-') for key in steno_keys)
        else:
            pre = ''.join(k.strip('-') for k in steno_keys if k[-1] == '-' or 
                          k == '#')
            post = ''.join(k.strip('-') for k in steno_keys if k[0] == '-')
            self.rtfcre = '-'.join([pre, post]) if post else pre

        self.steno_keys = steno_keys

        # Determine if this stroke is a correction stroke.
        self.is_correction = (self.rtfcre == '*')

    def __str__(self):
        if self.is_correction:
            prefix = '*'
        else:
            prefix = ''
        return '%sStroke(%s)' % (prefix, self.rtfcre)

    def __eq__(self, other):
        return isinstance(other, Stroke) and self.rtfcre==other.rtfcre

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return str(self)


class StenotypeBase:
    """The base class for all Stenotype classes."""

    # Some subclasses of StenotypeBase might require configuration
    # parameters to be passed to the constructor. This variable
    # advertises the class that contains such parameters.
    CONFIG_CLASS = None
    
    def __init__(self):
        self.subscribers = []

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        pass

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        pass

    def add_callback(self, callback):
        """Subscribe to output from the stenotype machine.

        Argument:

        callback -- The function to call whenever there is output from
        the stenotype machine and output is being captured.

        """
        self.subscribers.append(callback)
        
    def remove_callback(self, callback):
        """Unsubscribe from output from the stenotype machine.

        Argument:

        callback -- A function previously added using add_callback.

        """
        self.subscribers.remove(callback)

    def _notify(self, steno_keys):
        """Invoke the callback of each subscriber with the given argument."""
        stroke = Stroke(steno_keys)
        for callback in self.subscribers:
            callback(stroke)


class SerialStenotypeBase(StenotypeBase, threading.Thread):
    """For use with stenotype machines that connect via serial port.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    CONFIG_CLASS = serial.Serial

    def __init__(self, **kwargs):
        """Monitor the stenotype over a serial port.

        Keyword arguments are the same as the keyword arguments for a
        serial.Serial object.

        """
        try:
            self.serial_port = self.CONFIG_CLASS(**kwargs)
        except serial.SerialException:
            raise SerialPortException()
        if self.serial_port is None or not self.serial_port.isOpen():
            raise SerialPortException()
        threading.Thread.__init__(self)
        StenotypeBase.__init__(self)
        self.finished = threading.Event()
        
    def run(self):
        """This method should be overridden by a subclass."""
        pass

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        self.finished.clear()
        self.start()

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        self.finished.set()
        # TODO: Don't close the port until the loop reports that it stopped.
        self.serial_port.close()
