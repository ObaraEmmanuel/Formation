# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import functools
import os
import sys
import time
import tkinter
import webbrowser
from tkinter import filedialog

import tkinterDnD

from studio.feature.design import DesignContext, MultiSaveDialog
from studio.feature import FEATURES, StylePane
from studio.feature._base import BaseFeature, FeaturePane
from studio.tools import ToolManager
from studio.ui.widgets import SideBar
from studio.ui.about import about_window
from studio.preferences import Preferences, open_preferences
from studio.resource_loader import ResourceLoader
from studio.updates import Updater
from studio.context import BaseContext
import studio

from hoverset.ui.widgets import (
    Application, Frame, PanedWindow, Button,
    ActionNotifier, TabView, Label
)
from hoverset.ui.icons import get_icon_image
from hoverset.data.images import load_tk_image
from hoverset.util.execution import Action
from hoverset.data.utils import get_resource_path
from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.menu import MenuUtils, EnableIf, dynamic_menu, LoadLater
from hoverset.data import actions
from hoverset.data.keymap import ShortcutManager, CharKey, KeyMap, BlankKey
from hoverset.platform import platform_is, MAC

from formation import AppBuilder
from formation.formats import get_file_types, get_file_extensions

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
        self._left = FeaturePane("left", self._pane, **self.style.pane_vertical)
        self._center = PanedWindow(self._pane, **self.style.pane_vertical)
        self._right = FeaturePane("right", self._pane, **self.style.pane_vertical)

        self._bin = []
        self._clipboard = None
        self.current_preview = None

        self._pane.add(self._left, minsize=320, width=320, sticky='nswe', stretch='never')
        self._pane.add(self._center, minsize=400, stretch="always", sticky='nswe')
        self._pane.add(self._right, minsize=320, width=320, sticky='nswe', stretch='never')

        self._left.restore_size()
        self._right.restore_size()

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

        self.tool_manager = ToolManager(self)

        # -------------------------------------------- menu definition ------------------------------------------------
        self.menu_template = (EnableIf(
            lambda: self.selected,
            ("separator",),
            ("command", "copy", icon("copy", 14, 14), actions.get('STUDIO_COPY'), {}),
            ("command", "duplicate", icon("copy", 14, 14), actions.get('STUDIO_DUPLICATE'), {}),
            EnableIf(
                lambda: self._clipboard is not None,
                ("command", "paste", icon("clipboard", 14, 14), actions.get('STUDIO_PASTE'), {})
            ),
            ("command", "cut", icon("cut", 14, 14), actions.get('STUDIO_CUT'), {}),
            ("separator",),
            ("command", "delete", icon("delete", 14, 14), actions.get('STUDIO_DELETE'), {}),
        ),)

        self.menu_bar = MenuUtils.make_dynamic(
            ((
                 ("cascade", "formation", None, None, {"menu": (
                     ("command", "Restart", None, actions.get('STUDIO_RESTART'), {}),
                     ("separator", ),
                     ("command", "About Formation", icon("formation", 14, 14), lambda: about_window(self), {}),
                 ), "name": "apple"}),
             ) if platform_is(MAC) else ()) +
            (
                ("cascade", "File", None, None, {"menu": (
                    ("command", "New", icon("add", 14, 14), actions.get('STUDIO_NEW'), {}),
                    ("command", "Open", icon("folder", 14, 14), actions.get('STUDIO_OPEN'), {}),
                    ("cascade", "Recent", icon("clock", 14, 14), None, {"menu": self._create_recent_menu()}),
                    ("separator",),
                    EnableIf(
                        lambda: self.designer,
                        ("command", "Save", icon("save", 14, 14), actions.get('STUDIO_SAVE'), {}),
                        ("command", "Save As", icon("blank", 14, 14), actions.get('STUDIO_SAVE_AS'), {})
                    ),
                    EnableIf(
                        # more than one design contexts open
                        lambda: len([i for i in self.contexts if isinstance(i, DesignContext)]) > 1,
                        ("command", "Save All", icon("blank", 14, 14), actions.get('STUDIO_SAVE_ALL'), {})
                    ),
                    ("separator",),
                    ("command", "Settings", icon("settings", 14, 14), actions.get('STUDIO_SETTINGS'), {}),
                    ("command", "Restart", icon("blank", 14, 14), actions.get('STUDIO_RESTART'), {}),
                    ("command", "Exit", icon("close", 14, 14), actions.get('STUDIO_EXIT'), {}),
                )}),
                ("cascade", "Edit", None, None, {"menu": (
                    EnableIf(lambda: self.context and self.context.has_undo(),
                             ("command", "undo", icon("undo", 14, 14), actions.get('STUDIO_UNDO'), {})),
                    EnableIf(lambda: self.context and self.context.has_redo(),
                             ("command", "redo", icon("redo", 14, 14), actions.get('STUDIO_REDO'), {})),
                    *self.menu_template,
                )}),
                ("cascade", "Code", None, None, {"menu": (
                    EnableIf(
                        lambda: self.designer and self.designer.root_obj,
                        ("command", "Preview design", icon("play", 14, 14), actions.get('STUDIO_PREVIEW'), {}),
                        ("command", "close preview", icon("close", 14, 14), actions.get('STUDIO_PREVIEW_CLOSE'), {}),
                        ("separator", ),
                        EnableIf(
                            lambda: self.designer and self.designer.design_path,
                            ("command", "Reload design file", icon("rotate_clockwise", 14, 14),
                             actions.get('STUDIO_RELOAD'), {}),
                        ),
                    )
                )}),
                ("cascade", "View", None, None, {"menu": (
                    ("command", "show all panes", blank_img, actions.get('FEATURE_SHOW_ALL'), {}),
                    ("command", "close all panes", icon("close", 14, 14), actions.get('FEATURE_CLOSE_ALL'), {}),
                    ("command", "close all panes on the right", blank_img, actions.get('FEATURE_CLOSE_RIGHT'), {}),
                    ("command", "close all panes on the left", blank_img, actions.get('FEATURE_CLOSE_LEFT'), {}),
                    ("separator",),
                    ("command", "Undock all windows", blank_img, actions.get('FEATURE_UNDOCK_ALL'), {}),
                    ("command", "Dock all windows", blank_img, actions.get('FEATURE_DOCK_ALL'), {}),
                    ("separator",),
                    LoadLater(self.get_features_as_menu),
                    ("separator",),
                    EnableIf(
                        lambda: self.context,
                        ("command", "close tab", icon("close", 14, 14), actions.get('CONTEXT_CLOSE'), {}),
                        ("command", "close all tabs", blank_img, actions.get('CONTEXT_CLOSE_ALL'), {}),
                        EnableIf(
                            lambda: self.context and len(self.tab_view.tabs()) > 1,
                            ("command", "close other tabs", blank_img, actions.get('CONTEXT_CLOSE_OTHER'), {})
                        ),
                        EnableIf(
                            lambda: self.context and self.context._contexts_right(),
                            ("command", "close all tabs on the right", blank_img,
                             actions.get('CONTEXT_CLOSE_OTHER_RIGHT'), {})
                        )
                    ),
                    ("separator",),
                    ("command", "Save window positions", blank_img, actions.get('FEATURE_SAVE_POS'), {})
                )}),
                ("cascade", "Tools", None, None, {"menu": (LoadLater(self.tool_manager.get_tools_as_menu), )}),
                ("cascade", "Help", None, None, {"menu": (
                    ("command", "Help", icon('dialog_info', 14, 14), actions.get('STUDIO_HELP'), {}),
                    ("command", "Report issue", blank_img, self.report_issue, {}),
                    ("command", "Check for updates", icon("cloud", 14, 14), self._check_updates, {}),
                    ("separator",),
                    ("command", "About Formation", icon("formation", 14, 14), lambda: about_window(self), {}),
                )})
            ), self, self.style, False)

        self.config(menu=self.menu_bar)

        if platform_is(MAC):
            self.createcommand("tk::mac::ShowPreferences", lambda: actions.get('STUDIO_SETTINGS').invoke())
            self.createcommand("tk::mac::ShowHelp", lambda: actions.get('STUDIO_HELP').invoke())
            self.createcommand("tk::mac::Quit", lambda: actions.get('STUDIO_EXIT').invoke())

        self.features = []
        self.context = None
        self.contexts = []
        self.tab_view = TabView(self._center)
        self.tab_view.register_drop_target(tkinterDnD.FILE)
        self.tab_view.bind("<<Drop:File>>", lambda e: self.open_file(e.data))
        self.tab_view.malleable(True)
        self.tab_view.bind("<<TabSelectionChanged>>", self.on_context_switch)
        self.tab_view.bind("<<TabClosed>>", self.on_context_close)
        self.tab_view.bind("<<TabAdded>>", self.on_context_add)
        self.tab_view.bind("<<TabOrderChanged>>", lambda _: self.save_tab_status())
        self._center.add(self.tab_view, sticky='nswe')
        self._tab_view_empty = Label(
            self.tab_view, **self.style.text_passive, compound='top',
            image=get_icon_image("paint", 60, 60)
        )
        self._tab_view_empty.config(**self.style.bright)

        # install features
        for feature in FEATURES:
            self.install(feature)

        # common feature references
        self.style_pane = self.get_feature(StylePane)

        # initialize tools with everything ready
        self.tool_manager.initialize()

        self._ignore_tab_status = False
        self._startup()
        self._exit_failures = 0
        self._is_shutting_down = False

        self._left.restore_size()
        self._right.restore_size()

    def on_context_switch(self, _):
        selected = self.tab_view.selected
        if isinstance(self.context, BaseContext):
            self.context.on_context_unset()

        if isinstance(selected, BaseContext):
            self.context = selected
        else:
            self.context = None

        for feature in self.features:
            feature.on_context_switch()

        self.tool_manager.on_context_switch()

        if self.context:
            selected.on_context_set()

        # switch selection to that of the new context
        if self.designer:
            self.select(self.designer.current_obj, self.designer)
        else:
            self.select(None)
        self.save_tab_status()

    def on_context_close(self, context):
        if not self.tab_view.tabs():
            self._show_empty("Open a design file")
        if context in self.contexts:
            self.contexts.remove(context)
        for feature in self.features:
            feature.on_context_close(context)
        self.tool_manager.on_context_close(context)
        self.save_tab_status()

    def on_context_add(self, _):
        self._show_empty(None)

    def add_context(self, context, select=True):
        self.contexts.append(context)
        tab = self.tab_view.add(
            context, None, False, text=context.name, icon=context.icon, closeable=True
        )
        context.tab_handle = tab
        if select:
            self.tab_view.select(tab)
        context.on_context_mount()
        self.save_tab_status()

    def create_context(self, context, *args, select=True, **kwargs):
        new_context = context(self.tab_view, self, *args, **kwargs)
        self.add_context(new_context, select)
        return new_context

    def close_context(self):
        if self.context:
            self.context.close()

    def close_all_contexts(self):
        if self.check_unsaved_changes():
            for context in list(self.contexts):
                context.close(force=True)

    def close_other_contexts(self):
        if self.context:
            self.context.close_other()

    def close_other_contexts_right(self):
        if self.context:
            self.context.close_other_right()

    @property
    def designer(self):
        if isinstance(self.context, DesignContext):
            return self.context.designer

    def _show_empty(self, text):
        if text:
            self._tab_view_empty.lift()
            self._tab_view_empty['text'] = text
            self._tab_view_empty.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self._tab_view_empty.place_forget()

    def _startup(self):
        on_startup = pref.get("studio::on_startup")
        if on_startup == "new":
            self.open_new()
        elif on_startup == "recent":
            self.restore_tabs()
        else:
            self._show_empty("Open a design file")

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
            geometry=self.geometry(),
            state=self._get_window_state(),  # window state either zoomed or normal
        ))
        self._left.save_size()
        self._right.save_size()

    def _restore_position(self):
        pos = pref.get("studio::pos")
        state = pos.get('state', 'zoomed')
        self._set_window_state(state)
        if state == 'normal' and pos.get('geometry'):
            self.geometry(pos['geometry'])

    def new_action(self, action: Action):
        """
        Register a undo redo point
        :param action: An action object implementing undo and redo methods
        :return:
        """
        if self.context:
            self.context.new_action(action)

    def undo(self):
        if self.context:
            self.context.undo()

    def redo(self):
        if self.context:
            self.context.redo()

    def last_action(self):
        if self.context:
            return self.context.last_action()

    def pop_last_action(self, key=None):
        if self.context:
            self.context.pop_last_action(key)

    def copy(self):
        if self.designer and self.selected:
            # store the current object as  node in the clipboard
            self._clipboard = self.designer.as_node(self.selected)

    def install_status_widget(self, widget_class, *args, **kwargs):
        widget = widget_class(self._statusbar, *args, **kwargs)
        widget.pack(side='right', padx=2, fill='y')
        return widget

    def get_pane_info(self, pane):
        return self._panes.get(pane, [self._right, self._right_bar])

    def paste(self):
        if self.designer and self._clipboard is not None:
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
            path = filedialog.askopenfilename(parent=self, filetypes=get_file_types())
        elif not os.path.exists(path):
            MessageDialog.show_error(
                parent=self,
                title="Missing File",
                message="File {} does not exist".format(path),
            )
            return
        elif path.split(".")[-1] not in get_file_extensions():
            MessageDialog.show_error(
                parent=self,
                title="Unsupported type",
                message=f"File {path} is not of a supported file type ({get_file_extensions()}).",
            )
            return
        if path:
            # find if path is already open on the designer
            for context in self.contexts:
                if isinstance(context, DesignContext) and context.path == path:
                    # path is open, select
                    context.select()
                    break
            else:
                self.create_context(DesignContext, path)
                self.set_path(path)
                pref.update_recent(path)

    def open_recent(self, path):
        self.open_file(path)

    def open_new(self):
        context = self.create_context(DesignContext)
        self.set_path(context.name)

    def save(self):
        if self.designer:
            path = self.context.save()
            if path:
                self.set_path(path)
                self.save_tab_status()
                pref.update_recent(path)

    def save_as(self):
        if self.designer:
            path = self.context.save(new_path=True)
            if path:
                self.set_path(path)
                self.save_tab_status()
                pref.update_recent(path)

    def save_all(self):
        contexts = [
            i for i in self.contexts if isinstance(i, DesignContext) and i.designer.has_changed()
        ]
        for context in contexts:
            if context.save() is None:
                # save has been cancelled
                break

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
        if not pane.panes():
            pane.hide()
        else:
            pane.show()

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
        if self.designer and source != self.designer:
            # Select from the designer explicitly so the selection does not end up being re-fired
            self.designer.select(widget, True)
        for feature in self.features:
            if feature != source:
                feature.on_select(widget)
        self.tool_manager.on_select(widget)

    def add(self, widget, parent=None):
        for feature in self.features:
            feature.on_widget_add(widget, parent)
        self.tool_manager.on_widget_add(widget, parent)

    def widget_modified(self, widget1, source=None, widget2=None):
        for feature in self.features:
            if feature != source:
                feature.on_widget_change(widget1, widget2)
        if self.designer and self.designer != source:
            self.designer.on_widget_change(widget1, widget2)
        self.tool_manager.on_widget_change(widget1, widget2)

    def widget_layout_changed(self, widget):
        for feature in self.features:
            feature.on_widget_layout_change(widget)
        self.tool_manager.on_widget_layout_change(widget)

    def delete(self, widget=None, source=None):
        widget = self.selected if widget is None else widget
        if widget is None:
            return
        if self.selected == widget:
            self.select(None)
        if self.designer and source != self.designer:
            self.designer.delete(widget)
        for feature in self.features:
            feature.on_widget_delete(widget)
        self.tool_manager.on_widget_delete(widget)

    def cut(self, widget=None, source=None):
        if not self.designer:
            return
        widget = self.selected if widget is None else widget
        if not widget:
            return
        if self.selected == widget:
            self.select(None)
        self._clipboard = self.designer.as_node(widget)
        if source != self.designer:
            self.designer.delete(widget, True)
        for feature in self.features:
            feature.on_widget_delete(widget, True)
        self.tool_manager.on_widget_delete(widget)

    def duplicate(self):
        if self.designer and self.selected:
            self.designer.paste(self.designer.as_node(self.selected))

    def on_restore(self, widget):
        for feature in self.features:
            feature.on_widget_restore(widget)

    def on_feature_change(self, new, old):
        self.features.insert(self.features.index(old), new)
        self.features.remove(old)

    def on_session_clear(self, source):
        for feature in self.features:
            if feature != source:
                feature.on_session_clear()
        self.tool_manager.on_session_clear()

    def restore_tabs(self):
        # ignore all tab status changes as we restore tabs
        self._ignore_tab_status = True
        first_context = None
        has_select = False
        for context_dat in self.pref.get("studio::prev_contexts"):
            context = self.create_context(
                context_dat["class"],
                *context_dat["args"],
                select=context_dat["selected"],
                **context_dat["kwargs"]
            )
            has_select = has_select or context_dat["selected"]
            first_context = context if first_context is None else first_context
            context.deserialize(context_dat["data"])
        if not first_context:
            self._show_empty("Open a design file")
        elif not has_select:
            first_context.select()
        self._ignore_tab_status = False

    def save_tab_status(self):
        if self._ignore_tab_status:
            return
        status = []
        for tab in self.tab_view._tab_order:
            context = self.tab_view._tabs[tab]
            if isinstance(context, BaseContext) and context.can_persist():
                data = context.serialize()
                data["selected"] = self.context == context
                status.append(data)
        self.pref.set("studio::prev_contexts", status)

    def check_unsaved_changes(self, check_contexts=None):
        check_contexts = self.contexts if check_contexts is None else check_contexts
        unsaved = [
            i for i in check_contexts if isinstance(i, DesignContext) and i.designer.has_changed()
        ]
        if len(unsaved) > 1:
            contexts = MultiSaveDialog.ask_save(self, self, check_contexts)
            if contexts is None:
                return False
            for context in contexts:
                if context.designer.save() is None:
                    return False
        elif unsaved:
            return unsaved[0].designer.on_app_close()
        elif unsaved is None:
            return False
        return True

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
        self.current_preview = AppBuilder(node=self.designer.to_tree(), path=self.designer.design_path)

    def close_preview(self):
        if self.current_preview:
            try:
                self.current_preview._app.destroy()
            except tkinter.TclError:
                pass
            self.current_preview = None

    def reload(self):
        if self.designer:
            self.designer.reload()

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
        """ Return ``True`` if exit successful otherwise ``False`` """
        if self._is_shutting_down:
            # block multiple close attempts
            return
        self._is_shutting_down = True
        try:
            self._save_position()
            # pass the on window close event to the features
            for feature in self.features:
                # if any feature returns false abort shut down
                feature.save_window_pos()
                if not feature.on_app_close():
                    self._is_shutting_down = False
                    return False
            if not self.tool_manager.on_app_close() or not self.check_unsaved_changes():
                self._is_shutting_down = False
                return False
            self.quit()
            return True
        except Exception:
            self._exit_failures += 1
            if self._exit_failures >= 2:
                force = self._force_exit_prompt()
                if force:
                    # exit by all means necessary
                    sys.exit(1)
            self._is_shutting_down = False
            return False

    def get_help(self):
        # Entry point for studio help functionality
        webbrowser.open("https://formation-studio.readthedocs.io/en/latest/")

    def report_issue(self):
        # open issues on github
        webbrowser.open("https://github.com/ObaraEmmanuel/Formation/issues")

    def settings(self):
        open_preferences(self)

    def _coming_soon(self):
        MessageDialog.show_info(
            parent=self,
            title="Coming soon",
            message="We are working hard to bring this feature to you. Hang in there.",
            icon="clock"
        )

    def _open_debugtools(self):
        from studio.debugtools.debugger import Debugger

        # close previous process if any
        proc = getattr(self, "_dbg_process", None)
        if proc:
            proc.terminate()

        path = filedialog.askopenfilename(parent=self, filetypes=(("python", ".py .pyw .pyc"), ))
        if path:
            self._dbg_process = Debugger.run_process(path)

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
            routine(self.duplicate, 'STUDIO_DUPLICATE', 'Duplicate selected widget', 'studio', CTRL + CharKey('d')),
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
            routine(self.save_all, 'STUDIO_SAVE_ALL', 'Save all open designs', 'studio', CTRL + ALT + CharKey('s')),
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
            routine(self.close_context, 'CONTEXT_CLOSE', 'Close tab', 'studio', CTRL + CharKey('T')),
            routine(self.close_all_contexts, 'CONTEXT_CLOSE_ALL', 'Close all tabs', 'studio',
                    CTRL + ALT + CharKey('T')),
            routine(self.close_other_contexts, 'CONTEXT_CLOSE_OTHER', 'Close other tabs', 'studio', BlankKey),
            routine(self.close_other_contexts_right, 'CONTEXT_CLOSE_OTHER_RIGHT', 'Close all tabs on the right',
                    'studio', BlankKey),
            # -----------------------------
            routine(self.preview, 'STUDIO_PREVIEW', 'Show preview', 'studio', KeyMap.F(5)),
            routine(self.close_preview, 'STUDIO_PREVIEW_CLOSE', 'Close any preview', 'studio', ALT + KeyMap.F(5)),
            routine(self.reload, 'STUDIO_RELOAD', 'Reload current design', 'studio', CTRL + CharKey('R'))
        )


def restart():
    exit_success = actions.get_routine("STUDIO_EXIT").invoke()
    if not exit_success:
        return
    pref._release()
    # allow some time before starting
    time.sleep(2)
    python = sys.executable
    os.execl(python, python, sys.argv[0])


def main():
    # load resources first
    ResourceLoader.load(pref)
    StudioApplication(className='Formation Studio').mainloop()


if __name__ == "__main__":
    main()
