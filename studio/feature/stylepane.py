"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import logging
from collections import defaultdict
import tkinter as tk
from tkinter import ttk

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Button, TabView
from hoverset.util.execution import Action
from hoverset.platform import platform_is, LINUX
from studio.feature._base import BaseFeature
from studio.ui.editors import StyleItem, get_display_name, get_editor
from studio.ui.widgets import CollapseFrame
from studio.lib.pseudo import Container, PseudoWidget
from studio.lib.layouts import GridLayoutStrategy
from studio.preferences import Preferences
from studio.lib.properties import get_combined_properties, combine_properties
from studio.i18n import _


class ReusableStyleItem(StyleItem):
    _pool = defaultdict(dict)
    _editor_pool = set()

    def __init__(self, parent, style_definition, on_change=None):
        super().__init__(parent, style_definition, on_change)
        self.parent = parent
        self.is_available = True
        # add self to reusable pool
        ReusableStyleItem._pool[parent][style_definition.get("name")] = self
        # Mark item as available/not available for reuse based on whether it's visible
        self.bind("<Unmap>", lambda e: self._make_available(True))
        self.bind("<Map>", lambda e: self._make_available(False))

    def set_editor(self, style_def):
        if style_def["type"] == self._editor.style_def["type"]:
            return
        self._editor_pool.add(self._editor)
        self._editor.grid_forget()
        # fetch editor from pool
        for e in self._editor_pool:
            if e.style_def["type"] == style_def["type"]:
                self._editor = e
                self._editor_pool.remove(e)
                break
        else:
            self._editor = get_editor(self, style_def)
        self._editor.grid(row=0, column=1, sticky='ew')

    def _re_purposed(self, style_definition, on_change=None):
        if on_change is not None:
            self._on_change = on_change
        # block changes temporarily by setting on_change to None
        # this prevents glitching while resizing or unexpected race conditions
        temp = self._on_change
        self._on_change = None
        self.name = style_definition.get("name")
        # allow editor to adjust to the new definition
        # change the editor widget if necessary
        self.set_editor(style_definition)
        self._editor.set_def(style_definition)
        self._editor.set(style_definition.get("value"))
        self._editor.on_change(self._change)
        self._label.configure(text=get_display_name(style_definition, self.pref))
        self._on_change = temp
        return self

    def _make_available(self, flag: bool):
        self.is_available = flag

    def destroy(self):
        pool = self._pool[self.parent]
        if self in pool:
            pool.pop(self)
        super().destroy()

    @classmethod
    def free_all(cls, items):
        list(map(lambda x: x._make_available(True), items))

    @classmethod
    def acquire(cls, parent, style_definition, on_change=None):
        pool = cls._pool.get(parent)
        if pool:
            item = pool.get(style_definition.get("name"))
            if item and item.is_available:
                return item._re_purposed(style_definition, on_change)
        item = ReusableStyleItem(parent, style_definition, on_change)
        return item


