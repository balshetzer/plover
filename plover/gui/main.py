# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""The main graphical user interface.

Plover's graphical user interface is a simple task bar icon that
pauses and resumes stenotype translation and allows for application
configuration.

"""

# BUG: In command mode on keyboard, regular text is still typed when used as a command.

# TODO: swap out states when doing dict updates

# TODO: threading issues

# write: normal keyboard
# command only: ability to turn on or off

# stroke: only raw strokes except for some special command(s). output directed to a specific field. or just on while focused. if in command only mode then nothing.
# raw: unformatted dictionary except for some special command(s). output directed to a specific field. or just on while focused. if in command only mode then nothing.

import os
import wx
import threading
import copy
import ConfigParser
import plover.app as app
import plover.config as conf
import plover.gui.config as gui
import plover.exception as exception
import plover.oslayer.keyboardcontrol as keyboardcontrol

import plover.translation as translation

from plover import __name__ as __software_name__
from plover import __version__
from plover import __copyright__
from plover import __long_description__
from plover import __url__
from plover import __credits__
from plover import __license__

class PloverGUI(wx.App):
    """The main entry point for the Plover application."""
    
    def __init__(self):
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        """Called just before the application starts."""
        frame = Frame()
        frame.Show()
        self.SetTopWindow(frame)
        return True

class Frame(wx.Frame):
    """The top-level GUI element of the Plover application."""

    # Class constants.
    TITLE = "Plover"
    ALERT_DIALOG_TITLE = TITLE
    ON_IMAGE_FILE = "plover_on.png"
    OFF_IMAGE_FILE = "plover_off.png"
    BORDER = 5
    RUNNING_MESSAGE = "running"
    STOPPED_MESSAGE = "stopped"
    ERROR_MESSAGE = "error"
    CONFIGURE_BUTTON_LABEL = "Configure..."
    ABOUT_BUTTON_LABEL = "About..."
    COMMAND_SUSPEND = 'SUSPEND'
    COMMAND_RESUME = 'RESUME'
    COMMAND_TOGGLE = 'TOGGLE'
    COMMAND_CONFIGURE = 'CONFIGURE'
    COMMAND_FOCUS = 'FOCUS'
    COMMAND_QUIT = 'QUIT'
    COMMAND_DICT_UPDATE = "DICT_UPDATE"
    COMMAND_TOGGLE_FIELDS = "TOGGLE_FIELDS"
    COMMAND_ADD_TRANSLATION = "ADD_TRANSLATION"
    COMMAND_CANCEL = "CANCEL"
    
    def __init__(self):
        wx.Frame.__init__(self, None,
                          title=self.TITLE,
                          pos=wx.DefaultPosition,
                          size=wx.DefaultSize,
                          style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER|
                                                           wx.RESIZE_BOX|
                                                           wx.MAXIMIZE_BOX))
        # Status button.
        on_icon_file = os.path.join(conf.ASSETS_DIR, self.ON_IMAGE_FILE)
        off_icon_file = os.path.join(conf.ASSETS_DIR, self.OFF_IMAGE_FILE)
        self.on_bitmap = wx.Bitmap(on_icon_file, wx.BITMAP_TYPE_PNG)
        self.off_bitmap = wx.Bitmap(off_icon_file, wx.BITMAP_TYPE_PNG)
        self.status_button = wx.BitmapButton(self, bitmap=self.on_bitmap)
        self.status_button.Bind(wx.EVT_BUTTON, self._toggle_machine)

        # Configure button.
        self.configure_button = wx.Button(self, label=self.CONFIGURE_BUTTON_LABEL)
        self.configure_button.Bind(wx.EVT_BUTTON, self._show_config_dialog)

        # About button.
        self.about_button = wx.Button(self, label=self.ABOUT_BUTTON_LABEL)
        self.about_button.Bind(wx.EVT_BUTTON, self._show_about_dialog)

        # Layout.
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.status_button,
                  flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.configure_button,
                  flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.about_button,
                  flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_CLOSE, self._quit)
        
        config = conf.get_config()
        self.steno_engine = app.steno_engine_from_config(conf.get_config())
        self.output = _Output(self.consume_command)
        self.steno_engine.set_output(self.output)
        self.machine = None
        self._init_machine(config)

        auto_start = config.getboolean(conf.MACHINE_CONFIG_SECTION,
                                       conf.MACHINE_AUTO_START_OPTION)
        self._set_machine_on(auto_start)
        
        # Hacky stuff for dict update
        self.real_dict = self.steno_engine._translator._dictionary
        self.dict_dialog = AddToDictDialog(self)
        self.lock = threading.RLock()

    def consume_command(self, command):
        # Wrap all actions in a CallAfter since the initiator of the
        # action is likely a thread other than the wx thread.
        if command == self.COMMAND_SUSPEND and self.steno_engine:
            wx.CallAfter(self._set_machine_on, False)
        elif command == self.COMMAND_RESUME and self.steno_engine:
            wx.CallAfter(self._set_machine_on, True)
        elif command == self.COMMAND_TOGGLE and self.steno_engine:
            wx.CallAfter(self._toggle_machine)
        elif command == self.COMMAND_CONFIGURE:
            wx.CallAfter(self._show_config_dialog)
        elif command == self.COMMAND_FOCUS:
            wx.CallAfter(self.Raise)
            wx.CallAfter(self.Iconize, False)
        elif command == self.COMMAND_DICT_UPDATE:
            wx.CallAfter(self._show_dict_dialog)
        elif command == self.COMMAND_TOGGLE_FIELDS:
            wx.CallAfter(self.dict_dialog.toggle_fields)
        elif command == self.COMMAND_ADD_TRANSLATION:
            wx.CallAfter(self.dict_dialog.add_translation)
        elif command == self.COMMAND_CANCEL:
            wx.CallAfter(self.dict_dialog.cancel)
        elif command == self.COMMAND_QUIT:
            wx.CallAfter(self._quit)

    def _update_status(self):
        if self.machine:
            self.status_button.Enable()
            if self._is_machine_on():
                self.status_button.SetBitmapLabel(self.on_bitmap)
                self.SetTitle("%s: %s" % (self.TITLE, self.RUNNING_MESSAGE))
            else:
                self.status_button.SetBitmapLabel(self.off_bitmap)
                self.SetTitle("%s: %s" % (self.TITLE, self.STOPPED_MESSAGE))
        else:
            self.status_button.Disable()
            self.status_button.SetBitmapLabel(self.off_bitmap)
            self.SetTitle("%s: %s" % (self.TITLE, self.ERROR_MESSAGE))

    def _quit(self, event=None):
        if self.machine:
            self.machine.stop_capture()
        self.Destroy()

    def _toggle_machine(self, event=None):
        """Called when the status button is clicked."""
        if self.machine:
            self._set_machine_on(not self._is_machine_on())

    def _set_machine_on(self, b):
        if self.machine:
            self.output.mode = (OUTPUT_MODE_WRITE if b else 
                                OUTPUT_MODE_COMMAND_ONLY)
            if hasattr(self.machine, 'suppress_keyboard'):
                self.machine.suppress_keyboard(b)
        self._update_status()
        
    def _is_machine_on(self):
        return self.machine and self.output.mode == OUTPUT_MODE_WRITE

    def _show_config_dialog(self, event=None):
        dialog = gui.ConfigurationDialog(conf.CONFIG_FILE, self)
        dialog.Show()
        return dialog
        
    def _show_dict_dialog(self):
        self.dict_dialog.Show()
        self.dict_dialog.reset()

    def _show_about_dialog(self, event=None):
        """Called when the About... button is clicked."""
        info = wx.AboutDialogInfo()
        info.Name = __software_name__
        info.Version = __version__
        info.Copyright = __copyright__
        info.Description = __long_description__
        info.WebSite = __url__
        info.Developers = __credits__
        info.License = __license__
        wx.AboutBox(info)
        
    def _machine_callback(self, stroke):
        with self.lock:
            self.steno_engine.process_stroke(stroke)
        
    def _init_machine(self, config=None):
        config = config if config else conf.get_config()
        if self.machine:
            self.machine.stop_capture()
            self.machine.remove_callback(self._machine_callback)
            self.machine = None
        try:
            self.machine = app.machine_from_config(conf.get_config())
        except exception.SerialPortException, spe:
            self.machine = None
            alert_dialog = wx.MessageDialog(self._show_config_dialog(),
                                            unicode(spe),
                                            self.ALERT_DIALOG_TITLE,
                                            wx.OK | wx.ICON_INFORMATION)
            alert_dialog.ShowModal()
            alert_dialog.Destroy()
            return
        self.machine.add_callback(self._machine_callback)
        self.machine.start_capture()
        # TODO: A way to wait on the machine being ready?

OUTPUT_MODE_WRITE = 1
OUTPUT_MODE_COMMAND_ONLY = 2

class _Output(object):
    def __init__(self, engine):
        self.keyboard = keyboardcontrol.KeyboardEmulation()
        self.engine = engine
        self.output_buffer = ''
        self.mode = OUTPUT_MODE_COMMAND_ONLY

    def set_mode(self, mode):
        self.mode = mode

    def send_backspaces(self, n):
        if self.mode == OUTPUT_MODE_COMMAND_ONLY:
            return
        self.keyboard.send_backspaces(n)

    def send_string(self, s):
        if self.mode == OUTPUT_MODE_COMMAND_ONLY:
            return
        self.keyboard.send_string(s)

    def send_key_combination(self, c):
        if self.mode == OUTPUT_MODE_COMMAND_ONLY:
            return
        self.keyboard.send_key_combination(c)

    def send_engine_command(self, c):
        self.engine(c)

class AddToDictDialog(wx.Dialog):
    def __init__(self, 
                 parent,
                 id=wx.ID_ANY,
                 title='', 
                 pos=wx.DefaultPosition,
                 size=wx.DefaultSize, 
                 style=wx.DEFAULT_DIALOG_STYLE,
                 name=wx.DialogNameStr):
        super(AddToDictDialog, self).__init__(parent, id, title, pos, size, style, name)
        
        self.parent = parent
        
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        box = wx.BoxSizer(wx.HORIZONTAL)
        
        box.Add(wx.StaticText(self, label='strokes:'), border=3)
        self.strokes_text = wx.TextCtrl(self)
        self.strokes_text.Bind(wx.EVT_TEXT, self._on_strokes_change)
        self.strokes_text.Bind(wx.EVT_SET_FOCUS, self._on_strokes_gained_focus)
        self.strokes_text.Bind(wx.EVT_KILL_FOCUS, self._on_strokes_lost_focus)
        box.Add(self.strokes_text, border=3)
        box.Add(wx.StaticText(self, label='translation:'), border=3)
        self.translation_text = wx.TextCtrl(self)
        self.translation_text.Bind(wx.EVT_TEXT, self._on_translation_change)
        self.translation_text.Bind(wx.EVT_SET_FOCUS, self._on_translation_gained_focus)
        self.translation_text.Bind(wx.EVT_KILL_FOCUS, self._on_translation_lost_focus)
        box.Add(self.translation_text, border=3)
        button = wx.Button(self, label='Add to dictionary')
        button.Bind(wx.EVT_BUTTON, self.add_translation)
        box.Add(button)
        sizer.Add(box)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.stroke_mapping_text = wx.StaticText(self)
        box.Add(self.stroke_mapping_text)
        sizer.Add(box)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.translation_mapping_text = wx.StaticText(self)
        box.Add(self.translation_mapping_text)
        sizer.Add(box)
        
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        sizer.Fit(self)
        sizer.SetSizeHints(self)
        self.Layout()
        
        # BUG: reverse dict doesn't update with dict changes
        self.dictionary = self.parent.real_dict
        self.reverse_dictionary = {}
        for k, v in self.dictionary.items():
            if v in self.reverse_dictionary:
                self.reverse_dictionary[v].append(k)
            else:
                self.reverse_dictionary[v] = [k]

        self._stroke_dict = translation._Dictionary()
        # BUG: This doesn't work if there are spaces
        for special in ['{PLOVER:TOGGLE_FIELDS}', '{PLOVER:ADD_TRANSLATION}',
                        '{PLOVER:CANCEL}']:
            if special in self.reverse_dictionary:
                for strokes in self.reverse_dictionary[special]:
                    self._stroke_dict[strokes] = special
                    
        self.stroke_in_focus = True
        
        # cached state
        self.cached_state = None

    def reset(self):
        self.strokes_text.SetValue('')
        self.translation_text.SetValue('')
        self.strokes_text.SetFocus()

    def cancel(self):
        self.Close()

    def add_translation(self, event=None):
        with self.parent.lock:
            d = self.parent.real_dict
            strokes = tuple(s for s in self.strokes_text.GetValue().split())
            translation = self.translation_text.GetValue()
            d[strokes] = translation
            # TODO: Save file
            app.save_dict(conf.get_config(), d)
            self.Close()

    def toggle_fields(self):
        if self.stroke_in_focus:
            self.translation_text.SetFocus()
        else:
            self.strokes_text.SetFocus()

    def _on_strokes_change(self, event):
        with self.parent.lock:
            stroke = event.GetString()
            if stroke:
                stroke = stroke.upper()
                self.strokes_text.ChangeValue(stroke)
                self.strokes_text.SetInsertionPointEnd()
                translation = self.dictionary.get(tuple(stroke.replace('/', ' ').split()), None)
                if translation:
                    self.stroke_mapping_text.SetLabel('"' + event.GetString() + '" already maps to "' + translation + '"')
                else:
                    self.stroke_mapping_text.SetLabel('')
            else:
                self.stroke_mapping_text.SetLabel('')
            self.GetSizer().Fit(self)
            self.GetSizer().Layout()

    def _on_translation_change(self, event):
        
        # TODO: This lookup isn't fully correct because translations aren't
        # canonicalized. Also, no full search is done to see if combos of translations
        # get the same result.

        translation = event.GetString()
        if translation:
            strokes = self.reverse_dictionary.get(translation, [])
            if strokes:
                s = '"' + translation + '" is already mapped by: ' + (' and '.join(['"' + ('/'.join(s)) + '"' for s in strokes]))
                self.translation_mapping_text.SetLabel(s)
            else:
                self.translation_mapping_text.SetLabel('')
        else:
            self.translation_mapping_text.SetLabel('')
        self.GetSizer().Fit(self)
        self.GetSizer().Layout()

    def _on_strokes_gained_focus(self, event=None):
        with self.parent.lock:
            self.parent.steno_engine._translator.set_dictionary(self._stroke_dict)
            self.cached_state = copy.deepcopy(self.parent.steno_engine._translator.get_state())
            self.parent.steno_engine._translator.clear_state()
            self.stroke_in_focus = True

    def _on_strokes_lost_focus(self, event=None):
        with self.parent.lock:
            self.parent.steno_engine._translator.set_dictionary(self.parent.real_dict)
            if self.cached_state:
                self.parent.steno_engine._translator.set_state(self.cached_state)
                self.cached_state = None

    def _on_translation_gained_focus(self, event=None):
        self.stroke_in_focus = False
        self.cached_state = copy.deepcopy(self.parent.steno_engine._translator.get_state())
        self.parent.steno_engine._translator.clear_state()

    def _on_translation_lost_focus(self, event=None):
        if self.cached_state:
            self.parent.steno_engine._translator.set_state(self.cached_state)
            self.cached_state = None

    def _on_activate(self, event):
        b = 'gained' if event.GetActive() else 'lost'
        if event.GetActive():
            self.strokes_text.SetFocus()
            # This needs to be called because when the dialog gets back focus the strokes field may already have focus and so the event will not fire.
            self._on_strokes_gained_focus()
            self.Raise()
        else:
            with self.parent.lock:
                self.parent.steno_engine._translator.set_dictionary(self.parent.real_dict)
                if self.cached_state:
                    self.parent.steno_engine._translator.set_state(self.cached_state)
                    self.cached_state = None
                
        # TODO: CLose dialog on losing focus? Or reuse same dialog every time.

    def _on_close(self, event):
        #self._on_strokes_lost_focus()
        # Clear fields on close
        #self.Destroy()
        event.Skip()
