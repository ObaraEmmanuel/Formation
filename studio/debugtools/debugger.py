# ======================================================================= #
# Copyright (C) 2022 Hoverset Group.                                      #
# ======================================================================= #

import sys
import tkinter
import logging

from hoverset.ui.widgets import *

from studio.ui.highlight import WidgetHighlighter
from studio.debugtools.preferences import Preferences
from studio.debugtools.element_pane import ElementPane
from studio.debugtools.style_pane import StylePane

from studio.resource_loader import ResourceLoader

logger = logging.getLogger("Debugger")


class Elements(PanedWindow):

    def __init__(self, master, debugger):
        super().__init__(master)
        self.config(**self.style.pane_vertical)
        self.element_pane = ElementPane(self, debugger)
        self.style_pane = StylePane(self, debugger)
        self.add(self.element_pane, minsize=100)
        self.add(self.style_pane, minsize=100)


class Console(Frame):
    pass


class Debugger(Window):
    _instance = None

    def __init__(self, master):
        self.pref = Preferences.acquire()
        Application.load_styles(self, self.pref.get("resource::theme"))
        super(Window, self).__init__(master)
        self.geometry(self.pref.get("debugger::geometry"))
        self.set_up_mousewheel()
        Debugger._instance = self
        self.master = self.root = self.position_ref = master
        self.setup_window()
        self.set_up_mousewheel()
        self.wm_transient(master)
        self.wm_title("Formation Debugger")

        self.tabs = TabView(self)
        self.tabs.pack(fill="both", expand=True)
        self.elements = Elements(self.tabs, self)
        self.tabs.add(self.elements, text="Elements")
        self.tabs.add(Frame(self.tabs, **self.style.surface), text="Variables")
        self.tabs.add(Frame(self.tabs, **self.style.surface), text="Images")
        # self.tabs.add(Frame(self.tabs, **self.style.surface), text="Variables")
        self.console = Console(self.tabs)
        self.tabs.add(self.console, text="Console")

        self.configure(**self.style.surface)
        self.is_minimized = False
        self.active_widget = None
        self.enable_hooks = True
        self._dbg_ignore = True
        self.selected = None

        self.highlighter = WidgetHighlighter(self.root, self.style)
        self.highlighter_map = {}
        for elem in self.highlighter.elements:
            setattr(elem, "_dbg_ignore", True)

        self.wm_protocol("WM_DELETE_WINDOW", self.exit)
        self._hook_creation()
        self.root.bind_all("")

    def update_selection(self, selection):
        self.selected = selection
        self.event_generate("<<WidgetSelectionChanged>>")

    def _hook_creation(self):
        _setup = tkinter.BaseWidget.__init__

        def _hook(slf, master, *args, **kwargs):
            _setup(slf, master, *args, **kwargs)
            if slf.master.winfo_toplevel() != self and slf.master != self and not getattr(slf, "_dbg_ignore", False) and self.enable_hooks:
                self.active_widget = slf
                self.event_generate("<<WidgetCreated>>")

        setattr(tkinter.BaseWidget, '__init__', _hook)

    def _hook_destroy(self, widget):
        destroy = widget.destroy

        def _hook():
            if self.enable_hooks:
                self.active_widget = widget
                self.event_generate("<<WidgetDeleted>>")
            return destroy()

        setattr(widget, "destroy", _hook)

    def _hook_widget_conf(self, widget):
        widget_conf = widget.configure

        def _hook(cnf=None, **kw):
            ret = widget_conf(cnf, **kw)
            if (cnf or kw) and self.enable_hooks:
                self.active_widget = widget
                self.event_generate("<<WidgetModified>>")
            return ret

        setattr(widget, "configure", _hook)
        setattr(widget, "config", _hook)

    def highlight_widget(self, widget):
        if widget is None:
            self.highlighter.clear()
        else:
            self.highlighter.highlight(widget)

    def hook_widget(self, widget):
        if getattr(widget, "dbg_ignore", False):
            return
        self._hook_widget_conf(widget)
        self._hook_destroy(widget)
        setattr(widget, "_dbg_hooked", True)

    def destroy(self) -> None:
        # save window position
        self.pref.set("debugger::geometry", self.geometry())
        self.enable_hooks = False
        super().destroy()

    def exit(self):
        self.enable_hooks = False
        self.root.destroy()

    @classmethod
    def acquire(cls, root):
        if not cls._instance:
            cls._instance = Debugger(root)
        return cls._instance

    @classmethod
    def _root(cls):
        if not tkinter._support_default_root:
            raise RuntimeError('Default root not supported, cannot hook debugger')
        return tkinter._default_root

    @classmethod
    def _hook(cls):
        # store reference to actual mainloop
        _default_mainloop = tkinter.Misc.mainloop
        _default_mainloop_func = tkinter.mainloop

        def _mainloop_func(n=0):
            tkinter.Misc.mainloop = _default_mainloop
            tkinter.mainloop = _default_mainloop_func
            cls.acquire(cls._root())
            _default_mainloop_func(n)

        def _mainloop(root, n=0):
            # restore actual mainloop
            tkinter.Misc.mainloop = _default_mainloop
            tkinter.mainloop = _default_mainloop_func
            cls.acquire(root)
            # run actual mainloop
            _default_mainloop(root, n)

        # hook into mainloop
        tkinter.Misc.mainloop = _mainloop
        tkinter.mainloop = _mainloop_func

    @classmethod
    def run(cls, path=None):
        if path is None:
            if len(sys.argv) > 1:
                path = sys.argv[1]
                # remove ourself from sys args
                # just incase the program reads sys args
                sys.argv.pop(0)
            else:
                return
        ResourceLoader.load(Preferences.acquire())
        cls._hook()
        with open(path) as file:
            code = compile(file.read(), path, 'exec')
        exec(code, {'__name__': '__main__'})


if __name__ == '__main__':
    Debugger.run()