class StyleGroup(CollapseFrame):
    """
    Main subdivision of the Style pane
    """
    handles_layout = False
    self_positioned = False

    def __init__(self, master, pane, **cnf):
        super().__init__(master)
        self.pane_row = 0
        self.style_pane = pane
        self.configure(**{**self.style.surface, **cnf})
        self._empty_message = _("Select an item to see styles")
        self._empty = Frame(self.body, **self.style.surface)
        self._empty_label = Label(self._empty, **self.style.text_passive,)
        self._empty_label.pack(fill="both", expand=True, pady=15)
        self._prev_widget = None
        self._has_initialized = False  # Flag to mark whether Style Items have been created
        self.items = {}

    @property
    def widgets(self):
        return self.style_pane.selection

    def can_optimize(self):
        return False

    def add(self, style_item):
        self.items[style_item.name] = style_item
        if self.style_pane._search_query is not None:
            if self._match_query(style_item.definition, self.style_pane._search_query):
                self._show(style_item)
            # make sure item is not available for reuse whether it
            # is displayed or not
            style_item._make_available(False)
        else:
            self._show(style_item)

    def remove(self, style_item):
        if style_item.name in self.items:
            self.items.pop(style_item.name)
        self._hide(style_item)

    def _show(self, item):
        item.pack(side="top", fill="x", pady=1)

    def _hide(self, item):
        item.pack_forget()

    def _get_prop(self, prop, widget):
        return widget.get_prop(prop)

    def _set_prop(self, prop, value, widget):
        widget.configure(**{prop: value})

    def _hide_group(self):
        pass

    def _show_group(self):
        pass

    def _match_query(self, definition, query):
        return query in definition["name"] or query in definition["display_name"]

    def _show_empty(self, text=None):
        self._empty.pack(fill="both", expand=True)
        text = self._empty_message if text is None else text
        self._empty_label["text"] = text

    def _remove_empty(self):
        self._empty.pack_forget()

    def on_widgets_change(self):
        if not self.widgets:
            self.collapse()
            return
        definitions = self.get_definition()
        if self.can_optimize() and self.items:
            for prop in definitions:
                self.items[prop]._re_purposed(definitions[prop])
        else:
            self.style_pane.show_loading()
            # this unmaps all style items returning them to the pool for reuse
            self.clear_children()
            # make all items held by group available for reuse
            ReusableStyleItem.free_all(self.items.values())
            self.items.clear()
            add = self.add
            list(map(lambda p: add(ReusableStyleItem.acquire(self, definitions[p], self.apply), ), sorted(definitions)))
            if not self.items:
                self._show_empty()
            else:
                self._remove_empty()
            # self.style_pane.body.scroll_to_start()

        self._has_initialized = True
        self._prev_widgets = self.widgets

    def _apply_action(self, prop, value, widgets, data):
        self.apply(prop, value, widgets, True)

    def _get_action_data(self, widget, prop):
        return {}

    def _get_key(self, widgets, prop):
        return f"{'.'.join([w.id for w in widgets])}:{self.__class__.__name__}:{prop}"

    def apply(self, prop, value, widgets=None, silent=False):
        is_external = widgets is not None
        widgets = self.widgets if widgets is None else widgets
        if not widgets:
            return
        try:
            prev_val = [self._get_prop(prop, widget) for widget in widgets]
            data = [self._get_action_data(widget, prop) for widget in widgets]
            if is_external:
                list(map(lambda x: self._set_prop(prop, x[0], x[1]), zip(value, widgets)))
            else:
                [self._set_prop(prop, value, widget) for widget in widgets]
            new_data = [self._get_action_data(widget, prop) for widget in widgets]
            self.style_pane.widgets_modified(widgets)
            if is_external:
                if widgets == self.widgets:
                    self.items[prop].set_silently(value)
            if silent:
                return
            key = self._get_key(widgets, prop)
            action = self.style_pane.last_action()

            if action is None or action.key != key:
                self.style_pane.new_action(Action(
                    lambda _: self._apply_action(prop, prev_val, widgets, data),
                    lambda _: self._apply_action(prop, [value for _ in widgets], widgets, new_data),
                    key=key,
                ))
            else:
                action.update_redo(lambda _: self._apply_action(prop, [value for _ in widgets], widgets, new_data))
        except Exception as e:
            # Empty string values are too common to be useful in logger debug
            if value != '':
                logging.error(e)
                logging.error(f"Could not set {self.__class__.__name__} {prop} as {value}", )

    def get_definition(self):
        return {}

    def supports_widgets(self):
        return True

    def on_search_query(self, query):
        item_found = False
        for item in self.items.values():
            if self._match_query(item.definition, query):
                self._show(item)
                item_found = True
            else:
                self._hide(item)
        if not item_found:
            self._show_empty(_("No items match your search"))
        else:
            self._remove_empty()

    def on_search_clear(self):
        # Calling search query with empty query ensures all items are displayed
        self.clear_children()
        self.on_search_query("")


class IdentityGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Widget identity")

    def get_definition(self):
        if not self.widgets:
            return
        if hasattr(self.widgets[0], 'identity'):
            return self.widgets[0].identity
        return None

    def can_optimize(self):
        return self._has_initialized

    def supports_widgets(self):
        return len(self.widgets) == 1


class AttributeGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Attributes")
        self._prev_classes = set()

    def get_definition(self):
        if self.widgets and all(isinstance(widget, PseudoWidget) for widget in self.widgets):
            return get_combined_properties(self.widgets)
        return {}

    def _get_action_data(self, widget, prop):
        if prop == "layout" and isinstance(widget, Container):
            return widget.get_all_info()
        super()._get_action_data(widget, prop)

    def _apply_action(self, prop, value, widgets, data):
        self.apply(prop, value, widgets, True)
        if prop == "layout":
            has_change = False
            for widget, info in zip(widgets, data):
                widget.config_all_widgets(info)
                if any(w in widget._children for w in self.widgets):
                    has_change = True

            if has_change:
                self.style_pane._layout_group.on_widgets_change()

    def can_optimize(self):
        classes = set(w.__class__ for w in self.widgets)
        if classes != self._prev_classes:
            self._prev_classes = classes
            return False
        return True


class ColumnConfig(StyleGroup):

    handles_layout = True
    self_positioned = True

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.clear_children()
        self._label_frame.pack_forget()
        self._index = StyleItem(self, self._get_index_def())
        self._show(self._index)

    def _get_index_def(self):
        definition = dict(GridLayoutStrategy.COLUMN_DEF)
        if self.widgets:
            definition["value"] = self.widgets[0].grid_info()["column"]

        for w in self.widgets:
            if w.grid_info()["column"] != definition["value"]:
                definition["value"] = ''
                break

        return definition

    def _get_prop(self, prop, widget):
        info = widget.layout.body.columnconfigure(widget.grid_info()["column"])
        return info.get(prop)

    def _set_prop(self, prop, value, widget):
        column = int(widget.grid_info()["column"])
        widget.layout.body.columnconfigure(column, **{prop: value})
        if not hasattr(widget.layout, "_column_conf"):
            widget.layout._column_conf = {column}
        else:
            widget.layout._column_conf.add(column)

    def is_grid(self, widget):
        if not widget:
            return False
        return widget.layout.layout_strategy.__class__ == GridLayoutStrategy

    def get_definition(self):
        if not self.widgets and self.is_grid(self.widgets[0]):
            return {}
        return combine_properties([w.layout.layout_strategy.get_column_def(w) for w in self.widgets])

    def can_optimize(self):
        return self._has_initialized

    def clear_children(self):
        for child in self.items.values():
            self._hide(child)

    def _update_index(self):
        if self.widgets:
            self._index.set(self.widgets[0].grid_info()["column"])

    def on_widgets_change(self):
        if self.widgets and all(self.is_grid(widget) for widget in self.widgets):
            super().on_widgets_change()
            self._index._editor.set_def(self._get_index_def())
            self._update_index()


class RowConfig(ColumnConfig):

    def _get_index_def(self):
        definition = dict(GridLayoutStrategy.ROW_DEF)
        if self.widgets:
            definition["value"] = self.widgets[0].grid_info()["row"]

        for w in self.widgets:
            if w.grid_info()["row"] != definition["value"]:
                definition["value"] = ''
                break

        return definition

    def _get_prop(self, prop, widget):
        info = widget.layout.body.rowconfigure(widget.grid_info()["row"])
        return info.get(prop)

    def _set_prop(self, prop, value, widget):
        row = int(widget.grid_info()["row"])
        widget.layout.body.rowconfigure(row, **{prop: value})
        if not hasattr(widget.layout, "_row_conf"):
            widget.layout._row_conf = {row}
        else:
            widget.layout._row_conf.add(row)

    def _update_index(self):
        if self.widgets:
            self._index.set(self.widgets[0].grid_info()["column"])

    def get_definition(self):
        if not self.widgets and self.is_grid(self.widgets[0]):
            return {}
        return combine_properties([w.layout.layout_strategy.get_row_def(w) for w in self.widgets])


