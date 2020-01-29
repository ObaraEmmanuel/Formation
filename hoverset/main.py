"""
The Marshalling magic. Gathers all apps and creates an ecosystem.
"""

import sys
# Add Hoverset to path so imports from hoverset can work.
sys.path.append("..\\..\\Hoverset")

import hoverset.ui.widgets as widgets
from hoverset.ui.icons import get_icon, get_icon_image
from hoverset.catalogue import app_catalogue
from hoverset.ui.animation import Animate, Easing
from hoverset.apps import BaseApp


# We define a few universal widget handles easily accessible across classes
# The are inflated with widgets when MainApplication class is initialized
DESKTOP = None
TASK_BAR = None
START_WINDOW = None
SYSTEM = None

# Flags
NESTED = 0x1
SEPARATE = 0x2


class TaskBarIcon(widgets.Button):

    def __init__(self, master, bundle: BaseApp, **cnf):
        super().__init__(master, **cnf)
        self.config(text = bundle.icon, **self.style.dark_icon_medium_accent_1)
        self.bundle = bundle
        self.bind("<Enter>", lambda _: self.config(**self.style.dark_on_hover))
        self.bind("<Leave>", lambda _: self.un_hover())
        self.selected = False

        self.set_up_context((
            ("command", "close", get_icon_image("close"), self.close, {}),
            ("command", "open as window", get_icon_image("separate"), self.open_separate, {}),
        ))

    def close(self):
        SYSTEM.close_app(self)

    def re_launch(self):
        self.select()
        DESKTOP.clear_children()
        self.bundle.pack(fill="both", expand=True)

    def un_hover(self):
        if not self.selected:
            self.config(**self.style.dark_on_hover_ended)

    def select(self):
        self.selected = True
        self.config(**self.style.dark_on_hover)

    def deselect(self):
        self.selected = False
        self.config(**self.style.dark_on_hover_ended)

    def close_bundle(self):
        self.bundle.close()

    def open_separate(self):
        SYSTEM.close_app(self)
        SYSTEM.launch(self.bundle.__class__, SEPARATE)


class AppItem(widgets.Frame):

    def __init__(self, master, app, **cnf):
        super().__init__(master, **cnf)
        self.app = app
        self.config(height=40, width=280, **self.style.dark, **self.style.dark_highlight)
        self._icon = widgets.Label(self, text=self.app.icon, **self.style.dark_icon_medium_accent_1)
        self._icon.place(x=0, y=5, width=50, height=35)
        self._name = widgets.Label(self, text=app.NAME, **self.style.dark_text)
        self._name.place(x=55, y=10, width=240, height=20)
        self._name.set_alignment("w")
        self.bind("<Enter>", lambda _: self.on_hover())
        self.bind("<Leave>", lambda _: self.on_hover_ended())
        self.on_click(self.launch)
        self.set_up_context((
            ("command", "open as window", get_icon_image("separate"), self.launch_separate, {}),
            ("command", "About app", get_icon_image("info"), None, {}),
        ))

    def on_hover(self):
        self.config_all(**self.style.dark_on_hover)

    def on_hover_ended(self):
        self.config_all(**self.style.dark_on_hover_ended)

    def launch(self, *_):
        SYSTEM.launch(self.app)

    def launch_separate(self):
        SYSTEM.launch(self.app, SEPARATE)


class Category(widgets.Frame):

    def __init__(self, master, app_group_index, app_body, **cnf):
        self.app_group = app_catalogue[app_group_index]
        super().__init__(master, **cnf)
        self.config(height=65, width=255, **self.style.dark, **self.style.dark_highlight)
        self._icon = widgets.Label(self, text=app_group_index.value[1], **self.style.dark_icon_large)
        self._icon.place(x=0, y=0, width=60, height=60)
        self._name = widgets.Label(self, text=app_group_index.value[0], **self.style.dark_text_medium)
        self._name.place(x=65, y=5, width=185, height=20)
        self._name.set_alignment("w")
        self._count = widgets.Label(self, text="{} apps".format(len(self.app_group)), **self.style.dark_text_accent_1)
        self._count.place(x=65, y=30, width=185, height=20)
        self._count.set_alignment("w")
        self._app_body = app_body
        self.bind("<Enter>", lambda _: self.on_hover())
        self.bind("<Leave>", lambda _: self.on_hover_ended())

    def on_hover(self):
        self.config_all(**self.style.dark_on_hover)
        self._app_body.clear_children()
        for app in self.app_group:
            AppItem(self._app_body.body, app).pack(side="top", anchor="n")
        if len(self.app_group) == 0:
            widgets.Label(self._app_body.body, **self.style.dark_text_accent_1,
                          text="No apps developed in this category").pack(anchor="center")

    def on_hover_ended(self):
        self.config_all(**self.style.dark_on_hover_ended)


