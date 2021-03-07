"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import logging
from collections import defaultdict

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Button
from hoverset.util.execution import Action
from studio.feature._base import BaseFeature
from studio.ui.editors import StyleItem
from studio.ui.widgets import CollapseFrame
from studio.lib.pseudo import Container


class ReusableStyleItem(StyleItem):
    _pool = defaultdict(dict)

    def __init__(self, parent, style_definition, on_change=None):
        super().__init__(parent, style_definition, on_change)
        self.parent = parent
        self.is_available = True
        # add self to reusable pool
        ReusableStyleItem._pool[parent][style_definition.get("name")] = self
        # Mark item as available/not available for reuse based on whether it's visible
        self.bind("<Unmap>", lambda e: self._make_available(True))
        self.bind("<Map>", lambda e: self._make_available(False))

    def _re_purposed(self, style_definition, on_change=None):
        if on_change is not None:
            self._on_change = on_change
        # block changes temporarily by setting on_change to None
        # this prevents glitching while resizing or unexpected race conditions
        temp = self._on_change
        self._on_change = None
        self.name = style_definition.get("name")
        # allow editor to adjust to the new definition
        self._editor.set_def(style_definition)
        self._editor.set(style_definition.get("value"))
        self._editor.on_change(self._change)
        self._label.configure(text=style_definition.get("display_name"))
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

    def __init__(self, master, pane, **cnf):
        super().__init__(master)
        self.style_pane = pane
        self.studio = self.style_pane.studio
        self.configure(**{**self.style.surface, **cnf})
        self._widget = None
        self._prev_widget = None
        self._has_initialized = False  # Flag to mark whether Style Items have been created
        self.items = {}

    @property
    def widget(self):
        return self._widget

    def can_optimize(self):
        return False

    def add(self, style_item):
        self.items[style_item.name] = style_item
        self._show(style_item)

    def remove(self, style_item):
        if style_item.name in self.items:
            self.items.pop(style_item.name)
        self._hide(style_item)

    def _show(self, item):
        item.pack(fill="x", pady=1)

    def _hide(self, item):
        item.pack_forget()

    def _get_prop(self, prop, widget):
        return widget.get_prop(prop)

    def _set_prop(self, prop, value, widget):
        widget.configure(**{prop: value})

    def on_widget_change(self, widget):
        self._widget = widget
        if widget is None:
            self.collapse()
            return
        definitions = self.get_definition()
        if self.can_optimize():
            for prop in definitions:
                self.items[prop]._re_purposed(definitions[prop])
        else:
            # this unmaps all style items returning them to the pool for reuse
            self.clear_children()
            self.items.clear()
            add = self.add
            list(map(lambda p: add(ReusableStyleItem.acquire(self, definitions[p], self.apply), ), definitions))

        self._has_initialized = True
        self._prev_widget = widget

    def _apply_action(self, prop, value, widget, data):
        self.apply(prop, value, widget, True)

    def _get_action_data(self, widget, prop):
        return {}

    def apply(self, prop, value, widget=None, silent=False):
        is_external = widget is not None
        widget = self.widget if widget is None else widget
        if widget is None:
            return
        try:
            prev_val = self._get_prop(prop, widget)
            data = self._get_action_data(widget, prop)
            self._set_prop(prop, value, widget)
            new_data = self._get_action_data(widget, prop)
            self.studio.widget_modified(widget, self.style_pane, None)
            if is_external:
                if widget == self.widget:
                    self.items[prop].set_silently(value)
            if silent:
                return
            key = f"{widget}:{self.__class__.__name__}:{prop}"
            action = self.studio.last_action()
            if action is None or action.key != key:
                self.studio.new_action(Action(
                    lambda _: self._apply_action(prop, prev_val, widget, data),
                    lambda _: self._apply_action(prop, value, widget, new_data),
                    key=key,
                ))
            else:
                action.update_redo(lambda _: self._apply_action(prop, value, widget, new_data))
        except Exception as e:
            # Empty string values are too common to be useful in logger debug
            if value != '':
                logging.error(e)
                logging.error(f"Could not set {self.__class__.__name__} {prop} as {value}", )

    def get_definition(self):
        return {}

    def on_search_query(self, query):
        for item in self.items.values():
            if query in item.definition.get("display_name"):
                self._show(item)
            else:
                self._hide(item)

    def on_search_clear(self):
        # Calling search query with empty query ensures all items are displayed
        self.on_search_query("")


class IdentityGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = "Widget identity"

    def get_definition(self):
        if hasattr(self.widget, 'identity'):
            return self.widget.identity
        return None

    def can_optimize(self):
        return self._has_initialized


class AttributeGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = "Attributes"

    def get_definition(self):
        if hasattr(self.widget, 'properties'):
            return self.widget.properties
        return {}

    def _get_action_data(self, widget, prop):
        if prop == "layout" and isinstance(widget, Container):
            return widget.get_all_info()
        super()._get_action_data(widget, prop)

    def _apply_action(self, prop, value, widget, data):
        self.apply(prop, value, widget, True)
        if prop == "layout" and data and isinstance(widget, Container):
            widget.config_all_widgets(data)
            if self.widget in widget._children:
                self.style_pane._layout_group.on_widget_change(self.widget)

    def can_optimize(self):
        return self._widget.__class__ == self._prev_widget.__class__ and self._has_initialized


class LayoutGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = "Layout"
        self._prev_layout = None

    def _get_prop(self, prop, widget):
        info = widget.layout.layout_strategy.info(widget)
        return info.get(prop)

    def _set_prop(self, prop, value, widget):
        widget.layout.apply(prop, value, widget)

    def on_widget_change(self, widget):
        super().on_widget_change(widget)
        self._prev_layout = widget.layout.layout_strategy
        if widget:
            self.label = f"Layout ({widget.layout.layout_strategy.name})"
        else:
            self.label = "Layout"

    def can_optimize(self):
        layout_strategy = self.widget.layout.layout_strategy
        return layout_strategy.__class__ == self._prev_layout.__class__ \
            and self._layout_equal(self.widget, self._prev_widget)

    def get_definition(self):
        if self.widget is not None:
            return self.widget.layout.definition_for(self.widget)
        return {}

    def _layout_equal(self, widget1, widget2):
        def1 = widget1.layout.layout_strategy.get_def(widget1)
        def2 = widget2.layout.layout_strategy.get_def(widget2)
        return def1 == def2


class StylePane(BaseFeature):
    name = "Style pane"
    icon = "edit"
    _defaults = {
        **BaseFeature._defaults,
        "side": "right",
    }

    def __init__(self, master, studio, **cnf):
        super().__init__(master, studio, **cnf)
        self.body = ScrolledFrame(self, **self.style.surface)
        self.body.pack(side="top", fill="both", expand=True)

        self._toggle_btn = Button(self._header, image=get_icon_image("chevron_down", 15, 15), **self.style.button,
                                  width=25,
                                  height=25)
        self._toggle_btn.pack(side="right")
        self._toggle_btn.on_click(self._toggle)

        self._search_btn = Button(self._header, image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)

        self.groups = []

        self._identity_group = self.add_group(IdentityGroup)
        self._layout_group = self.add_group(LayoutGroup)
        self._attribute_group = self.add_group(AttributeGroup)

        self._empty_frame = Frame(self.body)
        self.show_empty()
        self._current = None
        self._expanded = False

    def create_menu(self):
        return (
            ("command", "Search", get_icon_image("search", 14, 14), self.start_search, {}),
            ("command", "Expand all", get_icon_image("chevron_down", 14, 14), self.expand_all, {}),
            ("command", "Collapse all", get_icon_image("chevron_up", 14, 14), self.collapse_all, {})
        )

    def extern_apply(self, group_class, prop, value, widget=None, silent=False):
        for group in self.groups:
            if group.__class__ == group_class:
                group.apply(prop, value, widget, silent)
                return
        raise ValueError(f"Class {group_class.__class__.__name__} not found")

    def apply_style(self, prop, value, widget=None, silent=False):
        self._attribute_group.apply(prop, value, widget, silent)

    def apply_layout(self, prop, value, widget=None, silent=False):
        self._layout_group.apply(prop, value, widget, silent)

    def add_group(self, group_class) -> StyleGroup:
        if not issubclass(group_class, StyleGroup):
            raise ValueError('type required.')
        group = group_class(self.body.body, self)
        self.groups.append(group)
        group.pack(side='top', fill='x', pady=4)
        return group

    def show_empty(self):
        self.remove_empty()
        self._empty_frame.place(x=0, y=0, relheight=1, relwidth=1)
        Label(self._empty_frame, text="You have not selected any item",
              **self.style.text_passive).place(x=0, y=0, relheight=1, relwidth=1)

    def remove_empty(self):
        self._empty_frame.clear_children()
        self._empty_frame.place_forget()

    def show_loading(self):
        self.remove_empty()
        self._empty_frame.place(x=0, y=0, relheight=1, relwidth=1)
        Label(self._empty_frame, text="Loading...",
              **self.style.text_passive).place(x=0, y=0, relheight=1, relwidth=1)

    def styles_for(self, widget):
        self._current = widget
        if widget is None:
            self.show_empty()
            return
        self.show_loading()
        for group in self.groups:
            group.on_widget_change(widget)
        self.remove_empty()
        self.body.update_idletasks()

    def layout_for(self, widget):
        self._layout_group.on_widget_change(widget)

    def on_select(self, widget):
        self.styles_for(widget)

    def on_widget_change(self, old_widget, new_widget=None):
        if new_widget is None:
            new_widget = old_widget
        self.styles_for(new_widget)

    def on_widget_layout_change(self, widget):
        self.layout_for(widget)

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
        if self._current:
            super().start_search()
            self.body.scroll_to_start()

    def on_search_query(self, query):
        for group in self.groups:
            group.on_search_query(query)
        self.__update_frames()

    def on_search_clear(self):
        for group in self.groups:
            group.on_search_clear()
        # The search bar is being closed and we need to bring everything back
        super().on_search_clear()