class GridConfig(Frame):

    def __init__(self, master, pane, **cnf):
        super().__init__(master)
        self._title = Label(self, **self.style.text_accent)
        self._title.pack(side="top", fill="x")
        self._tab_view = TabView(self)
        self._tab_view.pack(fill="both")
        self.column_config = ColumnConfig(self, pane, **cnf)
        self.row_config = RowConfig(self, pane, **cnf)
        self._tab_view.add(self.column_config, text="Column")
        self._tab_view.add(self.row_config, text="Row")


class LayoutGroup(StyleGroup):

    handles_layout = True

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Layout")
        self._prev_layout = None
        self._grid_config = GridConfig(self.body, pane)
        self._last_keys = set()

    def _get_prop(self, prop, widget):
        info = widget.layout.layout_strategy.info(widget)
        return info.get(prop)

    def _set_prop(self, prop, value, widget):
        widget.layout.apply(prop, value, widget)

    def on_widgets_change(self):
        super().on_widgets_change()
        layout_strategy = self.widgets[0].layout.layout_strategy if self.widgets else None
        self._prev_layout = layout_strategy

        if self.widgets:
            self.label = _("Layout") + f"({self.widgets[0].layout.layout_strategy.name})"
        else:
            self.label = _("Layout")

        if layout_strategy.__class__ == GridLayoutStrategy:
            self._show_grid_conf(True)
        else:
            self._show_grid_conf(False)

    def _show_grid_conf(self, flag):
        if flag:
            if not self._grid_config.winfo_ismapped():
                self._grid_config.pack(side="bottom", fill="x", pady=1)
        else:
            self._grid_config.pack_forget()

    def can_optimize(self):
        keys = set(self.get_definition().keys())
        layout = self.widgets[0].layout.layout_strategy if self.widgets else None
        if self._last_keys != keys or self._prev_layout != layout:
            self._last_keys = keys
            self._prev_layout = layout
            return False
        return True

    def get_definition(self):
        if self.widgets:
            return combine_properties([w.layout.definition_for(w) for w in self.widgets])
        return {}

    def _layout_equal(self, widget1, widget2):
        def1 = widget1.layout.layout_strategy.get_def(widget1)
        def2 = widget2.layout.layout_strategy.get_def(widget2)
        return def1 == def2

    def supports_widgets(self):
        # toplevel widgets do not need layout
        if any(widget.is_toplevel for widget in self.widgets):
            return False
        if not self.widgets:
            return False
        strategy = self.widgets[0].layout.layout_strategy
        # only support widgets with the same layout strategy
        return all(widget.layout.layout_strategy == strategy for widget in self.widgets)


class WindowGroup(StyleGroup):
    handles_layout = True

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Window")
        self._prev_layout = None

    def _get_prop(self, prop, widget):
        return widget.get_win_prop(prop)

    def _set_prop(self, prop, value, widget):
        widget.set_win_prop(prop, value)

    def can_optimize(self):
        return True

    def get_definition(self):
        if self.widgets:
            return combine_properties([widget.window_definition() for widget in self.widgets])
        return {}

    def supports_widgets(self):
        return all(widget.is_toplevel for widget in self.widgets)


