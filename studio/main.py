# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import functools
import sys

# Add Studio and Hoverset to path so imports from hoverset can work.
sys.path.append("..\\..\\Hoverset")

from studio.feature.design import Designer
from studio.feature.component_tree import ComponentTree
from studio.feature.stylepane import StylePane
from studio.feature.components import ComponentPane
from studio.feature import BaseFeature
from studio.ui.widgets import SideBar

from hoverset.ui.widgets import Application, Frame, PanedWindow, Button
from hoverset.ui.icons import get_icon_image
from hoverset.util.execution import Action


class StudioApplication(Application):
    widget_tree = None
    designer: Designer = None
    style_pane: StylePane = None
    widget_set: ComponentPane = None

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.load_styles("../hoverset/ui/themes/default.css")
        self.geometry("1100x650")
        self.state('zoomed')
        self.title('Tkinter Studio')
        self._toolbar = Frame(self, **self.style.dark, height=30)
        self._toolbar.pack(side="top", fill="x")
        self._toolbar.pack_propagate(0)
        self._statusbar = Frame(self, **self.style.dark, height=20)
        self._statusbar.pack(side="bottom", fill="x")
        self._statusbar.pack_propagate(0)
        body = Frame(self, **self.style.dark)
        body.pack(fill="both", expand=True, side="top")
        self._right_bar = SideBar(body)
        self._right_bar.pack(side="right", fill="y")
        self._left_bar = SideBar(body)
        self._left_bar.pack(side="left", fill="y")
        self._pane = PanedWindow(body, **self.style.dark_pane_horizontal)
        self._pane.pack(side="left", fill="both", expand=True)
        self._left = PanedWindow(self._pane, **self.style.dark_pane_vertical)
        self._center = PanedWindow(self._pane, **self.style.dark_pane_vertical)
        self._right = PanedWindow(self._pane, **self.style.dark_pane_vertical)

        self._bin = []
        self._clipboard = None
        self._undo_stack = []
        self._redo_stack = []

        self._pane.add(self._left, minsize=320, sticky='nswe', width=320)
        self._pane.add(self._center, minsize=400, width=16000, sticky='nswe')
        self._pane.add(self._right, minsize=320, sticky='nswe', width=320)

        self._panes = {
            "left": (self._left, self._left_bar),
            "right": (self._right, self._right_bar),
            "center": (self._center, None)
        }

        self.features = []

        self.designer = Designer(self._center, self)
        self._center.add(self.designer, sticky='nswe')
        self.install(ComponentPane)
        self.install(ComponentTree)
        self.install(StylePane)

        self.actions = (
            ("Undo", get_icon_image("undo", 20, 20), lambda e: self.undo()),
            ("Redo", get_icon_image("redo", 20, 20), lambda e: self.redo()),
            ("Fullscreen", get_icon_image("image_editor", 20, 20), self.close_all)
        )

        self.init_actions()
        self.selected = None

        # -------------------------------------------- menu definition ------------------------------------------------

        self.menu_bar = self.make_menu((
            ("cascade", "File", None, None, {"menu": (
                ("command", "New", None, None, {"accelerator": "Ctrl+N"}),
                ("command", "Open", None, None, {"accelerator": "Ctrl+O"}),
                ("separator",),
                ("command", "Save", None, None, {"accelerator": "Ctrl+S"}),
                ("command", "Save As", None, None, {}),
                ("separator",),
                ("command", "Exit", None, self.destroy, {}),
            )}),
            ("cascade", "Edit", None, None, {"menu": (
                ("command", "undo", get_icon_image("undo", 14, 14), self.undo, {"accelerator": "Ctrl+Z"}),
                ("command", "redo", get_icon_image("redo", 14, 14), self.redo, {"accelerator": "Ctrl+Y"}),
                ("separator",),
                ("command", "copy", get_icon_image("copy", 14, 14), self.copy, {"accelerator": "Ctrl+C"}),
                ("command", "paste", get_icon_image("clipboard", 14, 14), self.paste, {"accelerator": "Ctrl+V"}),
                ("command", "cut", get_icon_image("cut", 14, 14), None, {"accelerator": "Ctrl+X"}),
                ("separator",),
                ("command", "delete", get_icon_image("delete", 14, 14), self.delete, {}),
            )}),
            ("cascade", "Code", None, None, {"menu": (
                ("cascade", "Generate", None, None, {"menu": (
                    ("command", "Python", None, None, {}),
                    ("command", "xml", None, None, {}),
                    ("command", "tcl", None, None, {})
                )}),
                ("command", "View", None, None, {})
            )}),
            ("cascade", "Window", None, None, {"menu": (
                ("command", "close all", get_icon_image("close", 14, 14), self.close_all, {}),
                ("command", "close all on the right", get_icon_image("blank", 14, 14),
                 self.close_all_on_side("right"), {}),
                ("command", "close all on the left", get_icon_image("blank", 14, 14),
                 self.close_all_on_side("left"), {}),
                ("separator", ),
                ("command", "Save window positions", None, None, {})
            )}),
            ("cascade", "Tools", None, None, {"menu": ()}),
            ("cascade", "Help", None, None, {"menu": (
                ("command", "Documentation", None, None, {}),
                ("command", "Check for updates", get_icon_image("cloud", 14, 14), None, {}),
                ("separator",),
                ("command", "About Studio", None, None, {}),
            )})
        ), self)
        self.config(menu=self.menu_bar)

        self.menu_template = (
            ("command", "copy", get_icon_image("copy", 14, 14), self.copy, {"accelerator": "Ctrl+C"}),
            ("command", "paste", get_icon_image("clipboard", 14, 14), self.paste, {"accelerator": "Ctrl+V"}),
            ("command", "cut", get_icon_image("cut", 14, 14), None, {"accelerator": "Ctrl+X"}),
            ("separator",),
            ("command", "delete", get_icon_image("delete", 14, 14), self.delete, {}),
        )

    def new_action(self, action: Action):
        """
        Register a undo redo point
        :param action: An action object implementing undo and redo methods
        :return:
        """
        self._undo_stack.append(action)
        self._redo_stack.clear()

    def undo(self):
        if not len(self._undo_stack):
            # Let's avoid popping an empty list to prevent raising IndexError
            return
        action = self._undo_stack.pop()
        action.undo()
        self._redo_stack.append(action)

    def redo(self):
        if not len(self._redo_stack):
            return
        action = self._redo_stack.pop()
        action.redo()
        self._undo_stack.append(action)

    def copy(self):
        if self.selected:
            self._clipboard = self.selected

    def get_pane_info(self, pane):
        return self._panes.get(pane, [self._right, self._right_bar])

    def paste(self):
        if self._clipboard:
            self.designer.paste(self._clipboard)

    def close_all_on_side(self, side):
        for feature in self.features:
            if feature.pane == side:
                self.minimize(feature)
        # To avoid errors when side is not a valid pane identifier we default to the right pane
        self._panes.get(side, (self._right, self._right_bar))[1].close_all()

    def close_all(self, *_):
        for feature in self.features:
            self.minimize(feature)
        self._right_bar.close_all()
        self._left_bar.close_all()

    def init_actions(self):
        for action in self.actions:
            btn = Button(self._toolbar, image=action[1], **self.style.dark_button, width=25, height=25)
            btn.pack(side="left")
            btn.on_click(action[2])

    def uninstall(self, feature):
        self.features.remove(feature)
        feature.bar.remove(feature)
        feature.pane.forget(feature)
        self._adjust_pane(feature.pane)

    def install(self, feature) -> BaseFeature:
        pane, bar = self._panes.get(feature.side, (self._left, self._left_bar))
        obj = feature(pane, self)
        obj.pane = pane
        obj.bar = bar
        self.features.append(obj)
        if bar is not None:
            bar.add_feature(obj)
        pane.add(obj, minsize=100, height=300, sticky='nswe')
        return obj

    def get_features_as_menu(self):
        # For each feature we create a menu template
        # The command value is the self.maximize method which will reopen the feature
        return [("command",  # Type
                 f.name, get_icon_image(f.icon, 14, 14),  # Label, image
                 functools.partial(self.maximize, f),  # Command built from feature
                 {}) for f in self.features]

    def _adjust_pane(self, pane):
        if len(pane.panes()) == 0:
            self._pane.paneconfig(pane, minsize=0, width=0)
            self._pane.paneconfig(self._center, width=16000)
        else:
            self._pane.paneconfig(pane, minsize=320)

    def minimize(self, feature):
        feature.pane.forget(feature)
        feature.bar.deselect(feature)
        self._adjust_pane(feature.pane)

    def maximize(self, feature):
        feature.pane.add(feature, height=300, sticky='nswe')
        feature.bar.select(feature)
        self._adjust_pane(feature.pane)

    def select(self, widget, source=None):
        self.selected = widget
        if source != self.designer:
            # Select from the designer explicitly so the selection does not end up being re-fired
            self.designer.select(widget, True)
        for feature in self.features:
            if feature != source:
                feature.on_select(widget)

    def add(self, widget, parent=None):
        for feature in self.features:
            feature.on_widget_add(widget, parent)

    def widget_modified(self, widget1, source=None, widget2=None):
        if source != self.designer:
            self.designer.on_widget_change(widget1, widget2)
        for feature in self.features:
            if feature != source:
                feature.on_widget_change(widget1, widget2)

    def widget_layout_changed(self, widget):
        for feature in self.features:
            feature.on_widget_layout_change(widget)

    def delete(self, widget=None, source=None):
        widget = self.selected if widget is None else widget
        if self.selected == widget:
            self.select(None)
        if source != self.designer:
            self.designer.delete(widget)
        for feature in self.features:
            feature.on_widget_delete(widget)

    def on_restore(self, widget):
        for feature in self.features:
            feature.on_widget_restore(widget)

    def on_feature_change(self, new, old):
        self.features.insert(self.features.index(old), new)
        self.features.remove(old)


def main():
    StudioApplication().mainloop()


if __name__ == "__main__":
    # apps.unicode_viewer.App().mainloop()
    main()
