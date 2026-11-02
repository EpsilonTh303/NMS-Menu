"""Keep hidden Tk controllers out of Qt's native Windows event dispatch.

Only explicit Tcl calls may invoke Python Tk commands. Native Tk bindings,
scroll callbacks and timers would otherwise run from Qt's Windows dispatcher
without _tkinter's saved thread state (CPython #84256).
"""
import sys
import tkinter as tk
from PySide6 import QtCore


class ControllerEvents:
    def __init__(self, root, owner):
        self.root, self.owner = root, owner
        self.timers = {}
        self.serial = 0
        self.bindings = {}
        self.selections = {}
        self.original_destroy = root.destroy
        root.after = self.after
        root.after_cancel = self.cancel
        root.destroy = self.destroy

    def after(self, milliseconds, callback=None, *args):
        if callback is None:
            raise ValueError('The Qt controller requires a scheduled callback')
        self.serial += 1
        identifier = f'qt-after-{self.serial}'
        timer = QtCore.QTimer(self.owner)
        timer.setSingleShot(True)
        self.timers[identifier] = timer

        def invoke():
            self.timers.pop(identifier, None)
            timer.deleteLater()
            try:
                callback(*args)
            except Exception:
                self.root.report_callback_exception(*sys.exc_info())

        timer.timeout.connect(invoke)
        timer.start(0 if milliseconds == 'idle' else max(0, int(milliseconds)))
        return identifier

    def cancel(self, identifier):
        timer = self.timers.pop(identifier, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def cancel_all(self):
        for identifier in list(self.timers):
            self.cancel(identifier)

    def destroy(self):
        self.cancel_all()
        self.original_destroy()

    def adapt(self, widget):
        if widget in self.bindings:
            return
        scripts = {}
        for event in widget.bind():
            scripts[event] = widget.bind(event)
            widget.tk.call('bind', widget._w, event, '')
        self.bindings[widget] = scripts
        if isinstance(widget, tk.Tk):
            widget.protocol('WM_DELETE_WINDOW', '')
        # Hidden scrollbars need no geometry callbacks; Qt renders its own.
        options = widget.keys()
        for option in ('xscrollcommand', 'yscrollcommand'):
            if option in options:
                widget.configure(**{option: ''})
        widget.event_generate = lambda event, **kwargs: self.dispatch(widget, event, **kwargs)
        for child in widget.winfo_children():
            self.adapt(child)

    def dispatch(self, widget, event, **kwargs):
        if event == '<<TreeviewSelect>>':
            self.selections[widget] = widget.selection()
        script = self.bindings.get(widget, {}).get(event)
        if not script:
            return tk.Misc.event_generate(widget, event, **kwargs)
        # Restore a binding only for this synchronous Tcl call. No native
        # event loop runs while a Python callback is attached to the widget.
        widget.tk.call('bind', widget._w, event, script)
        try:
            kwargs['when'] = 'now'
            return tk.Misc.event_generate(widget, event, **kwargs)
        finally:
            widget.tk.call('bind', widget._w, event, '')

    def refresh_selections(self):
        for widget, scripts in self.bindings.items():
            if '<<TreeviewSelect>>' in scripts:
                selected = widget.selection()
                previous = self.selections.get(widget, ())
                self.selections[widget] = selected
                if selected != previous:
                    self.dispatch(widget, '<<TreeviewSelect>>')