class ScrollGroup(StyleGroup):
    handles_layout = False

    DEF = {
        "yscroll": {
            "name": "yscroll",
            "display_name": "Y Scroll",
            "type": "widget",
            "include": [tk.Scrollbar, ttk.Scrollbar],
        },
        "xscroll": {
            "name": "xscroll",
            "display_name": "X Scroll",
            "type": "widget",
            "include": [tk.Scrollbar, ttk.Scrollbar],
        },
    }

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Scroll")
        self._last_keys = None

    def _get_prop(self, prop, widget):
        if prop == "yscroll":
            return getattr(widget, "_cnf_y_scroll", '')
        if prop == "xscroll":
            return getattr(widget, "_cnf_x_scroll", '')

    def _set_prop(self, prop, value, widget):
        if prop == "yscroll":
            widget._cnf_y_scroll = value
        if prop == "xscroll":
            widget._cnf_x_scroll = value

    def _keys(self, widget):
        keys = []
        widget_keys = widget.keys()
        if 'yscrollcommand' in widget_keys:
            keys.append('yscroll')
        if 'xscrollcommand' in widget_keys:
            keys.append('xscroll')
        return tuple(keys)

    def can_optimize(self):
        keys = set()
        for widget in self.widgets:
            for k in self._keys(widget):
                keys.add(k)
        if keys != self._last_keys:
            self._last_keys = keys
            return False
        return True

    def _definition(self, widget):
        keys = widget.keys()
        props = {}
        if 'yscrollcommand' in keys:
            props['yscroll'] = dict(**self.DEF['yscroll'], value=getattr(widget, '_cnf_y_scroll', ''))
        if 'xscrollcommand' in keys:
            props['xscroll'] = dict(**self.DEF['xscroll'], value=getattr(widget, '_cnf_x_scroll', ''))
        return props

    def get_definition(self):
        if self.widgets:
            return combine_properties([self._definition(widget) for widget in self.widgets])
        return {}

    def _support(self, widget):
        keys = widget.keys()
        return any(x in keys for x in ('yscrollcommand', 'xscrollcommand'))

    def supports_widgets(self):
        return all(self._support(w) for w in self.widgets)


class StylePaneFramework:

    def setup_style_pane(self):
        self.body = ScrolledFrame(self, **self.style.surface)
        self.body.pack(side="top", fill="both", expand=True)

        self._toggle_btn = Button(self.get_header(), image=get_icon_image("chevron_down", 15, 15), **self.style.button,
                                  width=25,
                                  height=25)
        self._toggle_btn.pack(side="right")
        self._toggle_btn.on_click(self._toggle)

        self._search_btn = Button(self.get_header(), image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)

        self.groups = []

        self._empty_frame = Frame(self.body)
        self.show_empty()
        self._selection = []
        self._expanded = False
        self._is_loading = False
        self._search_query = None
        self._current_row = 0

        self.body.body.columnconfigure(0, weight=1)

    def get_header(self):
        raise NotImplementedError()

    @property
    def selection(self):
        return self._selection

    @property
    def widgets(self):
        return self._selection

    def create_menu(self):
        return (
            ("command", _("Search"), get_icon_image("search", 18, 18), self.start_search, {}),
            ("command", _("Expand all"), get_icon_image("chevron_down", 18, 18), self.expand_all, {}),
            ("command", _("Collapse all"), get_icon_image("chevron_up", 18, 18), self.collapse_all, {})
        )

    def extern_apply(self, group_class, prop, value, widgets=None, silent=False):
        for group in self.groups:
            if group.__class__ == group_class:
                group.apply(prop, value, widgets, silent)
                return
        raise ValueError(f"Class {group_class.__class__.__name__} not found")

    def last_action(self):
        raise NotImplementedError()

    def new_action(self, action):
        raise NotImplementedError()

    def widgets_modified(self, widgets):
        raise NotImplementedError()

    def add_group(self, group_class, **kwargs) -> StyleGroup:
        if not issubclass(group_class, StyleGroup):
            raise ValueError('type required.')
        group = group_class(self.body.body, self, **kwargs)
        group.pane_row = self._current_row
        self._current_row += 1
        self.groups.append(group)
        self.show_group(group)
        return group

    def add_group_instance(self, group_instance, show=False):
        if not isinstance(group_instance, StyleGroup):
            raise ValueError('Expected object of type StyleGroup.')
        group_instance.pane_row = self._current_row
        self._current_row += 1
        self.groups.append(group_instance)
        if show:
            self.show_group(group_instance)

    def hide_group(self, group):
        if group.self_positioned:
            group._hide_group()
            return
        if not group.winfo_ismapped():
            return
        group.grid_forget()

    def show_group(self, group):
        if group.self_positioned:
            group._show_group()
            return
        if group.winfo_ismapped():
            return
        group.grid(row=group.pane_row, column=0, sticky="nsew", pady=12)

    def show_empty(self):
        self.remove_empty()
        self._empty_frame.place(x=0, y=0, relheight=1, relwidth=1)
        Label(self._empty_frame, text=_("You have not selected any item"),
              **self.style.text_passive).place(x=0, y=0, relheight=1, relwidth=1)

    def remove_empty(self):
        self._empty_frame.clear_children()
        self._empty_frame.place_forget()

    def show_loading(self):
        if platform_is(LINUX) or self._is_loading:
            # render transitions in linux are very fast and glitch free
            # for other platforms or at least for windows we need to hide the glitching
            return
        self.remove_empty()
        self._empty_frame.place(x=0, y=0, relheight=1, relwidth=1)
        Label(self._empty_frame, text=_("Loading..."),
              **self.style.text_passive).place(x=0, y=0, relheight=1, relwidth=1)
        self._is_loading = True

    def remove_loading(self):
        self.remove_empty()
        self._is_loading = False

    def render_styles(self):
        if not self.widgets:
            self.show_empty()
            return

        for group in self.groups:
            if group.supports_widgets():
                self.show_group(group)
                group.on_widgets_change()
            else:
                self.hide_group(group)
        self.remove_loading()
        self.body.update_idletasks()

    def render_layouts(self):
        for group in self.groups:
            if group.handles_layout and group.supports_widgets():
                group.on_widgets_change()
        self.remove_loading()

    def _select(self, _, selection=None):
        selection = list(selection if selection is not None else self.studio.selection)

        if selection == self._selection:
            return
        self._selection = selection
        self.render_styles()

    def on_widgets_change(self, widgets):
        if any(w in self.widgets for w in widgets):
            self.render_styles()

    def on_widgets_layout_change(self, widgets):
        if any(w in self.widgets for w in widgets):
            self.render_layouts()

    def expand_all(self):
        for group in self.groups:
            group.expand()
        self._expanded = True
        self._toggle_btn.config(image=get_icon_image("chevron_up", 15, 15))

    def clear_all(self):
        for group in self.groups:
            group.clear_children()

    def collapse_all(self):
        for group in self.groups:
            group.collapse()
        self._expanded = False
        self._toggle_btn.config(image=get_icon_image("chevron_down", 15, 15))

    def _toggle(self, *_):
        if not self._expanded:
            self.expand_all()
        else:
            self.collapse_all()

    def __update_frames(self):
        for group in self.groups:
            group.update_state()

    def start_search(self, *_):
        if self._selection:
            super().start_search()
            self.body.scroll_to_start()

    def on_search_query(self, query):
        for group in self.groups:
            group.on_search_query(query)
        self.__update_frames()
        self.body.scroll_to_start()
        self._search_query = query

    def on_search_clear(self):
        for group in self.groups:
            group.on_search_clear()
        # The search bar is being closed and we need to bring everything back
        super().on_search_clear()
        self._search_query = None