class TaskBar(widgets.Frame):
    ICON_DIMENSION = 50

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.config(height=self.ICON_DIMENSION)
        self.apps = []
        self.selected = None

    def add(self, app):
        app.place(x=self.ICON_DIMENSION * len(self.apps), y=0, width=self.ICON_DIMENSION, relheight=1)
        self.apps.append(app)
        if isinstance(app, TaskBarIcon):
            app.on_click(lambda _: self.select(app))
            self.select(app)

    def select(self, app):
        if self.selected is not None:
            self.selected.deselect()
        self.selected = app
        app.re_launch()
        app.select()

    def remove(self, app):
        app.place_forget()
        index = self.apps.index(app)
        self.apps.remove(app)
        self.redraw()
        # If we close the app we want the TaskBar to automatically select the next available app handle
        # if the app closed was at the end (index == len(self.apps)) then its index is out of bound so lower it by one
        if index == len(self.apps):
            index -= 1
        # Select the app that now lies at the position of the closed app
        if index >= 0:
            # We need to avoid selecting non TaskBar icons which would result in errors
            if isinstance(self.apps[index], TaskBarIcon):
                self.select(self.apps[index])

    def redraw(self):
        # Re-place the icons for cases where an app is closed so its position is rendered vacant
        # TODO Make the redraw more efficient by re-placing only affected zones
        self.clear_children()
        for i in range(len(self.apps)):
            self.apps[i].place(x=self.ICON_DIMENSION * i, y=0, width=self.ICON_DIMENSION, relheight=1)


class Start(widgets.Frame):
    MAX_WIDTH = 600
    GROW_RATE = 100

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark, **self.style.dark_border_highlight)
        self._width = 0
        self.place(x=0, y=0, width=self._width, relheight=1)
        retract = widgets.Button(self, anchor="center", text=get_icon("arrow_left"), **self.style.dark_button)
        retract.on_click(lambda _: self.hide())
        self.categories = widgets.ScrolledFrame(self, width=255, **self.style.dark)
        self.categories.pack(side="left", fill="y", anchor="w")
        self.apps = widgets.ScrolledFrame(self, width=280, **self.style.dark)
        self.apps.pack(side="left", fill="y", anchor="w")
        self._load_apps()
        retract.place(x=self.MAX_WIDTH - 30, y=10, width=25, height=25)
        self.bind("<FocusOut>", lambda _: self.hide())

    def show(self):
        Animate(self, 0, self.MAX_WIDTH, lambda x: self.place(x=0, y=0, width=x, relheight=1), dur=1,
                easing=Easing.SLING_SHOT)
        self.focus_set()

    def _load_apps(self):
        for app_group_index in app_catalogue:
            Category(self.categories.body, app_group_index, self.apps).pack(side="top", anchor="n")

    def hide(self):
        self.place(x=0, y=0, width=0, relheight=1)


class Window(widgets.Window):

    def __init__(self, master, app=None, **cnf):
        super().__init__(master, **cnf)
        self.geometry("800x500")
        if app is not None:
            self.bundle = app(self)
            self.bundle.window = self
        self.protocol("WM_DELETE_WINDOW", lambda: SYSTEM.close_app(self))

    def close_bundle(self):
        self.destroy()


class MainApplication(widgets.Application):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        global DESKTOP, START_WINDOW, TASK_BAR, SYSTEM
        SYSTEM = self
        self.load_styles("ui/themes/default.css")
        self.geometry("1100x650")
        self.desktop = DESKTOP = widgets.Frame(self, **self.style.dark, takefocus=1)
        self._task_bar = TASK_BAR = TaskBar(self, **self.style.dark)
        self._task_bar.pack(side="bottom", fill="x", anchor="s")
        self.desktop.pack(side="top", fill="both", expand=True)
        self._start = widgets.Button(self._task_bar, height=2, width=2, text=get_icon("play"),
                                     **self.style.dark_text_medium, **self.style.dark_highlight)
        self._task_bar.add(self._start)
        self._start_window = START_WINDOW = Start(self)
        self._start.on_click(lambda _: self._start_window.show())
        self.running_app_handles = []

    def launch(self, app_class, flag=NESTED):
        for app_handle in self.running_app_handles:
            if isinstance(app_handle.bundle, app_class):
                handle = app_handle
                if isinstance(handle, TaskBarIcon):
                    DESKTOP.clear_children()
                    TASK_BAR.select(handle)
                if isinstance(handle, Window):
                    handle.deiconify()
                    handle.lift()
                break
        else:
            if flag == NESTED:
                DESKTOP.clear_children()
                app = app_class(DESKTOP)
                handle = TaskBarIcon(TASK_BAR, app)
                self.running_app_handles.append(handle)
                TASK_BAR.add(handle)
            else:
                handle = Window(self.window, app_class)
                self.running_app_handles.append(handle)

        START_WINDOW.hide()

    def close_app(self, app_handle):
        self.running_app_handles.remove(app_handle)
        if isinstance(app_handle, TaskBarIcon):
            TASK_BAR.remove(app_handle)
        app_handle.close_bundle()


if __name__ == "__main__":
    # apps.unicode_viewer.App().mainloop()
    MainApplication().mainloop()
