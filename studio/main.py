# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import functools
import os
import sys
import time
from tkinter import filedialog, Toplevel

from studio.feature.design import Designer
from studio.feature import FEATURES, StylePane
from studio.feature._base import BaseFeature, FeaturePane
from studio.tools import ToolManager
from studio.ui.widgets import SideBar
from studio.ui.about import about_window
from studio.preferences import Preferences, open_preferences
from studio.resource_loader import ResourceLoader
from studio.updates import Updater
import studio

from hoverset.ui.widgets import Application, Frame, PanedWindow, Button, ActionNotifier
from hoverset.ui.icons import get_icon_image
from hoverset.data.images import load_tk_image
from hoverset.util.execution import Action
from hoverset.data.utils import get_resource_path
from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.menu import MenuUtils, EnableIf, dynamic_menu, LoadLater
from hoverset.data import actions
from hoverset.data.keymap import ShortcutManager, CharKey, KeyMap, BlankKey

from formation import AppBuilder

pref = Preferences.acquire()


class StudioApplication(Application):
    ICON_PATH = get_resource_path(studio, "resources/images/formation_icon.png")
    THEME_PATH = pref.get("resource::theme")

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        # Load icon asynchronously to prevent issues which have been known to occur when loading it synchronously
        icon_image = load_tk_image(self.ICON_PATH)
        self.load_styles(self.THEME_PATH)
        self.iconphoto(True, icon_image)
        self.pref = pref
        self._restore_position()
        self.title('Formation Studio')
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self.shortcuts = ShortcutManager(self, pref)
        self.shortcuts.bind_all()
        self._register_actions()
        self._toolbar = Frame(self, **self.style.surface, height=30)
        self._toolbar.pack(side="top", fill="x")
        self._toolbar.pack_propagate(0)
        self._statusbar = Frame(self, **self.style.surface, height=20)
        self._statusbar.pack(side="bottom", fill="x")
        self._statusbar.pack_propagate(0)
        body = Frame(self, **self.style.surface)
        body.pack(fill="both", expand=True, side="top")
        self._right_bar = SideBar(body)
        self._right_bar.pack(side="right", fill="y")
        self._left_bar = SideBar(body)
        self._left_bar.pack(side="left", fill="y")
        self._pane = PanedWindow(body, **self.style.pane_horizontal)
        self._pane.pack(side="left", fill="both", expand=True)
        self._left = FeaturePane(self._pane, **self.style.pane_vertical)
        self._center = PanedWindow(self._pane, **self.style.pane_vertical)
        self._right = FeaturePane(self._pane, **self.style.pane_vertical)

        self._bin = []
        self._clipboard = None
        self._undo_stack = []
        self._redo_stack = []
        self.current_preview = None

        self._pane.add(self._left, minsize=320, sticky='nswe', width=320)
        self._pane.add(self._center, minsize=400, width=16000, sticky='nswe')
        self._pane.add(self._right, minsize=320, sticky='nswe', width=320)

        self._panes = {
            "left": (self._left, self._left_bar),
            "right": (self._right, self._right_bar),
            "center": (self._center, None)
        }

        icon = get_icon_image

        self.actions = (
            ("Delete", icon("delete", 20, 20), lambda e: self.delete(), "Delete selected widget"),
            ("Undo", icon("undo", 20, 20), lambda e: self.undo(), "Undo action"),
            ("Redo", icon("redo", 20, 20), lambda e: self.redo(), "Redo action"),
            ("Cut", icon("cut", 20, 20), lambda e: self.cut(), "Cut selected widget"),
            ("separator",),
            ("Fullscreen", icon("image_editor", 20, 20), lambda e: self.close_all(), "Design mode"),
            ("Separate", icon("separate", 20, 20), lambda e: self.features_as_windows(),
             "Open features in window mode"),
            ("Dock", icon("flip_horizontal", 15, 15), lambda e: self.features_as_docked(),
             "Dock all features"),
            ("separator",),
            ("New", icon("add", 20, 20), lambda e: self.open_new(), "New design"),
            ("Save", icon("save", 20, 20), lambda e: self.save(), "Save design"),
            ("Preview", icon("play", 20, 20), lambda e: self.preview(), "Preview design"),
        )

        self.init_toolbar()
        self.selected = None
        # set the image option to blank if there is no image for the menu option
        self.blank_img = blank_img = icon("blank", 14, 14)

        # -------------------------------------------- menu definition ------------------------------------------------
        self.menu_template = (EnableIf(
            lambda: self.selected,
            ("separator",),
            ("command", "copy", icon("copy", 14, 14), actions.get('STUDIO_COPY'), {}),
            EnableIf(
                lambda: self._clipboard is not None,
                ("command", "paste", icon("clipboard", 14, 14), actions.get('STUDIO_PASTE'), {})
            ),
            ("command", "cut", icon("cut", 14, 14), actions.get('STUDIO_CUT'), {}),
            ("separator",),
            ("command", "delete", icon("delete", 14, 14), actions.get('STUDIO_DELETE'), {}),
        ),)

        self.menu_bar = MenuUtils.make_dynamic((
            ("cascade", "File", None, None, {"menu": (
                ("command", "New", icon("add", 14, 14), actions.get('STUDIO_NEW'), {}),
                ("command", "Open", icon("folder", 14, 14), actions.get('STUDIO_OPEN'), {}),
                ("cascade", "Recent", icon("clock", 14, 14), None, {"menu": self._create_recent_menu()}),
                ("separator",),
                ("command", "Save", icon("save", 14, 14), actions.get('STUDIO_SAVE'), {}),
                ("command", "Save As", icon("save", 14, 14), actions.get('STUDIO_SAVE_AS'), {}),
                ("separator",),
                ("command", "Settings", icon("settings", 14, 14), actions.get('STUDIO_SETTINGS'), {}),
                ("command", "Restart", icon("blank", 14, 14), actions.get('STUDIO_RESTART'), {}),
                ("command", "Exit", icon("close", 14, 14), actions.get('STUDIO_EXIT'), {}),
            )}),
            ("cascade", "Edit", None, None, {"menu": (
                EnableIf(lambda: len(self._undo_stack),
                         ("command", "undo", icon("undo", 14, 14), actions.get('STUDIO_UNDO'), {})),
                EnableIf(lambda: len(self._redo_stack),
                         ("command", "redo", icon("redo", 14, 14), actions.get('STUDIO_REDO'), {})),
                *self.menu_template,
            )}),
            ("cascade", "Code", None, None, {"menu": (
                EnableIf(
                    lambda: self.designer and self.designer.root_obj,
                    ("command", "Preview design", icon("play", 14, 14), actions.get('STUDIO_PREVIEW'), {}),
                    ("command", "close preview", icon("close", 14, 14), actions.get('STUDIO_PREVIEW_CLOSE'), {})
                )
            )}),
            ("cascade", "View", None, None, {"menu": (
                ("command", "show all", blank_img, actions.get('FEATURE_SHOW_ALL'), {}),
                ("command", "close all", icon("close", 14, 14), actions.get('FEATURE_CLOSE_ALL'), {}),
                ("command", "close all on the right", blank_img, actions.get('FEATURE_CLOSE_RIGHT'), {}),
                ("command", "close all on the left", blank_img, actions.get('FEATURE_CLOSE_LEFT'), {}),
                ("separator",),
                ("command", "Undock all windows", blank_img, actions.get('FEATURE_UNDOCK_ALL'), {}),
                ("command", "Dock all windows", blank_img, actions.get('FEATURE_DOCK_ALL'), {}),
                ("separator",),
                LoadLater(self.get_features_as_menu),
                ("separator",),
                ("command", "Save window positions", blank_img, actions.get('FEATURE_SAVE_POS'), {})
            )}),
            ("cascade", "Tools", None, None, {"menu": ToolManager.get_tools_as_menu(self)}),
            ("cascade", "Help", None, None, {"menu": (
                ("command", "Help", icon('dialog_info', 14, 14), actions.get('STUDIO_HELP'), {}),
                ("command", "Check for updates", icon("cloud", 14, 14), self._check_updates, {}),
                ("separator",),
                ("command", "About Formation", icon("formation", 14, 14), lambda: about_window(self), {}),
            )})
        ), self, self.style, False)
        self.config(menu=self.menu_bar)

        self.features = []

        self.designer = Designer(self._center, self)
        self._center.add(self.designer, sticky='nswe')

        # install features
        for feature in FEATURES:
            self.install(feature)

        # common feature references
        self.style_pane = self.get_feature(StylePane)

        self._startup()
        self._restore_position()
        self._exit_failures = 0

    def _startup(self):
        on_startup = pref.get("studio::on_startup")
        if on_startup == "new":
            self.open_new()
        elif on_startup == "recent":
            latest = pref.get_latest()
            if latest:
                self.open_file(latest)
        # if blank do nothing

    def _get_window_state(self):
        try:
            if self.wm_attributes("-zoomed"):
                return 'zoomed'
            return 'normal'
        except:
            # works for windows and mac os
            return self.state()

    def _set_window_state(self, state):
        try:
            # works in windows and mac os
            self.state(state)
        except:
            self.wm_attributes('-zoomed', state == 'zoomed')

    def _save_position(self):
        # self.update_idletasks()
        pref.set("studio::pos", dict(
            width=self.width,
            height=self.height,
            x=self.winfo_x(),
            y=self.winfo_y(),
            state=self._get_window_state(),  # window state either zoomed or normal
        ))

    def _restore_position(self):
        pos = pref.get("studio::pos")
        self._set_window_state(pos.get("state"))
        if pos.get("state") == 'normal':
            self.geometry('{width}x{height}+{x}+{y}'.format(**pos))

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

    def last_action(self):
        if len(self._undo_stack):
            return self._undo_stack[-1]
        return None

    def pop_last_action(self, key=None):
        last = self.last_action()
        if last is not None:
            # verify action key first
            if key is not None and last.key != key:
                return
            self._undo_stack.remove(last)

    def copy(self):
        if self.selected:
            # store the current object as an xml node in the clipboard
            self._clipboard = self.designer.as_xml_node(self.selected)

    def install_status_widget(self, widget_class, *args, **kwargs):
        widget = widget_class(self._statusbar, *args, **kwargs)
        widget.pack(side='right', padx=2, fill='y')
        return widget

    def get_pane_info(self, pane):
        return self._panes.get(pane, [self._right, self._right_bar])

    def paste(self):
        if self._clipboard is not None:
            self.designer.paste(self._clipboard)

    def close_all_on_side(self, side):
        for feature in self.features:
            if feature.side == side:
                feature.minimize()
        # To avoid errors when side is not a valid pane identifier we default to the right pane
        self._panes.get(side, (self._right, self._right_bar))[1].close_all()

    def close_all(self, *_):
        for feature in self.features:
            feature.minimize()
        self._right_bar.close_all()
        self._left_bar.close_all()

    def init_toolbar(self):
        for action in self.actions:
            if len(action) == 1:
                Frame(self._toolbar, width=1, bg=self.style.colors.get("primarydarkaccent")).pack(
                    side='left', fill='y', pady=3, padx=5)
                continue
            btn = Button(self._toolbar, image=action[1], **self.style.button, width=25, height=25)
            btn.pack(side="left", padx=3)
            btn.tooltip(action[3])
            ActionNotifier.bind_event("<Button-1>", btn, action[2], text=action[3])

    def uninstall(self, feature):
        self.features.remove(feature)
        feature.bar.remove(feature)
        feature.pane.forget(feature)
        self._adjust_pane(feature.pane)

    def get_pane_bar(self, side):
        if side in self._panes:
            return self._panes.get(side, (self._left, self._left_bar))

    def reposition(self, feature: BaseFeature, side):
        if self.get_pane_bar(side):
            pane, bar = self.get_pane_bar(side)
            feature.bar.remove(feature)
            feature.pane.forget(feature)
            self._adjust_pane(feature.pane)
            feature.bar = bar
            feature.pane = pane
            bar.add_feature(feature)
            if feature.get_pref("mode") == "docked":
                pane.add(feature, minsize=100)
            feature.set_pref("side", side)

    def install(self, feature) -> BaseFeature:
        obj = feature(self, self)
        pane, bar = self._panes.get(obj.get_pref('side'), (self._left, self._left_bar))
        obj.pane = pane
        obj.bar = bar
        self.features.append(obj)
        if bar is not None:
            bar.add_feature(obj)
        if not obj.get_pref('visible'):
            bar.deselect(obj)
            self._adjust_pane(pane)
        else:
            bar.select(obj)
            obj.maximize()
        return obj

    def show_all_windows(self):
        for feature in self.features:
            feature.maximize()

    def features_as_windows(self):
        for feature in self.features:
            feature.open_as_window()

    def features_as_docked(self):
        for feature in self.features:
            feature.open_as_docked()

    def set_path(self, path):
        if path:
            file_dir = os.path.dirname(path)
            if os.path.exists(file_dir):
                # change working directory
                os.chdir(file_dir)
        path = path or "untitled"
        self.title("Formation studio" + " - " + str(path))

    @dynamic_menu
    def _create_recent_menu(self, menu):
        # Dynamically create recent file menu every time menu is posted
        menu.image = get_icon_image("close", 14, 14)
        menu.config(**self.style.context_menu)
        recent = pref.get_recent()
        for path, label in recent:
            menu.add_command(
                label=label,
                command=functools.partial(self.open_recent, path),
                image=self.blank_img, compound='left',
            )
        menu.add_command(
            label="Clear", image=menu.image, command=pref.clear_recent,
            compound="left"
        )

    def open_file(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(parent=self, filetypes=[('XML', '*.xml')])
        elif not os.path.exists(path):
            MessageDialog.show_error(
                parent=self,
                title="Missing File",
                message="File {} does not exist".format(path),
            )
            return
        if path:
            self.set_path(path)
            self.designer.open_xml(path)
            pref.update_recent(path)

    def open_recent(self, path):
        self.open_file(path)

    def open_new(self):
        self.designer.open_new()
        self.set_path(None)

    def save(self):
        path = self.designer.save()
        self.set_path(path)
        pref.update_recent(path)

    def save_as(self):
        path = self.designer.save(new_path=True)
        self.set_path(path)
        pref.update_recent(path)

    def get_feature(self, feature_class) -> BaseFeature:
        for feature in self.features:
            if feature.__class__ == feature_class:
                return feature
        # returns None by if feature is not found

    def get_features_as_menu(self):
        # For each feature we create a menu template
        # The command value is the self.maximize method which will reopen the feature
        return [("checkbutton",  # Type
                 f.name, None,  # Label, image
                 functools.partial(f.toggle),  # Command built from feature
                 {"variable": f.is_visible}) for f in self.features]

    def save_window_positions(self):
        for feature in self.features:
            feature.save_window_pos()
        self._save_position()

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
        feature.pane.add(feature, minsize=100)
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
        for feature in self._all_features():
            if feature != source:
                feature.on_widget_change(widget1, widget2)

    def widget_layout_changed(self, widget):
        for feature in self.features:
            feature.on_widget_layout_change(widget)

    def delete(self, widget=None, source=None):
        widget = self.selected if widget is None else widget
        if widget is None:
            return
        if self.selected == widget:
            self.select(None)
        if source != self.designer:
            self.designer.delete(widget)
        for feature in self.features:
            feature.on_widget_delete(widget)

    def cut(self, widget=None, source=None):
        widget = self.selected if widget is None else widget
        if not widget:
            return
        if self.selected == widget:
            self.select(None)
        self._clipboard = self.designer.as_xml_node(widget)
        if source != self.designer:
            self.designer.delete(widget, True)
        for feature in self.features:
            feature.on_widget_delete(widget, True)

    def on_restore(self, widget):
        for feature in self.features:
            feature.on_widget_restore(widget)

    def on_feature_change(self, new, old):
        self.features.insert(self.features.index(old), new)
        self.features.remove(old)

    def on_session_clear(self, source):
        self._redo_stack.clear()
        self._undo_stack.clear()
        for feature in self._all_features():
            if feature != source:
                feature.on_session_clear()

    def preview(self):
        if self.designer.root_obj is None:
            # If there is no root object show a warning
            MessageDialog.show_warning(
                parent=self,
                title='Empty design',
                message='There is nothing to preview. Please add a root widget')
            return
        # close previous preview if any
        self.close_preview()
        window = self.current_preview = Toplevel(self)
        window.wm_transient(self)
        window.build = AppBuilder(window, node=self.designer.to_xml())
        name = self.designer.design_path if self.designer.design_path is not None else "Untitled"
        window.build._app.title(os.path.basename(name))

    def close_preview(self):
        if self.current_preview:
            self.current_preview.destroy()

    def _all_features(self):
        """
        Return a tuple of all features including the designer instance
        :return: tuple of features
        """
        # We cannot unpack directly at the return statement due to a flaw in python versions < 3.8
        features = *self.features, self.designer
        return features

    def _force_exit_prompt(self):
        return MessageDialog.builder(
            {"text": "Force exit", "value": True, "focus": True},
            {"text": "Return to app", "value": False},
            wait=True,
            title="Exit Failure",
            message="An internal failure is preventing the app from exiting. Force exit?",
            parent=self,
            icon=MessageDialog.ICON_ERROR
        )

    def _on_close(self):
        try:
            self._save_position()
            # pass the on window close event to the features
            for feature in self._all_features():
                # if any feature returns false abort shut down
                feature.save_window_pos()
                if not feature.on_app_close():
                    return
            self.destroy()
        except Exception:
            self._exit_failures += 1
            if self._exit_failures >= 2:
                force = self._force_exit_prompt()
                if force:
                    # exit by all means necessary
                    sys.exit(1)

    def get_help(self):
        # Entry point for studio help functionality
        self._coming_soon()

    def settings(self):
        open_preferences(self)

    def _coming_soon(self):
        MessageDialog.show_info(
            parent=self,
            title="Coming soon",
            message="We are working hard to bring this feature to you. Hang in there.",
            icon="clock"
        )

    def _check_updates(self):
        Updater.check(self)

    def _register_actions(self):
        CTRL, ALT, SHIFT = KeyMap.CONTROL, KeyMap.ALT, KeyMap.SHIFT
        routine = actions.Routine
        # These actions are best bound separately to avoid interference with text entry widgets
        actions.add(
            routine(self.cut, 'STUDIO_CUT', 'Cut selected widget', 'studio', CTRL + CharKey('x')),
            routine(self.copy, 'STUDIO_COPY', 'Copy selected widget', 'studio', CTRL + CharKey('c')),
            routine(self.paste, 'STUDIO_PASTE', 'Paste selected widget', 'studio', CTRL + CharKey('v')),
            routine(self.delete, 'STUDIO_DELETE', 'Delete selected widget', 'studio', KeyMap.DELETE),
        )
        self.shortcuts.add_routines(
            routine(self.undo, 'STUDIO_UNDO', 'Undo last action', 'studio', CTRL + CharKey('Z')),
            routine(self.redo, 'STUDIO_REDO', 'Redo action', 'studio', CTRL + CharKey('Y')),
            # -----------------------------
            routine(self.open_new, 'STUDIO_NEW', 'Open new design', 'studio', CTRL + CharKey('n')),
            routine(self.open_file, 'STUDIO_OPEN', 'Open design from file', 'studio', CTRL + CharKey('o')),
            routine(self.save, 'STUDIO_SAVE', 'Save current design', 'studio', CTRL + CharKey('s')),
            routine(self.save_as, 'STUDIO_SAVE_AS', 'Save current design under a new file', 'studio',
                    CTRL + SHIFT + CharKey('s')),
            routine(self.get_help, 'STUDIO_HELP', 'Show studio help', 'studio', KeyMap.F(12)),
            routine(self.settings, 'STUDIO_SETTINGS', 'Open studio settings', 'studio', ALT + CharKey('s')),
            routine(restart, 'STUDIO_RESTART', 'Restart application', 'studio', BlankKey),
            routine(self._on_close, 'STUDIO_EXIT', 'Exit application', 'studio', CTRL + CharKey('q')),
            # ------------------------------
            routine(self.show_all_windows, 'FEATURE_SHOW_ALL', 'Show all feature windows', 'studio',
                    ALT + CharKey('a')),
            routine(self.close_all, 'FEATURE_CLOSE_ALL', 'Close all feature windows', 'studio', ALT + CharKey('x')),
            routine(lambda: self.close_all_on_side('right'),
                    'FEATURE_CLOSE_RIGHT', 'Close feature windows to the right', 'studio', ALT + CharKey('R')),
            routine(lambda: self.close_all_on_side('left'),
                    'FEATURE_CLOSE_LEFT', 'Close feature windows to the left', 'studio', ALT + CharKey('L')),
            routine(self.features_as_docked, 'FEATURE_DOCK_ALL', 'Dock all feature windows', 'studio',
                    ALT + CharKey('d')),
            routine(self.features_as_windows, 'FEATURE_UNDOCK_ALL', 'Undock all feature windows', 'studio',
                    ALT + CharKey('u')),
            routine(self.save_window_positions, 'FEATURE_SAVE_POS', 'Save window positions', 'studio',
                    ALT + SHIFT + CharKey('s')),
            # -----------------------------
            routine(self.preview, 'STUDIO_PREVIEW', 'Show preview', 'studio', KeyMap.F(5)),
            routine(self.close_preview, 'STUDIO_PREVIEW_CLOSE', 'Close any preview', 'studio', ALT + KeyMap.F(5)),
        )


def restart():
    actions.get_routine("STUDIO_EXIT").invoke()
    pref._release()
    # allow some time before starting
    time.sleep(2)
    python = sys.executable
    os.execl(python, python, sys.argv[0])


def main():
    # load resources first
    ResourceLoader.load()
    StudioApplication().mainloop()


if __name__ == "__main__":
    main()
