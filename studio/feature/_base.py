import logging
import copy
from tkinter import StringVar, BooleanVar, TkVersion

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import Frame, Label, Button, MenuButton, PanedWindow
from hoverset.ui.menu import EnableIf
from studio.ui.geometry import absolute_position
from studio.ui.widgets import SearchBar
from studio.preferences import Preferences

pref = Preferences.acquire()


class BaseFeature(Frame):
    _instance = None
    name = "Feature"
    pane = None
    bar = None
    icon = "blank"
    _view_mode = None
    _transparency_flag = None
    _side = None
    rec = (20, 20, 300, 300)  # Default window mode position
    _defaults = {
        "mode": "docked",
        "inactive_transparency": False,
        "position": "left",
        "visible": True,
        "side": "left",
        "pane": {
            "height": 300,
            "index": 1000,  # setting 1000 allows the feature pane to pick an index
        },
        "pos": {
            "initialized": False,
            "x": 20,
            "y": 20,
            "width": 200,
            "height": 200,
        }
    }

    @classmethod
    def update_defaults(cls):
        path = "features::{}".format(cls.name)
        if not pref.exists(path):
            pref.set(path, copy.deepcopy(cls._defaults))
        else:
            pref.update_defaults(path, copy.deepcopy(cls._defaults))

    def __init__(self, master, studio=None, **cnf):
        super().__init__(master, **cnf)
        self.update_defaults()
        self.__class__._instance = self
        if not self.__class__._view_mode:
            self.__class__._view_mode = StringVar(None, self.get_pref('mode'))
            self.__class__._transparency_flag = t = BooleanVar(None, self.get_pref('inactive_transparency'))
            self.__class__._side = StringVar(None, self.get_pref('side'))
            self.is_visible = BooleanVar(None, self.get_pref('visible'))
            t.trace_add("write", lambda *_: self.set_pref('inactive_transparency', t.get()))
        self.studio = studio
        self._header = Frame(self, **self.style.surface, **self.style.highlight_dim, height=30)
        self._header.pack(side="top", fill="x")
        self._header.pack_propagate(0)
        self._header.allow_drag = True
        Label(self._header, **self.style.text_accent, text=self.name).pack(side="left")
        self._min = Button(self._header, image=get_icon_image("close", 15, 15), **self.style.button, width=25,
                           height=25)
        self._min.pack(side="right")
        self._min.on_click(self.minimize)
        self._pref = MenuButton(self._header, **self.style.button)
        self._pref.configure(image=get_icon_image("settings", 15, 15))
        self._pref.pack(side="right")
        self._pref.tooltip("Options")
        self._search_bar = SearchBar(self._header, height=20)
        self._search_bar.on_query_clear(self.on_search_clear)
        self._search_bar.on_query_change(self.on_search_query)
        menu = self.make_menu((
            ("cascade", "View Mode", None, None, {"menu": (
                ("radiobutton", "Docked", None, self.open_as_docked, {"variable": self._view_mode, "value": "docked"}),
                ("radiobutton", "Window", None, self.open_as_window, {"variable": self._view_mode, "value": "window"}),
            )}),
            ("cascade", "Position", None, None, {"menu": (
                ("radiobutton", "Left", None, lambda: self.reposition("left"),
                 {"variable": self._side, "value": "left"}),
                ("radiobutton", "Right", None, lambda: self.reposition("right"),
                 {"variable": self._side, "value": "right"}),
            )}),
            EnableIf(lambda: self._view_mode.get() == 'window',
                     ("cascade", "Window options", None, None, {"menu": (
                         (
                             "checkbutton", "Transparent when inactive", None, None,
                             {"variable": self._transparency_flag}),
                     )})),
            ("command", "Close", get_icon_image("close", 14, 14), self.minimize, {}),
            ("separator",),
            *self.create_menu()
        ), self._pref)
        self._pref.config(menu=menu)
        # self._pref.on_click(self.minimize)
        self.config(**self.style.surface)
        self.indicator = None
        self.window_handle = None
        self.on_focus(self._on_focus_get)
        self.on_focus_lost(self._on_focus_release)
        self.on_close(self.close_window)
        self._mode_map = {
            'window': self.open_as_window,
            'docked': self.open_as_docked
        }

    @classmethod
    def get_pref_path(cls, short_path):
        return "features::{}::{}".format(cls.name, short_path)

    @classmethod
    def get_pref(cls, short_path):
        return pref.get(cls.get_pref_path(short_path))

    @classmethod
    def set_pref(cls, short_path, value):
        pref.set(cls.get_pref_path(short_path), value)

    @classmethod
    def get_instance(cls):
        return cls._instance

    def start_search(self, *_):
        self._search_bar.place(relwidth=1, relheight=1)
        self._search_bar.lift()
        self._search_bar.focus_set()

    def quit_search(self, *_):
        self._search_bar.place_forget()

    def on_search_query(self, query: str):
        """
        Called when inbuilt search feature is queried. Use the query string to display the
        necessary search results
        :param query: String of current search query
        :return: None
        """
        pass

    def on_search_clear(self):
        """
        Called when the user terminates the search bar. Ensure you make a call to the super
        method for the bar to actually get closed. This method can be used to restore the
        feature state to when not performing a search
        :return:
        """
        self.quit_search()
        pass

    def on_select(self, widget):
        """
        Called when a widget is selected in the designer
        :param widget: selected widget
        :return:None
        """
        pass

    def on_widget_change(self, old_widget, new_widget=None):
        """
        Called when a widget is fundamentally altered
        :param old_widget: Altered widget
        :param new_widget: The new widget taking the older widgets place
        :return: None
        """
        pass

    def on_widget_layout_change(self, widget):
        """
        Called when layout options of a widget are changed
        :param widget: Widget with altered layout options
        :return: None
        """
        pass

    def on_widget_add(self, widget, parent):
        """
        Called when a new widget is added to the designer
        :param widget: widget
        :param parent: the container widget to which thw widget is added
        :return: None
        """
        pass

    def on_widget_delete(self, widget, silently=False):
        """
        Called when a widget is deleted from the designer
        :param widget: deleted widget
        :param silently: flag indicating whether the deletion should be treated implicitly
        which is useful for instance when you don't want the deletion to be logged in the
        undo stack
        :return: None
        """
        pass

    def on_widget_restore(self, widget):
        """
        Called when a deleted widget is restored
        :param widget: restored widget
        :return: None
        """
        pass

    def on_session_clear(self):
        """
        Override to perform operations before a session is cleared and the studio
        resets to a new design
        :return: None
        """
        pass

    def on_app_close(self) -> bool:
        """
        Override to perform operations before the studio app closes.
        :return: True to allow shutdown to proceed or False to abort shutdown
        """
        return True

    def minimize(self, *_):
        if self.window_handle:
            self.close_window()
            return
        self.studio.minimize(self)
        self.set_pref("visible", False)
        self.is_visible.set(False)

    def maximize(self):
        if self.get_pref("mode") == "window":
            self.open_as_window()
            self.bar.select(self)
        else:
            self.studio.maximize(self)
        self.set_pref("visible", True)
        self.is_visible.set(True)

    def toggle(self):
        if self.get_pref("visible"):
            self.minimize()
        else:
            self.maximize()

    def create_menu(self):
        """
        Override this method to provide additional menu options
        :return: tuple of menu templates i.e. (type, label, image, callback, **additional_config)
        """
        # return an empty tuple as default
        return ()

    def _on_focus_release(self):
        if self._transparency_flag.get() and self.window_handle:
            if self.window_handle:
                self.window_handle.wm_attributes('-alpha', 0.3)
        if self.window_handle:
            self.save_window_pos()

    def _on_focus_get(self):
        if self.window_handle:
            self.window_handle.wm_attributes('-alpha', 1.0)

    def open_as_docked(self):
        self._view_mode.set("docked")
        self.set_pref('mode', 'docked')
        if self.window_handle:
            self.master.window.wm_forget(self)
            self.window_handle = None
            self.maximize()

    def reposition(self, side):
        self._side.set(side)
        self.studio.reposition(self, side)

    def open_as_window(self):
        if TkVersion < 8.5:
            logging.error("Window mode is not supported in current tk version")
            return
        self.master.window.wm_forget(self)
        rec = absolute_position(self) if not self.get_pref("pos::initialized") else (
            self.get_pref("pos::x"),
            self.get_pref("pos::y"),
            self.get_pref("pos::width"),
            self.get_pref("pos::height"),
        )
        self.window.wm_manage(self)
        # Allow us to create a hook in the close method of the window manager
        self.bind_close()
        self.title(self.name)
        self.transient(self.master.window)
        self.geometry('{}x{}+{}+{}'.format(rec[2], rec[3], rec[0], rec[1]))
        self.update_idletasks()
        self.window_handle = self
        self._view_mode.set("window")
        self.set_pref("mode", "window")
        self.studio._adjust_pane(self.pane)
        self.save_window_pos()
        if self.focus_get() != self and self.get_pref("inactive_transparency"):
            self.window_handle.wm_attributes('-alpha', 0.3)

    def save_window_pos(self):
        if not self.window_handle:
            if self.winfo_ismapped():
                self.set_pref("pane::height", self.height)
            return
        self.set_pref("pos", dict(
            x=self.winfo_x(),
            y=self.winfo_y(),
            width=self.width,
            height=self.height,
            initialized=True
        ))

    def close_window(self):
        if self.window_handle:
            # Store the current position of our window handle to used when it is reopened
            self.save_window_pos()
            self.master.window.wm_forget(self)
            self.window_handle = None
            self.studio.minimize(self)
            self.set_pref("visible", False)


class FeaturePane(PanedWindow):
    """
    Specialised Paned window for use with studio feature windows. It
    maintains an index of its children
    """
    # I don't expect anything close to 1000 features in a single pane
    MAX_PANES = 1000

    def add(self, child: BaseFeature, **kw):
        kw["height"] = child.get_pref("pane::height") if kw.get("height") is None else kw.get("height")
        insert_index = child.get_pref("pane::index")
        # no need for binary search the list will rarely be greater than 10
        for pane in self._panes():
            index = pane.get_pref("pane::index")
            if index > insert_index:
                # insert before pane with greater index
                kw['before'] = pane
                break
        else:
            if insert_index >= self.MAX_PANES:
                child.set_pref("pane::index", len(self.panes()))
        super().add(child, **kw)
        child.update_idletasks()

    def remove(self, child: BaseFeature):
        super().remove(child)
        for i, pane in enumerate(self._panes()):
            pane.set_pref("pane::index", i)
        child.set_pref("pane::index", self.MAX_PANES)

    forget = remove

    def _panes(self):
        # return resolved feature objects
        return list(map(lambda x: self.nametowidget(str(x)), self.panes()))
