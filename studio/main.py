# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import functools
import os
import subprocess
import sys
import time
import tkinter
import webbrowser
from tkinter import filedialog, ttk

import platformdirs
from tkinterdnd2 import DND_FILES

# force locale setting
from studio.i18n import _
import studio
from formation.formats import get_file_types, get_file_extensions
from formation.themes import get_themes, get_theme
from hoverset.data import actions
from hoverset.data.images import load_tk_image
from hoverset.data.keymap import ShortcutManager, CharKey, KeyMap, BlankKey, Symbol
from hoverset.data.utils import get_resource_path
from hoverset.platform import platform_is, MAC, WINDOWS
from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.icons import get_icon_image
from hoverset.ui.menu import MenuUtils, EnableIf, dynamic_menu, LoadLater, ShowIf
from hoverset.ui.widgets import (
    Application, Frame, PanedWindow, Button,
    ActionNotifier, TabView, Label
)
from hoverset.util.execution import Action
from hoverset.data.i18n import set_locale
from studio.context import BaseContext
from studio.feature import FEATURES, StylePane
from studio.feature._base import BaseFeature, FeaturePane
from studio.feature.design import DesignContext, MultiSaveDialog
from studio.preferences import Preferences, open_preferences
from studio.resource_loader import ResourceLoader
from studio.selection import Selection
from studio.tools import ToolManager
from studio.ui import geometry
from studio.ui.about import about_window
from studio.ui.widgets import SideBar, ThemeBar
from studio.updates import Updater
from studio.external import init_externals

pref = Preferences.acquire()


