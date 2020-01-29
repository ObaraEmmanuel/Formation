import logging

from hoverset.ui.widgets import Frame, Button, Label, MenuButton, ToolWindow, BooleanVar
from hoverset.ui.icons import get_icon, get_icon_image

from studio.ui.geometry import absolute_position

logging.basicConfig(level=logging.DEBUG)


class BaseFeature(Frame):
    name = "Feature"
    side = "left"
    pane = None
    bar = None
    icon = "blank"
    is_window = None
    is_docked = None
    _transparency_flag = None
    rec = (20, 20, 300, 300)  # Default window mode position

    def __init__(self, master, studio=None,  **cnf):
        super().__init__(master, **cnf)
        if not self.__class__.is_window:
            self.__class__.is_window = BooleanVar(None, False)
            self.__class__.is_docked = BooleanVar(None, True)
            self.__class__._transparency_flag = BooleanVar(None, False)
        self.studio = studio
        self._header = Frame(self, **self.style.dark, **self.style.dark_highlight_dim, height=30)
        self._header.pack(side="top", fill="x")
        self._header.pack_propagate(0)
        self._header.allow_drag = True
        Label(self._header, **self.style.dark_text_passive, text=self.name).pack(side="left")
        self._min = Button(self._header, text=get_icon("close"), **self.style.dark_button, width=25, height=25)
        self._min.pack(side="right")
        self._min.on_click(self.minimize)
        self._pref = MenuButton(self._header, text=get_icon("settings"), **self.style.dark_button)
        self._pref.pack(side="right")
        menu = self.make_menu((
            ("cascade", "View Mode", None, None, {"menu": (
                ("checkbutton", "Docked", None, self.open_as_docked, {"variable": self.is_docked}),
                ("checkbutton", "Window", None, self.open_as_window, {"variable": self.is_window}),
            )}),
            ("cascade", "Position", None, None, {"menu": (
                ("command", "Left", None, lambda: self.reposition("left"), {}),
                ("command", "Right", None, lambda: self.reposition("right"), {}),
            )}),
            ("checkbutton", "Transparent when inactive", None, None, {"variable": self._transparency_flag}),
            ("command", "Close", get_icon_image("close", 14, 14), self.minimize, {}),
            ("separator",),
            *self.create_menu()
        ), self._pref)
        self._pref.config(menu=menu)
        # self._pref.on_click(self.minimize)
        self.config(**self.style.dark)
        self.is_visible = True
        self.indicator = None
        self.window_handle = None

    def on_select(self, widget):
        pass

    def on_widget_change(self, old_widget, new_widget=None):
        pass

    def on_widget_layout_change(self, widget):
        pass

    def on_widget_add(self, widget, parent):
        pass

    def on_widget_delete(self, widget):
        pass

    def on_widget_restore(self, widget):
        pass

    def minimize(self, *_):
        if self.window_handle:
            self.close_window()
        else:
            self.studio.minimize(self)
        self.is_visible = False

    def maximize(self):
        if self.is_window.get():
            self.open_as_window()
        else:
            self.studio.maximize(self)
        self.is_visible = True

    def reposition(self, side):
        if self.window_handle:
            return
        if side == self.side:
            return
        self.__class__.side = side
        self.studio.uninstall(self)
        self.studio.install(self.__class__)

    def toggle(self):
        if self.is_visible:
            self.minimize()
        else:
            self.maximize()

    def on_new_feature(self, new):
        """
        Perform any important transfers before the old feature is completely destroyed
        :param new: The newly cloned feature
        :return:
        """
        self.studio.on_feature_change(new, self)
        self.bar.change_feature(new, self)
        new.bar = self.bar
        new.pane = self.pane
        new.studio = self.studio

    def create_menu(self):
        """
        Override this method to provide additional menu options
        :return: tuple of menu templates i.e. (type, label, image, callback, **additional_config)
        """
        # return an empty tuple as default
        return ()

    def clone(self, parent):
        """
        All features must implement a cloning procedure for some BaseFeature functionality to work.
        :param parent: The parent for the generated clone
        :return: The cloned widget
        """
        raise NotImplementedError()

    def _on_focus_lost(self):
        print(self._transparency_flag.get())
        if self._transparency_flag.get():
            print(self.window_handle)
            if self.window_handle:
                self.window_handle.wm_attributes('-alpha', 0.3)

    def _on_focus(self):
        if self.window_handle:
            self.window_handle.wm_attributes('-alpha', 1.0)

    def open_as_docked(self):
        self.is_docked.set(True)
        self.is_window.set(False)
        if self.window_handle:
            handle = self.window_handle
            self.create_temp().maximize()
            handle.destroy()

    def open_as_window(self):
        if not self.is_window.get():
            self.open_as_docked()
            return
        if self.window_handle:
            # There is already a window so no need to create one
            return
        window = ToolWindow(self.window)
        new_feature = self.clone(window)
        new_feature.pack(fill="both", expand=True)
        new_feature.window_handle = window
        rec = absolute_position(self) if self.winfo_ismapped() else self.__class__.rec
        self.on_new_feature(new_feature)
        window.set_geometry((rec[2], rec[3], rec[0], rec[1]))
        window.update_idletasks()
        window.show()
        window.on_close(new_feature.close_window)
        window.on_focus(new_feature._on_focus)
        window.on_focus_lost(new_feature._on_focus_lost)
        self.minimize()
        self.destroy()
        self.is_window.set(True)
        self.is_docked.set(False)

    def create_temp(self):
        new_feature = self.clone(self.pane)
        logging.debug(self.studio.features)
        self.on_new_feature(new_feature)
        self.window_handle = None
        return new_feature

    def close_window(self):
        if self.window_handle:
            # Store the current position of our window handle to used when it is reopened
            self.__class__.rec = absolute_position(self.window_handle)
            handle = self.window_handle
            self.create_temp()
            handle.destroy()
