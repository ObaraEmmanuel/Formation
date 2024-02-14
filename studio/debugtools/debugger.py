# ======================================================================= #
# Copyright (C) 2022 Hoverset Group.                                      #
# ======================================================================= #
import os

_global_freeze = dict(globals())

import sys
import tkinter
import logging
import subprocess

from hoverset.data.images import load_tk_image
from hoverset.data.utils import get_resource_path
from hoverset.ui.widgets import *

from studio.ui.highlight import WidgetHighlighter
from studio.debugtools.preferences import Preferences
from studio.debugtools.element_pane import ElementPane
from studio.debugtools.style_pane import StylePane
from studio.debugtools.selection import DebugSelection
from studio.debugtools.console import ConsolePane

from studio.resource_loader import ResourceLoader
import studio

from tkinterDnD.tk import _init_tkdnd

logger = logging.getLogger("Debugger")


class Elements(PanedWindow):

    def __init__(self, master, debugger):
        super().__init__(master)
        self.config(**self.style.pane_vertical)
        self.element_pane = ElementPane(self, debugger)
        self.style_pane = StylePane(self, debugger)
        self.add(self.element_pane, minsize=100)
        self.add(self.style_pane, minsize=100)


class DebuggerAPI:
    """
    A class that provides an interface for interacting with the debugger
    """

    __slots__ = ("__debugger",)

    def __init__(self, debugger):
        self.__debugger = debugger

    @property
    def selection(self) -> list:
        """
        Get the currently selected widgets in the debugger as a list
        """
        return self.__debugger.selection

    @property
    def selected(self) -> tkinter.Widget:
        """
        Get the first selected widget in the debugger. Useful when only one widget is selected
        """
        if self.__debugger.selection:
            return self.__debugger.selection[0]


class Debugger(Window):
    _instance = None

    def __init__(self, master):
        self.pref = Preferences.acquire()
        Application.load_styles(self, self.pref.get("resource::theme"))
        super(Window, self).__init__(master)
        _init_tkdnd(self)
        self.geometry(self.pref.get("debugger::geometry"))
        self.set_up_mousewheel()
        Debugger._instance = self
        self.master = self.root = self.position_ref = master
        self.setup_window()
        self.set_up_mousewheel()
        self.wm_transient(master)
        self.wm_title("Formation Debugger")
        icon_image = load_tk_image(get_resource_path(studio, "resources/images/formation_icon.png"))
        self.wm_iconphoto(False, icon_image)

        self.tabs = TabView(self)
        self.tabs.pack(fill="both", expand=True)
        self.elements = Elements(self.tabs, self)
        self.tabs.add(self.elements, text="Elements")
        self.debug_api = DebuggerAPI(self)
        self._locals = {"debugger": self.debug_api}
        self.console = ConsolePane(self.tabs, self._locals, self.exit)
        self.tabs.add(self.console, text="Console")

        self.configure(**self.style.surface)
        self.is_minimized = False
        self.active_widget = None
        self.enable_hooks = True
        self._dbg_ignore = True
        self._selection = DebugSelection(self)

        self.highlighter = WidgetHighlighter(self.root, self.style)
        self.highlighter_map = {}
        for elem in self.highlighter.elements:
            setattr(elem, "_dbg_ignore", True)

        self.wm_protocol("WM_DELETE_WINDOW", self.exit)
        self._hook_creation()
        self.root.bind_all("")

    @property
    def selection(self):
        return self._selection

    def update_selection(self, selection):
        self.selected = selection
        self.event_generate("<<SelectionChanged>>")

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
        try:
            self.enable_hooks = False
            self.root.destroy()
        finally:
            # Exit forcefully
            os._exit(os.EX_OK)

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
                # remove ourselves from sys args
                # just incase the program reads sys args
                sys.argv.pop(0)
            else:
                logger.error("No python file supplied")
                return
        ResourceLoader.load(Preferences.acquire())
        cls._hook()
        with open(path) as file:
            code = compile(file.read(), path, 'exec')

        sys.path.append(os.path.dirname(path))
        # Ensure hooked application thinks it is running as __main__
        _global_freeze.update({"__name__": "__main__", "__file__": path})
        exec(code, _global_freeze)

    @classmethod
    def run_process(cls, path) -> subprocess.Popen:
        return subprocess.Popen(["formation-dbg", path])


def main():
    Debugger.run()


if __name__ == '__main__':
    main()