class StudioApplication(Application):
    if platform_is(WINDOWS):
        ICON_PATH = get_resource_path(studio, "resources/images/formation.ico")
    else:
        ICON_PATH = get_resource_path(studio, "resources/images/formation_icon.png")
    THEME_PATH = pref.get("resource::theme")
    dirs = platformdirs.AppDirs(appname="formation", appauthor="hoverset")

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        # Load icon asynchronously to prevent issues which have been known to occur when loading it synchronously
        self.icon_image = load_tk_image(self.ICON_PATH)
        self.load_styles(self.THEME_PATH)
        self.iconphoto(True, self.icon_image)
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

        self._pane.add(self._left, minsize=360, width=320, sticky='nswe', stretch='never')
        self._pane.add(self._center, stretch="always", sticky='nswe')
        self._pane.add(self._right, minsize=360, width=320, sticky='nswe', stretch='never')

        self._left.restore_size()
        self._right.restore_size()

        self._panes = {
            "left": (self._left, self._left_bar),
            "right": (self._right, self._right_bar),
            "center": (self._center, None)
        }

        icon = get_icon_image

        def invoke(key):
            return lambda e: actions.get(key).invoke()

        self.actions = (
            ("Delete", icon("remove", 20, 20), invoke("STUDIO_DELETE"), _("Delete selected widgets")),
            ("Undo", icon("undo", 20, 20), invoke("STUDIO_UNDO"), _("Undo action")),
            ("Redo", icon("redo", 20, 20), invoke("STUDIO_REDO"), _("Redo action")),
            ("Cut", icon("cut", 20, 20), invoke("STUDIO_CUT"), _("Cut selected widgets")),
            ("separator",),
            ("Fullscreen", icon("fullscreen", 20, 20), lambda e: self.close_all(), _("Design mode")),
            ("Separate", icon("undock", 20, 20), lambda e: self.features_as_windows(),
             _("Open features in window mode")),
            ("Dock", icon("dock_horizontal", 15, 15), lambda e: self.features_as_docked(),
             _("Dock all features")),
            ("separator",),
            ("New", icon("add", 20, 20), lambda e: self.open_new(), _("New design")),
            ("Save", icon("save", 20, 20), lambda e: self.save(), _("Save design")),
            ("Preview", icon("play", 20, 20), lambda e: self.preview(), _("Preview design")),
        )

        self.init_toolbar()
        self._selection = Selection(self)
        # set the image option to blank if there is no image for the menu option
        self.blank_img = blank_img = icon("blank", 18, 18)

        self.tool_manager = ToolManager(self)

        # -------------------------------------------- menu definition ------------------------------------------------
        self.menu_template = (EnableIf(
            lambda: bool(self.selection),
            ("separator",),
            ("command", _("copy"), icon("copy", 18, 18), actions.get('STUDIO_COPY'), {}),
            ("command", _("duplicate"), icon("blank", 18, 18), actions.get('STUDIO_DUPLICATE'), {}),
            EnableIf(
                lambda: self._clipboard is not None and len(self.selection),
                ("command", _("paste"), icon("clipboard", 18, 18), actions.get('STUDIO_PASTE'), {})
            ),
            ("command", _("cut"), icon("cut", 18, 18), actions.get('STUDIO_CUT'), {}),
            ("separator",),
            ShowIf(
                lambda: self.selection and self.selection.not_toplevel() and self.selection.is_visual() and self.selection[0].layout.layout_strategy.stacking_support,
                EnableIf(
                    lambda: self.selection.is_same_parent(),
                    ("command", _("send to back"), icon("send_to_back", 18, 18), actions.get('STUDIO_BACK'), {}),
                    ("command", _("bring to front"), icon("bring_to_front", 18, 18), actions.get('STUDIO_FRONT'), {}),
                    ("command", _("back one step"), icon("send_to_back", 18, 18), actions.get('STUDIO_BACK_1'), {}),
                    ("command", _("forward one step"), icon("bring_to_front", 18, 18), actions.get('STUDIO_FRONT_1'), {}),
                ),
            ),
            ("separator",),
            ("command", _("delete"), icon("delete", 18, 18), actions.get('STUDIO_DELETE'), {}),
        ),)

        self.menu_bar = MenuUtils.make_dynamic(
            ((
                 ("cascade", _("formation"), None, None, {"menu": (
                     ("command", _("Restart"), None, actions.get('STUDIO_RESTART'), {}),
                     ("separator", ),
                     ("command", _("About Formation"), icon("formation", 18, 18), lambda: about_window(self), {}),
                 ), "name": "apple"}),
             ) if platform_is(MAC) else ()) +
            (
                ("cascade", _("File"), None, None, {"menu": (
                    ("command", _("New"), icon("add", 18, 18), actions.get('STUDIO_NEW'), {}),
                    ("command", _("Open"), icon("folder", 18, 18), actions.get('STUDIO_OPEN'), {}),
                    ("cascade", _("Recent"), icon("recent", 18, 18), None, {"menu": self._create_recent_menu()}),
                    ("separator",),
                    EnableIf(
                        lambda: self.designer,
                        ("command", _("Save"), icon("save", 18, 18), actions.get('STUDIO_SAVE'), {}),
                        ("command", _("Save As"), icon("blank", 18, 18), actions.get('STUDIO_SAVE_AS'), {})
                    ),
                    EnableIf(
                        # more than one design contexts open
                        lambda: len([i for i in self.contexts if isinstance(i, DesignContext)]) > 1,
                        ("command", _("Save All"), icon("blank", 18, 18), actions.get('STUDIO_SAVE_ALL'), {})
                    ),
                    ("separator",),
                    ("command", _("Settings"), icon("settings", 18, 18), actions.get('STUDIO_SETTINGS'), {}),
                    ("command", _("Restart"), icon("blank", 18, 18), actions.get('STUDIO_RESTART'), {}),
                    ("command", _("Exit"), icon("close", 18, 18), actions.get('STUDIO_EXIT'), {}),
                )}),
                ("cascade", _("Edit"), None, None, {"menu": (
                    EnableIf(lambda: self.context and self.context.has_undo(),
                             ("command", _("undo"), icon("undo", 18, 18), actions.get('STUDIO_UNDO'), {})),
                    EnableIf(lambda: self.context and self.context.has_redo(),
                             ("command", _("redo"), icon("redo", 18, 18), actions.get('STUDIO_REDO'), {})),
                    *self.menu_template,
                )}),
                ("cascade", _("Code"), None, None, {"menu": (
                    EnableIf(
                        lambda: self.designer and self.designer.root_obj,
                        ("command", _("Preview design"), icon("play", 18, 18), actions.get('STUDIO_PREVIEW'), {}),
                        ("command", _("close preview"), icon("close", 18, 18), actions.get('STUDIO_PREVIEW_CLOSE'), {}),
                        ("separator", ),
                        EnableIf(
                            lambda: self.designer and self.designer.design_path,
                            ("command", _("Reload design file"), icon("reload", 18, 18),
                             actions.get('STUDIO_RELOAD'), {}),
                        ),
                    )
                )}),
                ("cascade", _("View"), None, None, {"menu": (
                    ("command", _("show all panes"), blank_img, actions.get('FEATURE_SHOW_ALL'), {}),
                    ("command", _("close all panes"), icon("close", 18, 18), actions.get('FEATURE_CLOSE_ALL'), {}),
                    ("command", _("close all panes on the right"), blank_img, actions.get('FEATURE_CLOSE_RIGHT'), {}),
                    ("command", _("close all panes on the left"), blank_img, actions.get('FEATURE_CLOSE_LEFT'), {}),
                    ("separator",),
                    ("command", _("Undock all windows"), blank_img, actions.get('FEATURE_UNDOCK_ALL'), {}),
                    ("command", _("Dock all windows"), blank_img, actions.get('FEATURE_DOCK_ALL'), {}),
                    ("separator",),
                    LoadLater(self.get_features_as_menu),
                    ("separator",),
                    EnableIf(
                        lambda: self.context,
                        ("command", _("close tab"), icon("close", 18, 18), actions.get('CONTEXT_CLOSE'), {}),
                        ("command", _("close all tabs"), blank_img, actions.get('CONTEXT_CLOSE_ALL'), {}),
                        EnableIf(
                            lambda: self.context and len(self.tab_view.tabs()) > 1,
                            ("command", _("close other tabs"), blank_img, actions.get('CONTEXT_CLOSE_OTHER'), {})
                        ),
                        EnableIf(
                            lambda: self.context and self.context._contexts_right(),
                            ("command", _("close all tabs on the right"), blank_img,
                             actions.get('CONTEXT_CLOSE_OTHER_RIGHT'), {})
                        )
                    ),
                    ("separator",),
                    ("command", _("Save window positions"), blank_img, actions.get('FEATURE_SAVE_POS'), {})
                )}),
                ("cascade", _("Tools"), None, None, {"menu": (LoadLater(self.tool_manager.get_tools_as_menu), )}),
                ("cascade", _("Help"), None, None, {"menu": (
                    ("command", _("Help"), icon('dialog_info', 18, 18), actions.get('STUDIO_HELP'), {}),
                    ("command", _("Report issue"), blank_img, self.report_issue, {}),
                    ("command", _("Check for updates"), blank_img, self._check_updates, {}),
                    ("separator",),
                    ("command", _("About Formation"), icon("formation", 18, 18), lambda: about_window(self), {}),
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
        self.tab_view.drop_target_register(DND_FILES)
        self.tab_view.dnd_bind("<<Drop>>", lambda e: self.open_file(e.data))
        self.tab_view.malleable(True)
        self.tab_view.bind("<<TabSelectionChanged>>", self.on_context_switch)
        self.tab_view.bind("<<TabClosed>>", self.on_context_close)
        self.tab_view.bind("<<TabAdded>>", self.on_context_add)
        self.tab_view.bind("<<TabOrderChanged>>", lambda _: self.save_tab_status())
        self._center.add(self.tab_view, sticky='nswe')
        self._tab_view_empty = Label(
            self.tab_view, **self.style.text_passive, compound='top',
            image=get_icon_image("design", 60, 60)
        )
        self._tab_view_empty.config(**self.style.bright)

        # install features
        for feature in FEATURES:
            self.install(feature)

        # common feature references
        self.style_pane = self.get_feature(StylePane)

        # initialize tools with everything ready
        self.tool_manager.initialize()

        if pref.get("studio::allow_thirdparty"):
            # initialize externals
            init_externals(self)

        self._ignore_tab_status = False
        self._startup()
        self._exit_failures = 0
        self._is_shutting_down = False

        self._left.restore_size()
        self._right.restore_size()

        if pref.get("studio::check_updates"):
            Updater.check_silent(self)

        self._pane_drag_hint = Label(self, **self.style.text_small)
        self._pane_drag_hint.config(**self.style.text_bright, **self.style.accent)
        self._active_pane = None
        self._active_bar = None
        self._pane_drop_side = None

    @property
    def selection(self):
        return self._selection

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
            self.selection.set(self.designer.selected)
        else:
            self.selection.clear()
        self.save_tab_status()

    def on_context_close(self, context):
        if not self.tab_view.tabs():
            self._show_empty(_("Open a design file"))
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
        index = None
        if self.tab_view.selected is not None:
            index = self.tab_view.index(self.tab_view.selected.tab_handle) + 1
        tab = self.tab_view.add(
            context, index, False, text=context.name, icon=context.icon, closeable=True
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

    @property
    def color_data(self):
        if self.designer:
            return self.designer.color_data

    def _extract_descendants(self, widget, widget_set):
        for child in widget.all_children:
            widget_set.add(child)
            self._extract_descendants(child, widget_set)

    def get_widgets(self, criteria=None):
        if not self.designer:
            return

        if criteria is None:
            return self.designer.objects

        widgets = None
        for widget in self.selection:
            descendants = set()
            if criteria == "descendant":
                self._extract_descendants(widget, descendants)
            elif criteria == "child":
                descendants = set(widget.all_children)
            if widgets:
                widgets &= descendants
            else:
                widgets = descendants

        return widgets

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
            self._show_empty(_("Open a design file"))

    def _get_window_state(self):
        try:
            if self.wm_attributes("-zoomed"):
                return 'zoomed'
            return 'normal'
        except tkinter.TclError:
            # works for windows and mac os
            return self.state()

    def _set_window_state(self, state):
        try:
            # works in windows and mac os
            self.state(state)
        except tkinter.TclError:
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

    def install_status_widget(self, widget_class, *args, **kwargs):
        widget = widget_class(self._statusbar, *args, **kwargs)
        widget.pack(side='right', padx=2, fill='y')
        return widget

    def send_back(self, steps=0):
        if self.designer and self.selection:
            self.designer.send_back(steps)

    def bring_front(self, steps=0):
        if self.designer and self.selection:
            self.designer.bring_front(steps)

    def get_pane_info(self, pane):
        return self._panes.get(pane, [self._right, self._right_bar])

    def close_all_on_side(self, side):
        for feature in self.features:
            if feature._side.get() == side:
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

        Frame(self._toolbar, width=1, bg=self.style.colors.get("primarydarkaccent")).pack(
            side='left', fill='y', pady=3, padx=5)

        self.theme_bar = ThemeBar(self._toolbar)
        self.theme_bar.pack(side='left', padx=10)
        self.theme_bar.load_themes(list(get_themes().values()))
        self.theme_bar.set(get_theme(ttk.Style().theme_use()))

    def uninstall(self, feature):
        self.features.remove(feature)
        feature.bar.remove(feature)
        feature.pane.forget(feature)
        self._adjust_pane(feature.pane)

    def get_pane_bar(self, side):
        if side in self._panes:
            return self._panes.get(side, (self._left, self._left_bar))

    def on_pane_drag(self, pane, x, y):
        active_pane = None
        for feature in self.features:
            if feature == pane or not feature.is_visible.get() or feature.get_pref('mode') == 'window':
                continue

            bounds = geometry.absolute_bounds(feature)
            if geometry.is_pos_within(bounds, (x, y)):
                active_pane = feature
                h = bounds[3] - bounds[1]
                if y - bounds[1] < h * 0.3:
                    self._pane_drag_hint.config(text=_("Place above"))
                    self._pane_drag_hint.lift()
                    self._pane_drag_hint.place(in_=feature, relx=0.5, rely=0, anchor='n')
                    feature.configure(self.style.highlight_bright)
                    self._pane_drop_side = 'n'
                elif bounds[3] - y < h * 0.3:
                    self._pane_drag_hint.config(text=_("Place below"))
                    self._pane_drag_hint.lift()
                    self._pane_drag_hint.place(in_=feature, relx=0.5, rely=1, anchor='s')
                    feature.configure(self.style.highlight_bright)
                    self._pane_drop_side = 's'
                else:
                    self._pane_drop_side = ''
                    self._pane_drag_hint.place_forget()
                    feature.configure(self.style.highlight_passive)
                break

        if active_pane is None:
            active_bar = None
            for bar in (self._left_bar, self._right_bar):
                bounds = geometry.absolute_bounds(bar)
                if geometry.is_pos_within(bounds, (x, y)):
                    active_bar = bar
                    bar.configure(self.style.highlight_bright)
                else:
                    bar.configure(self.style.no_highlight)

            if active_bar != self._active_bar:
                if self._active_bar:
                    self._active_bar.configure(self.style.no_highlight)
                self._active_bar = active_bar
        elif self._active_bar:
            self._active_bar.configure(self.style.no_highlight)
            self._active_bar = None

        if active_pane != self._active_pane:
            if self._active_pane:
                self._active_pane.configure(self.style.no_highlight)
            if not active_pane:
                self._pane_drag_hint.place_forget()
            self._active_pane = active_pane

    def on_pane_drop(self, pane, x, y):
        # re-calculate drop targets just in case
        self.on_pane_drag(pane, x, y)
        self._pane_drag_hint.place_forget()
        if self._active_pane:
            self._active_pane.configure(self.style.no_highlight)
            if self._pane_drop_side:
                pane.reposition(
                    self._active_pane.get_pref('side'),
                    self._active_pane,
                    self._pane_drop_side,
                    True
                )
            else:
                self._drop_as_window(pane, x, y)
        elif self._active_bar:
            self._active_bar.configure(self.style.no_highlight)
            pane.reposition(
                "left" if self._active_bar == self._left_bar else "right",
                force_dock=True
            )
        else:
            self._drop_as_window(pane, x, y)

        self._active_pane = None
        self._active_bar = None

    def _drop_as_window(self, feature, x, y):
        bounds = geometry.absolute_bounds(feature._header)
        if not geometry.is_pos_within(bounds, (x, y)):
            feature.open_as_window((x, y))

    def reposition(self, feature: BaseFeature, side, target=None, position=None, force_dock=False):
        if self.get_pane_bar(side):
            pane, bar = self.get_pane_bar(side)
            feature.bar.remove(feature)
            feature.pane.forget(feature)
            self._adjust_pane(feature.pane)
            feature.bar = bar
            feature.pane = pane
            if force_dock and feature.get_pref("mode") == "window":
                feature.open_as_docked()

            if feature.get_pref("mode") == "docked":
                if target:
                    if position == "n":
                        pane.add(feature, before=target, minsize=300)
                    else:
                        pane.add(feature, after=target, minsize=300)
                else:
                    pane.add(feature, minsize=300)

            feature.set_pref("side", side)
            bar.add_feature(feature)

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
            if feature.is_visible.get():
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
        path = path or _("untitled")
        self.title("Formation studio" + " - " + str(path))

    @dynamic_menu
    def _create_recent_menu(self, menu):
        # Dynamically create recent file menu every time menu is posted
        menu.image = get_icon_image("close", 18, 18)
        menu.config(**self.style.context_menu)
        recent = pref.get_recent()
        for path, label in recent:
            menu.add_command(
                label=label,
                command=functools.partial(self.open_recent, path),
                image=self.blank_img, compound='left',
            )
        menu.add_command(
            label=_("Clear"), image=menu.image, command=pref.clear_recent,
            compound="left"
        )

    def open_file(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(parent=self, filetypes=get_file_types())
        elif not os.path.exists(path):
            MessageDialog.show_error(
                parent=self,
                title=_("Missing File"),
                message=_("File {} does not exist").format(path),
            )
            return
        elif path.split(".")[-1] not in get_file_extensions():
            MessageDialog.show_error(
                parent=self,
                title=_("Unsupported type"),
                message=_("File {path} is not of a supported file type ({typ}).").format(
                    path=path, typ=get_file_extensions()
                )
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
                 f.display_name, None,  # Label, image
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

    def add(self, widget, parent=None):
        for feature in self.features:
            feature.on_widget_add(widget, parent)

        self.tool_manager.on_widget_add(widget, parent)

    def widgets_modified(self, widgets, source=None):
        for feature in self.features:
            if feature != source:
                feature.on_widgets_change(widgets)
        if self.designer and self.designer != source:
            self.designer.on_widgets_change(widgets)

        self.tool_manager.on_widgets_change(widgets)

    def widgets_layout_changed(self, widgets):
        for feature in self.features:
            feature.on_widgets_layout_change(widgets)

        self.tool_manager.on_widgets_layout_change(widgets)

    def reorder_widgets(self, indices, source=None):
        for feature in self.features:
            if feature != source:
                feature.on_widgets_reorder(indices)

        self.tool_manager.on_widgets_reorder(indices)

    def make_clipboard(self, widgets):
        bounds = geometry.overall_bounds([w.get_bounds() for w in widgets])
        data = []
        for widget in widgets:
            data.append((
                self.designer.as_node(widget),
                geometry.relative_to_bounds(widget.get_bounds(), bounds),
            ))
        return data

    def set_clipboard(self, data, handler=None, key=None):
        self._clipboard = {
            "key": key,
            "data": data,
            "handler": self.designer.paste if handler is None else handler
        }

    def get_clipboard(self, key=None):
        if self._clipboard is None:
            return None
        if self._clipboard.get("key") == key:
            return self._clipboard["data"]

    def copy(self):
        if self.designer and self.selection:
            # store the current objects as  nodes in the clipboard
            self.set_clipboard(self.make_clipboard(self.selection.compact()), key="widget")
        pass

    def paste(self):
        if self.designer and self._clipboard is not None:
            if self._clipboard.get("handler"):
                self._clipboard["handler"](self._clipboard["data"])

    def delete(self, widgets=None, source=None):
        widgets = list(self.selection.compact()) if widgets is None else widgets
        if not widgets:
            return

        if any(widget in self.selection for widget in widgets):
            self.selection.clear()

        if self.designer and source != self.designer:
            self.designer.delete(widgets)

        for feature in self.features:
            feature.on_widgets_delete(widgets)

        self.tool_manager.on_widgets_delete(widgets)

    def cut(self, widgets=None, source=None):
        if not self.designer:
            return

        widgets = list(self.selection.compact()) if widgets is None else widgets
        if not widgets:
            return

        if any(widget in self.selection for widget in widgets):
            self.selection.clear()

        self.set_clipboard(self.make_clipboard(widgets))
        if source != self.designer:
            self.designer.delete(widgets)
        for feature in self.features:
            feature.on_widgets_delete(widgets, True)

        self.tool_manager.on_widgets_delete(widgets)

    def duplicate(self):
        if self.designer and self.selection:
            self.designer.paste(self.make_clipboard(self.selection.compact()))

    def on_restore(self, widgets):
        for feature in self.features:
            feature.on_widgets_restore(widgets)

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
            self._show_empty(_("Open a design file"))
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
                title=_('Empty design'),
                message=_('There is nothing to preview. Please add a root widget'))
            return
        # close previous preview if any
        self.close_preview()
        # extract extension from path
        path = self.designer.design_path or ''
        _, ext = os.path.splitext(path)
        ext = ext or '.json'
        path = os.path.join(self.dirs.user_cache_dir, f"temp_design{ext}")
        self.designer.to_tree().write(path)
        self.current_preview = subprocess.Popen([
            sys.executable, "-m", "formation",
            path, os.path.dirname(self.designer.design_path or '')
        ])

    def close_preview(self):
        if self.current_preview:
            try:
                self.current_preview.terminate()
            except tkinter.TclError:
                pass
            self.current_preview = None

    def reload(self):
        if self.designer:
            self.designer.reload()

    def _force_exit_prompt(self):
        return MessageDialog.builder(
            {"text": _("Force exit"), "value": True, "focus": True},
            {"text": _("Return to app"), "value": False},
            wait=True,
            title=_("Exit Failure"),
            message=_("An internal failure is preventing the app from exiting. Force exit?"),
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
            title=_("Coming soon"),
            message=_("We are working hard to bring this feature to you. Hang in there."),
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
            routine(self.cut, 'STUDIO_CUT', _('Cut selected widgets'), 'studio', CTRL + CharKey('x')),
            routine(self.copy, 'STUDIO_COPY', _('Copy selected widgets'), 'studio', CTRL + CharKey('c')),
            routine(self.paste, 'STUDIO_PASTE', _('Paste selected widgets'), 'studio', CTRL + CharKey('v')),
            routine(self.delete, 'STUDIO_DELETE', _('Delete selected widgets'), 'studio', KeyMap.DELETE),
            routine(self.duplicate, 'STUDIO_DUPLICATE', _('Duplicate selected widgets'), 'studio', CTRL + CharKey('d')),
        )
        self.shortcuts.add_routines(
            routine(self.undo, 'STUDIO_UNDO', _('Undo last action'), 'studio', CTRL + CharKey('Z')),
            routine(self.redo, 'STUDIO_REDO', _('Redo action'), 'studio', CTRL + CharKey('Y')),
            routine(self.send_back, 'STUDIO_BACK', _('Send selected widgets to back'), 'studio', Symbol(']')),
            routine(self.bring_front, 'STUDIO_FRONT', _('Bring selected widgets to front'), 'studio', Symbol('[')),
            routine(
                lambda: self.send_back(1),
                'STUDIO_BACK_1', _('Move selected widgets back one step'), 'studio', CTRL + Symbol(']')),
            routine(
                lambda: self.bring_front(1),
                'STUDIO_FRONT_1', _('Bring selected widgets up one step'), 'studio', CTRL + Symbol('[')),
            # -----------------------------
            routine(self.open_new, 'STUDIO_NEW', _('Open new design'), 'studio', CTRL + CharKey('n')),
            routine(self.open_file, 'STUDIO_OPEN', _('Open design from file'), 'studio', CTRL + CharKey('o')),
            routine(self.save, 'STUDIO_SAVE', _('Save current design'), 'studio', CTRL + CharKey('s')),
            routine(self.save_as, 'STUDIO_SAVE_AS', _('Save current design under a new file'), 'studio',
                    CTRL + SHIFT + CharKey('s')),
            routine(self.save_all, 'STUDIO_SAVE_ALL', _('Save all open designs'), 'studio', CTRL + ALT + CharKey('s')),
            routine(self.get_help, 'STUDIO_HELP', _('Show studio help'), 'studio', KeyMap.F(12)),
            routine(self.settings, 'STUDIO_SETTINGS', _('Open studio settings'), 'studio', ALT + CharKey('s')),
            routine(restart, 'STUDIO_RESTART', _('Restart application'), 'studio', BlankKey),
            routine(self._on_close, 'STUDIO_EXIT', _('Exit application'), 'studio', CTRL + CharKey('q')),
            # ------------------------------
            routine(self.show_all_windows, 'FEATURE_SHOW_ALL', _('Show all feature windows'), 'studio',
                    ALT + CharKey('a')),
            routine(self.close_all, 'FEATURE_CLOSE_ALL', _('Close all feature windows'), 'studio', ALT + CharKey('x')),
            routine(lambda: self.close_all_on_side('right'),
                    'FEATURE_CLOSE_RIGHT', _('Close feature windows to the right'), 'studio', ALT + CharKey('R')),
            routine(lambda: self.close_all_on_side('left'),
                    'FEATURE_CLOSE_LEFT', _('Close feature windows to the left'), 'studio', ALT + CharKey('L')),
            routine(self.features_as_docked, 'FEATURE_DOCK_ALL', _('Dock all feature windows'), 'studio',
                    ALT + CharKey('d')),
            routine(self.features_as_windows, 'FEATURE_UNDOCK_ALL', _('Undock all feature windows'), 'studio',
                    ALT + CharKey('u')),
            routine(self.save_window_positions, 'FEATURE_SAVE_POS', _('Save window positions'), 'studio',
                    ALT + SHIFT + CharKey('s')),
            # -----------------------------
            routine(self.close_context, 'CONTEXT_CLOSE', _('Close tab'), 'studio', CTRL + CharKey('T')),
            routine(self.close_all_contexts, 'CONTEXT_CLOSE_ALL', _('Close all tabs'), 'studio',
                    CTRL + ALT + CharKey('T')),
            routine(self.close_other_contexts, 'CONTEXT_CLOSE_OTHER', _('Close other tabs'), 'studio', BlankKey),
            routine(self.close_other_contexts_right, 'CONTEXT_CLOSE_OTHER_RIGHT', _('Close all tabs on the right'),
                    'studio', BlankKey),
            # -----------------------------
            routine(self.preview, 'STUDIO_PREVIEW', _('Show preview'), 'studio', KeyMap.F(5)),
            routine(self.close_preview, 'STUDIO_PREVIEW_CLOSE', _('Close any preview'), 'studio', ALT + KeyMap.F(5)),
            routine(self.reload, 'STUDIO_RELOAD', _('Reload current design'), 'studio', CTRL + CharKey('R'))
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
    set_locale(pref.get("locale::language"))
    ResourceLoader.load(pref)
    StudioApplication(className='Formation Studio').mainloop()


if __name__ == "__main__":
    main()
