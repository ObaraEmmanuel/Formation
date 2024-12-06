# ======================================================================= #
# Copyright (C) 2024 Hoverset Group.                                      #
# ======================================================================= #
_global_freeze = dict(globals())

import sys
import logging
import os
import tkinter
from multiprocessing.connection import Listener
import threading
import subprocess
import atexit
import queue
import code

from studio.ui.highlight import WidgetHighlighter
from studio.debugtools.defs import Message, marshal, RemoteEvent, unmarshal
from studio.debugtools.common import extract_base_class, get_logging_level
from studio.debugtools.preferences import Preferences


class _BypassedLogger:
    """
    A rudimentary logger that writes directly to stdout and stderr. This is
    necessary to avoid recursion errors when piping logs from the app to IPC
    """
    def __init__(self, name, level, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr
        self.level = level
        self.name = name

    def _log(self, msg, level):
        if level >= self.level:
            print(msg, file=self.stdout, flush=True)

    def debug(self, msg):
        self._log(f"DEBUG:{self.name}:{msg}", logging.DEBUG)

    def error(self, msg):
        self._log(f"ERROR:{self.name}:{msg}", logging.ERROR)

    def info(self, msg):
        self._log(f"INFO:{self.name}:{msg}", logging.INFO)

    def warning(self, msg):
        self._log(f"WARNING:{self.name}:{msg}", logging.WARNING)


logger = _BypassedLogger("[HOOK]", get_logging_level(), sys.stdout, sys.stderr)


class RemotePipe:

    def __init__(self, hook, tag):
        self.hook = hook
        self.tag = tag
        self.buffer = queue.Queue()
        self.reading = False

    def _call(self, method, *args):
        self.hook.transmit(Message(
            "CONSOLE",
            payload=marshal({"tag": self.tag, "action": method, "args": args})
        ))

    def write(self, data):
        self._call("write", data)

    def _write(self, data):
        self.buffer.put(data)

    def flush(self):
        pass

    def clear(self):
        self._call("clear")

    def readline(self):
        self.hook.transmit(
            Message("CONSOLE", payload=marshal({"note": "START_STDIN_READ"}))
        )
        line = self.buffer.get()
        self.hook.transmit(
            Message("CONSOLE", payload=marshal({"note": "STOP_STDIN_READ"}))
        )
        return line


class DebuggerAPI:
    """
    A class that provides an interface for interacting with the debugger
    """

    __slots__ = ("__hook",)

    def __init__(self, hook):
        self.__hook = hook

    @property
    def selection(self) -> list:
        """
        Get the currently selected widgets in the debugger as a list
        """
        return self.__hook.selection

    @property
    def selected(self) -> tkinter.Widget:
        """
        Get the first selected widget in the debugger. Useful when only one
        widget is selected
        """
        if self.__hook.selection:
            return self.__hook.selection[0]

    @property
    def root(self) -> tkinter.Tk:
        """
        Get the root widget of the debugger
        """
        return self.__hook.root


class DebuggerHook:

    def __init__(self, path=None):
        pref = Preferences.acquire()
        self.path = path
        self.root = None
        self.active_widget = None
        self.enable_hooks = True
        self._ignore = set()
        self.listener = Listener(
            ('localhost', 6999), authkey=pref.get("IPC::authkey")
        )
        self._handle_map = {}
        self.styles = None
        self._allow_hover = False
        self._handle = None
        self.last_compiled = None
        self.pipes = {
            "stdout": RemotePipe(self, "stdout"),
            "stderr": RemotePipe(self, "stderr"),
            "stdin": RemotePipe(self, "stdin")
        }
        self.orig_stdout, self.orig_stderr, self.orig_stdin = (
            sys.stdout, sys.stderr, sys.stdin
        )
        sys.stdout = self.pipes["stdout"]
        sys.stderr = self.pipes["stderr"]
        sys.stdin = self.pipes["stdin"]
        self.debugger_api = DebuggerAPI(self)
        self.shell = code.InteractiveConsole({"debugger": self.debugger_api})
        self._stream_clients = []
        self._server_clients = []
        self.selection = []
        atexit.register(self.terminate)

    @property
    def allow_hover(self):
        return self._allow_hover

    @allow_hover.setter
    def allow_hover(self, value):
        self._allow_hover = value
        if not value:
            self._clear_handle()

    def get_handle(self, widget):
        toplevel = widget.winfo_toplevel()
        if toplevel not in self._handle_map:
            self.enable_hooks = False
            self._handle_map[toplevel] = highlighter = WidgetHighlighter(
                toplevel, self.styles
            )
            for elem in highlighter.elements:
                self._ignore.add(elem)
            self.enable_hooks = True
        return self._handle_map[toplevel]

    @classmethod
    def _root(cls):
        if not tkinter._support_default_root:
            raise RuntimeError('Default root not supported, cannot hook debugger')
        return tkinter._default_root

    def acquire_debugger(self):
        threading.Thread(target=self.server, daemon=True).start()
        subprocess.Popen(
            [sys.executable, "-m", "studio.debugtools"],
            stdout=self.orig_stdout,
            stderr=self.orig_stderr,
            stdin=self.orig_stdin
        )
        tkinter.Misc.bind_all(self.root, "<Motion>", self.on_motion)
        tkinter.Misc.bind_all(self.root, "<Button-1>", self.on_widget_tap)
        tkinter.Misc.bind_all(self.root, "<Button-3>", self.on_widget_tap)
        tkinter.Misc.bind_all(self.root, "<Map>", self.on_widget_map)
        tkinter.Misc.bind_all(self.root, "<Unmap>", self.on_widget_unmap)

    def _clear_handle(self):
        if self._handle:
            try:
                self._handle.clear()
            except tkinter.TclError:
                pass
        self._handle = None

    def on_motion(self, event):
        if not self.allow_hover:
            return
        widget = event.widget
        if widget in self._ignore:
            return
        handle = self.get_handle(widget)
        if handle != self._handle:
            self._clear_handle()
            self._handle = handle
        self._handle.highlight(widget)

    def on_widget_tap(self, event):
        if not self.allow_hover:
            return
        widget = event.widget
        if widget in self._ignore:
            return
        self._clear_handle()
        self.push_event("<<SelectionChanged>>", widget, event)

    def on_widget_map(self, event):
        widget = event.widget
        if widget in self._ignore:
            return
        self.push_event("<<WidgetMapped>>", widget, event)

    def on_widget_unmap(self, event):
        widget = event.widget
        if widget in self._ignore:
            return
        self.push_event("<<WidgetUnmapped>>", widget, event)

    def widget_from_message(self, message):
        return self.root.nametowidget(message.id)

    def push_event(self, ev, widget=None, data=None):
        if data:
            data = RemoteEvent(data)
        self.transmit(Message(
            "EVENT",
            payload=marshal({"event": ev, "widget": widget, "data": data})
        ))

    def transmit(self, msg):
        logger.debug(f"[STRM]: {msg}")
        remove = []
        for client in self._stream_clients:
            try:
                client.send(msg)
            except ConnectionResetError:
                remove.append(client)

        for client in remove:
            self._stream_clients.remove(client)

    def sub_server(self, conn):
        logger.debug("[MISC]: Subserver started")
        while True:
            msg = conn.recv()
            # logger.debug(f"Sub server received message: {msg}")
            if msg == "TERMINATE":
                self.exit()
                break
            if isinstance(msg, Message):
                msg.payload = unmarshal(msg.payload, self)
            try:
                self.handle_msg(msg, conn)
            except Exception as e:
                conn.send(e)

    def server(self):
        while True:
            conn = self.listener.accept()
            msg = conn.recv()
            if msg == "STREAM":
                self._stream_clients.append(conn)
                logger.debug("[MISC]: Stream client connected")
            elif msg == "SERVER":
                self._server_clients.append(conn)
                logger.debug("[MISC]: Server client connected")
                threading.Thread(
                    target=self.sub_server, args=(conn,), daemon=True
                ).start()
            else:
                conn.close()

    def access(self, obj, msg, conn):
        # method runners, property setters and getters
        msg.payload = unmarshal(msg.payload, self)
        if "meth" in msg.payload:
            conn.send(marshal(
                getattr(obj, msg.payload["meth"])(
                    *msg.payload.get("args", []),
                    **msg.payload.get("kwargs", {})
                )
            ))
        elif "get" in msg.payload:
            conn.send(marshal(getattr(obj, msg.payload["get"], None)))
        elif "set" in msg.payload:
            setattr(obj, msg.payload["set"], msg.payload["value"])

    def handle_msg(self, msg, conn):
        if not hasattr(msg, "key"):
            return
        if msg.key == "WIDGET":
            widget = self.root.nametowidget(msg.payload["id"])
            self.access(widget, msg, conn)
        if msg.key == "CONSOLE":
            pipe = self.pipes[msg.payload["tag"]]
            self.access(pipe, msg, conn)
        if msg.key == "HOOK":
            self.access(self, msg, conn)

    def console_compile(self, command):
        try:
            result = code.compile_command(command)
            self.last_compiled = result
            result = result is not None
        except Exception as e:
            result = e
        return result

    def console_run(self):
        if not self.last_compiled:
            return

        def run_command(last_compiled):
            try:
                self.shell.runcode(last_compiled)
            except SystemExit:
                self.root.after(0, self.exit)

            self.transmit(
                Message("CONSOLE", payload={"note": "COMMAND_COMPLETE"})
            )

        threading.Thread(target=run_command, args=(self.last_compiled,)).start()
        self.last_compiled = None

    def exit(self):
        self.enable_hooks = False
        self.root.quit()
        self.terminate()

    def terminate(self):
        self.transmit("TERMINATE")

        for client in self._server_clients:
            client.close()

    def extract_base_class(self, widget):
        return extract_base_class(widget)

    def hook_widget(self, widget):
        if widget in self._ignore:
            return
        self._hook_widget_conf(widget)
        self._hook_destroy(widget)
        setattr(widget, "_dbg_hooked", True)

    def _hook_creation(self):
        _setup = tkinter.BaseWidget.__init__

        def _hook(slf, master, *args, **kwargs):
            _setup(slf, master, *args, **kwargs)
            if slf not in self._ignore and self.enable_hooks:
                self.hook_widget(slf)
                self.push_event("<<WidgetCreated>>", slf)

        setattr(tkinter.BaseWidget, '__init__', _hook)

    def _hook_destroy(self, widget):
        destroy = widget.destroy

        def _hook():
            if widget == self.root:
                # Root is being deleted so stop emitting events
                self.enable_hooks = False
            if self.enable_hooks:
                self.push_event("<<WidgetDeleted>>", widget)
            return destroy()

        setattr(widget, "destroy", _hook)

    def _hook_widget_conf(self, widget):
        widget_conf = widget.configure
        # should ideally be the same but hoverset overrides config
        # making it necessary to hook both Separately
        widget_conf_c = widget.config

        def _hook(*args, **kw):
            ret = widget_conf(*args, **kw)
            if (args or kw) and self.enable_hooks:
                self.push_event("<<WidgetModified>>", widget)
            return ret

        def _hook_c(*args, **kw):
            ret = widget_conf_c(*args, **kw)
            if (args or kw) and self.enable_hooks:
                self.push_event("<<WidgetModified>>", widget)
            return ret

        setattr(widget, "configure", _hook)
        setattr(widget, "config", _hook_c)

    def hook(self):
        # store reference to actual mainloop
        _default_mainloop = tkinter.Misc.mainloop
        _default_mainloop_func = tkinter.mainloop

        def _mainloop_func(n=0):
            tkinter.Misc.mainloop = _default_mainloop
            tkinter.mainloop = _default_mainloop_func
            self.root = self._root()
            self.acquire_debugger()
            _default_mainloop_func(n)

        def _mainloop(root, n=0):
            # restore actual mainloop
            tkinter.Misc.mainloop = _default_mainloop
            tkinter.mainloop = _default_mainloop_func
            self.root = self._root()
            self.acquire_debugger()
            # run actual mainloop
            _default_mainloop(root, n)

        # hook into mainloop
        tkinter.Misc.mainloop = _mainloop
        tkinter.mainloop = _mainloop_func

    def run(self):
        if self.path is None:
            if len(sys.argv) > 1:
                self.path = sys.argv[1]
                # remove ourselves from sys args
                # just incase the program reads sys args
                sys.argv.pop(0)
            else:
                logger.error("No python file supplied")
                return
        self.hook()
        self._hook_creation()
        with open(self.path) as file:
            code = compile(file.read(), self.path, 'exec')

        sys.path.append(os.path.dirname(self.path))
        # Ensure hooked application thinks it is running as __main__
        _global_freeze.update({"__name__": "__main__", "__file__": self.path})
        exec(code, _global_freeze)


def main():
    DebuggerHook().run()


if __name__ == "__main__":
    main()
