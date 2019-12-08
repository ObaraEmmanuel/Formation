import shelve
import tkinter.ttk as ttk
from copy import copy
from threading import Thread
from tkinter import *

from . import components
from . import dialogs
from .widgets import Grid, ContextMenu
from hoverset.ui.icons import get_icon
import hoverset.ui.widgets as widgets
from hoverset.apps import Categories, BaseApp

MAX_GRID_WIDTH, MAX_GRID_HEIGHT = 20, 10


# noinspection PyArgumentList
class App(BaseApp):
    icon = get_icon("emoji")
    NAME = "Unicode Viewer"
    CATEGORY = Categories.IMAGE_PROCESSING

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.window = master.window
        self.nav = widgets.Frame(self, bg="#5a5a5a")
        self.nav.place(x=0, y=0, relwidth=1, relheight=0.1)
        self.body = widgets.Frame(self)
        self.body.place(rely=0.101, x=0, relwidth=1, relheight=0.9)
        self.body.bind('<Leave>', lambda ev: self.deactivate_grid())
        self.body.bind('<Button-3>', lambda ev: print('context menu requested.'))
        self.context_menu = ContextMenu()
        self.context_menu.load_actions(
            ("\ue923", "Copy unicode", lambda: self.active_grid.copy(0)),
            ("\ue923", "Copy code point", lambda: self.active_grid.copy(2)),
            ("\ue923", "Copy hexadecimal scalar", lambda: self.active_grid.copy(1)),
            ('separator',),
            ("\ue7a9", "Save as image", lambda: dialogs.SaveAsImage(self)),
            ("\ue735", "Add to favorites", lambda: self.toggle_from_favourites()),
            ("\ue946", "Unicode info", lambda: dialogs.UnicodeInfo(self))
        )
        self._size = (MAX_GRID_WIDTH, MAX_GRID_HEIGHT)
        self.grids = []
        self.grid_cluster = []
        self.init_grids()
        self.active_grid = None
        # Plugin components here. Your component has to inherit the Component class
        # Components not placed here will not be rendered or receive broadcast events
        self.components = [
            components.Swipe(self),
            components.RenderRangeControl(self),
            components.GridTracker(self),
            components.RenderSizeControl(self),
            components.FontSelector(self),
            components.FavouritesManager(self)
        ]
        self._from = 0
        self.render_thread = None
        self.render(59422)
        self.size = (10, 5)
        self.style = ttk.Style(self)
        self.style.configure('Horizontal.TScale', background='#5a5a5a')
        self.show()

    @property
    def size(self) -> (int, int):
        return self._size

    @size.setter
    def size(self, value: (int, int)):
        if value[0] > MAX_GRID_WIDTH:
            raise ValueError("Width set exceeds maximum: {}".format(MAX_GRID_WIDTH))
        elif value[1] > MAX_GRID_HEIGHT:
            raise ValueError("Height set exceeds maximum: {}".format(MAX_GRID_HEIGHT))
        if self.size == value:
            # This condition prevents dangerous recursions that may be
            return
        self._size = value
        w_lower_bound = (MAX_GRID_WIDTH - value[0]) // 2
        h_lower_bound = (MAX_GRID_HEIGHT - value[1]) // 2
        self.grid_cluster = []
        for column in self.grids[w_lower_bound: w_lower_bound + value[0]]:
            for grid in column[h_lower_bound: h_lower_bound + value[1]]:
                self.grid_cluster.append(grid)
        self.render(self._from)
        for component in self.components:
            component.size_changed()

    def clear_grids(self):
        for column in self.grids:
            for grid in column:
                grid.set(None)

    def init_grids(self):
        w_ratio = 1 / MAX_GRID_WIDTH
        h_ratio = 1 / MAX_GRID_HEIGHT
        for i in range(MAX_GRID_WIDTH):
            column = []
            for j in range(MAX_GRID_HEIGHT):
                grid = Grid(self)
                column.append(grid)
                self.grid_cluster.append(grid)
                grid.place(relx=i * w_ratio, rely=j * h_ratio, relwidth=w_ratio, relheight=h_ratio)
            self.grids.append(column)

    @property
    def current_range(self) -> [int, int]:
        return [self._from, self._from + self.size[0] * self.size[1]]

    def _render(self, from_: int, prev_thread: Thread = None) -> None:
        if from_ > 0xffff:
            return
        if prev_thread:
            prev_thread.join()
        self._from = from_
        self.propagate_change()
        self.clear_grids()
        cluster = copy(self.grid_cluster)
        if self.active_grid:
            self.active_grid.unlock()
        to = from_ + self.size[0] * self.size[1]
        # Check whether value is above
        to = to if to <= 0xffff else 0xffff
        for i in range(from_, to):
            cluster[i - from_].set(i)
        if to == 0xffff:
            fracture_point = 0xffff - from_
            for j in range(fracture_point, self.size[0] * self.size[1]):
                cluster[j].set(None)

    def propagate_change(self):
        for component in self.components:
            component.receive_range()

    def activate_grid(self, grid: Grid):
        for component in self.components:
            component.receive_grid(grid)

    def deactivate_grid(self):
        for component in self.components:
            component.receive_grid(self.active_grid)

    def render(self, from_: int) -> None:
        self.render_thread = Thread(target=self._render, args=(from_, self.render_thread))
        self.render_thread.start()

    @staticmethod
    def get_favourites():
        # Ensure that favourites key exists in data
        descriptor = shelve.open("data")
        if not descriptor.get("favourites"):
            descriptor['favourites'] = []
            descriptor.sync()
        return descriptor

    @staticmethod
    def get_shelve():
        descriptor = shelve.open("data")
        return descriptor

    def favourites_as_list(self):
        with self.get_favourites() as data:
            return list(data["favourites"])

    def set_favourites(self, value: list) -> None:
        with self.get_favourites() as data:
            data["favourites"] = value

    def remove_favourites(self):
        # Completely rip away the favourites key
        with App.get_favourites() as data:
            del data["favourites"]

    def toggle_from_favourites(self) -> None:
        grid = self.active_grid
        with grid.app.get_favourites() as data:
            if (grid.code_point, grid.font) in data["favourites"]:
                fav = data["favourites"]
                fav.remove((grid.code_point, grid.font))
                data["favourites"] = fav
            else:
                data["favourites"] += [(int(grid.text, 16), grid.font)]

    def request_context_menu(self, event):
        if (self.active_grid.code_point, self.active_grid.font) in self.favourites_as_list():
            self.context_menu.entryconfigure(5, label="\ue8d9   Remove from favourites")
        else:
            self.context_menu.entryconfigure(5, label="\ue735   Add to favourites")
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
