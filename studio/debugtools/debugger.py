# ======================================================================= #
# Copyright (C) 2022 Hoverset Group.                                      #
# ======================================================================= #

import os
import logging
import subprocess
import threading
from multiprocessing.connection import Client

from hoverset.data.images import load_tk_image
from hoverset.data.utils import get_resource_path
from hoverset.platform import platform_is, WINDOWS
from hoverset.ui.widgets import *

from studio.debugtools.preferences import Preferences
from studio.debugtools.element_pane import ElementPane
from studio.debugtools.style_pane import StylePane
from studio.debugtools.selection import DebugSelection
from studio.debugtools.console import Console
from studio.debugtools.defs import RemoteWidget, Message, unmarshal, RemoteEvent, marshal

from studio.resource_loader import ResourceLoader
from studio.i18n import _
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


class Debugger(Application):
    _instance = None

    def __init__(self):
        self.pref = Preferences.acquire()
        self.load_styles(self.pref.get("resource::theme"))
        super().__init__()
        _init_tkdnd(self)
        self.geometry(self.pref.get("debugger::geometry"))
        Debugger._instance = self
        self._widget_map = {}
        self._server_client = None
        self.start_server_client()
        self.root = self.transmit(Message("HOOK", payload={"get": "root"}), response=True)
        self.wm_title("Formation Debugger")
        if platform_is(WINDOWS):
            ICON_PATH = get_resource_path(studio, "resources/images/formation.ico")
        else:
            ICON_PATH = get_resource_path(studio, "resources/images/formation_icon.png")
        icon_image = load_tk_image(ICON_PATH)
        self.wm_iconphoto(False, icon_image)

        self.tabs = TabView(self)
        self.tabs.pack(fill="both", expand=True)
        self.elements = Elements(self.tabs, self)
        self.tabs.add(self.elements, text=_("Elements"))
        self.console = Console(self.tabs, self.exit, self)
        self.tabs.add(self.console, text=_("Console"))

        self.configure(**self.style.surface)
        self.active_widget = None
        self._selection = DebugSelection(self)

        self._stream_client = None
        threading.Thread(target=self.stream_client).start()

        self.wm_protocol("WM_DELETE_WINDOW", self.exit)
        self.bind("<<SelectionChanged>>", self.on_selection_changed, True)

    def start_server_client(self):
        logging.debug("Starting server client...")
        self._server_client = Client(("localhost", 6999), authkey=b'studio-debugger')
        self._server_client.send("SERVER")
        self._server_client.send(Message("HOOK", payload={"set": "styles", "value": self.style}))

    def stream_client(self):
        logging.debug("Starting stream client...")
        self._stream_client = Client(("localhost", 6999), authkey=b'studio-debugger')
        self._stream_client.send("STREAM")
        while True:
            try:
                msg = self._stream_client.recv()
            except ConnectionAbortedError:
                break
            if msg == "TERMINATE":
                self.exit()
                break
            if hasattr(msg, "payload"):
                msg.payload = unmarshal(msg.payload, self)
            self.handle_msg(msg)

    def close_clients(self):
        if self._server_client:
            self._server_client.close()
            self._server_client = None
        if self._stream_client:
            self._stream_client.close()
            self._stream_client = None

    def transmit(self, msg, response=False):
        if not self._server_client:
            return
        if isinstance(msg, Message):
            msg.payload = marshal(msg.payload)
        self._server_client.send(msg)
        if response:
            result = self._server_client.recv()
            logger.debug("Received response: %s", result)
            if isinstance(result, Exception):
                raise result
            return unmarshal(result, self)

    def handle_msg(self, msg):
        if not hasattr(msg, "key"):
            return
        if msg.key == "EVENT":
            event = msg.payload["event"]
            widget = msg.payload["widget"]
            if msg.payload["data"]:
                msg.payload["data"] = RemoteEvent(msg.payload["data"])
            suppress = False
            if event == "<<WidgetMapped>>" and widget._dbg_node:
                widget._dbg_node.on_map()
            if event == "<<WidgetUnmapped>>" and widget._dbg_node:
                widget._dbg_node.on_unmap()
            if event == "<<WidgetDeleted>>":
                widget.deleted = True
            if event == "<<SelectionChanged>>":
                self.elements.element_pane.on_widget_tap(widget, msg.payload["data"])
                suppress = True

            if not suppress:
                self.active_widget = widget
                self.event_generate(event)
        if msg.key == "CONSOLE":
            self.console.handle_msg(msg.payload)

    def set_hover(self, value):
        self.transmit(Message("HOOK", payload={"set": "allow_hover", "value": value}))

    def widget_from_message(self, message):
        if message.id in self._widget_map:
            return self._widget_map[message.id]
        self._widget_map[message.id] = RemoteWidget(message.id, self)
        return self._widget_map[message.id]

    @property
    def selection(self):
        return self._selection

    def on_selection_changed(self, _):
        self.transmit(Message("HOOK", payload={"set": "selection", "value": list(self.selection)}))

    def highlight_widget(self, widget):
        pass

    def destroy(self) -> None:
        # save window position
        self.pref.set("debugger::geometry", self.geometry())
        self.enable_hooks = False
        super().destroy()

    def exit(self):
        try:
            self.transmit("TERMINATE")
            self.close_clients()
            self.destroy()
        finally:
            # Exit forcefully
            os._exit(os.EX_OK)

    @classmethod
    def run_process(cls, path) -> subprocess.Popen:
        return subprocess.Popen(["formation-dbg", path])


def main():
    logging.basicConfig(level=logging.INFO)
    pref = Preferences.acquire()
    ResourceLoader.load(pref)
    Debugger().mainloop()


if __name__ == '__main__':
    main()
