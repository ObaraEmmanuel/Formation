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
from studio.feature._base import BaseFeature
from studio.ui.editors import StyleItem
from studio.ui.widgets import CollapseFrame


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
        self._on_change = on_change
        self.name = style_definition.get("name")
        self._editor.set(style_definition.get("value"))
        self._editor.on_change(self._change)
        self._label.configure(text=style_definition.get("display_name"))
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


class StylePane(BaseFeature):
    name = "Style pane"
    side = "right"
    icon = "edit"

    def __init__(self, master, studio, **cnf):
        super().__init__(master, studio, **cnf)
        self.items = []
        self.body = ScrolledFrame(self, **self.style.dark)
        self.body.pack(side="top", fill="both", expand=True)

        self._toggle_btn = Button(self._header, image=get_icon_image("chevron_down", 15, 15), **self.style.dark_button,
                                  width=25,
                                  height=25)
        self._toggle_btn.pack(side="right")
        self._toggle_btn.on_click(self._toggle)

        self._search_btn = Button(self._header, image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.dark_button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)

        self._id = CollapseFrame(self.body.body, **self.style.dark)
        self._id.pack(side="top", fill="x", pady=4)
        self._id.label = "Widget identity"

        self._layout = CollapseFrame(self.body.body, **self.style.dark)
        self._layout.pack(side="top", fill="x", pady=4)
        self._layout.label = "Layout"

        self._all = CollapseFrame(self.body.body, **self.style.dark)
        self._all.pack(side="top", fill="x", pady=4)
        self._all.label = "All attributes"

        self.frames = (self._id, self._layout, self._all)
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

    def add(self, style_item):
        self.items.append(style_item)
        self._show(style_item)

    def _show(self, item):
        item.pack(fill="x", pady=1)

    def _hide(self, item):
        item.pack_forget()

    def apply(self, prop, value):
        if self._current is None:
            return
        try:
            self._current.configure(**{prop: value})
        except Exception as e:
            logging.error(e)
            logging.error(f"Could not set style {prop} as {value}", )

    def apply_layout(self, prop, value):
        try:
            self._current.layout.apply(prop, value, self._current)
            self.studio.designer.adjust_highlight(self._current)
        except Exception as e:
            print(e)
            logging.log(logging.ERROR, f"Could not set layout {prop} as {value}", )

    def show_empty(self):
        self.remove_empty()
        self._empty_frame.place(x=0, y=0, relheight=1, relwidth=1)
        Label(self._empty_frame, text="You have not selected any item",
              **self.style.dark_text_passive).place(x=0, y=0, relheight=1, relwidth=1)

    def remove_empty(self):
        self._empty_frame.clear_children()
        self._empty_frame.place_forget()

    def show_loading(self):
        self.remove_empty()
        self._empty_frame.place(x=0, y=0, relheight=1, relwidth=1)
        Label(self._empty_frame, text="Loading...",
              **self.style.dark_text_passive).place(x=0, y=0, relheight=1, relwidth=1)

    def styles_for(self, widget):
        self.show_loading()
        self._current = widget
        self.clear_all()
        self.items = []
        if widget is None:
            self.collapse_all()
            self.show_empty()
            return
        self.expand_all()
        identities = widget.identity
        frame = self._id
        add = self.add
        list(map(
            lambda identity: add(ReusableStyleItem.acquire(frame, identities[identity], self.apply), ), identities
        ))
        prop = widget.properties
        frame = self._all
        list(map(lambda definition: add(ReusableStyleItem.acquire(frame, prop[definition], self.apply), ), prop))
        self.layout_for(widget)
        self.remove_empty()

    def layout_for(self, widget):
        frame = self._layout
        frame.clear_children()
        layout_def = widget.layout.definition_for(widget)
        frame.label = f"Layout ({widget.layout.layout_strategy.name})"
        for definition in layout_def:
            self.add(ReusableStyleItem.acquire(frame, layout_def[definition], self.apply_layout))
        self.body.update_idletasks()

    def on_select(self, widget):
        self.styles_for(widget)

    def on_widget_change(self, old_widget, new_widget=None):
        self.styles_for(new_widget)

    def on_widget_layout_change(self, widget):
        self.layout_for(widget)

    def expand_all(self):
        for frame in self.frames:
            frame.expand()
        self._expanded = True
        self._toggle_btn.config(image=get_icon_image("chevron_up", 15, 15))

    def clear_all(self):
        for frame in self.frames:
            frame.clear_children()

    def collapse_all(self):
        for frame in self.frames:
            frame.collapse()
        self._expanded = False
        self._toggle_btn.config(image=get_icon_image("chevron_down", 15, 15))

    def _toggle(self, *_):
        if not self._expanded:
            self.expand_all()
        else:
            self.collapse_all()

    def __update_frames(self):
        for frame in self.frames:
            frame.update_state()

    def start_search(self, *_):
        if self._current:
            super().start_search()
            self.body.scroll_to_start()

    def on_search_query(self, query):
        for item in self.items:
            if query in item.definition.get("display_name"):
                self._show(item)
            else:
                self._hide(item)
        self.__update_frames()

    def on_search_clear(self):
        # The search bar is being closed and we need to bring everything back
        # Calling search query with empty query ensures all items are displayed
        self.on_search_query("")
        super().on_search_clear()