class StylePane(StylePaneFramework, BaseFeature):
    name = "Style pane"
    display_name = _("Style pane")
    icon = "edit"
    _defaults = {
        **BaseFeature._defaults,
        "side": "right",
    }

    def __init__(self, master, studio, **cnf):
        super().__init__(master, studio, **cnf)
        self.setup_style_pane()

        pref: Preferences = Preferences.acquire()
        pref.add_listener("designer::descriptive_names", lambda _: [self.render_styles(), self.render_layouts()])

        self._identity_group = self.add_group(IdentityGroup)
        self._layout_group = self.add_group(LayoutGroup)
        self._attribute_group = self.add_group(AttributeGroup)
        self.add_group(WindowGroup)
        self.add_group(ScrollGroup)

        self.add_group_instance(self._layout_group._grid_config.column_config)
        self.add_group_instance(self._layout_group._grid_config.row_config)

        self.studio.bind("<<SelectionChanged>>", self._select, add='+')

    def apply_style(self, prop, value, widgets=None, silent=False):
        self._attribute_group.apply(prop, value, widgets, silent)

    def apply_layout(self, prop, value, widgets=None, silent=False):
        self._layout_group.apply(prop, value, widgets, silent)

    def get_header(self):
        return self._header

    def last_action(self):
        return self.studio.last_action()

    def new_action(self, action):
        self.studio.new_action(action)

    def widgets_modified(self, widgets):
        self.studio.widgets_modified(widgets, self)
