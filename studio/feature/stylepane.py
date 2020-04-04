"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import logging

from PIL import Image, ImageTk

from hoverset.ui.icons import get_icon, get_icon_image
from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Button
from studio.feature._base import BaseFeature
from studio.ui.editors import StyleItem
from studio.ui.widgets import CollapseFrame


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

        self._special_handlers = {
            "id": self.change_widget_id,
            "image": self.set_widget_image
        }

    def create_menu(self):
        return (
            ("command", "Search", get_icon_image("search", 14, 14), self.start_search, {}),
            ("command", "Expand all", get_icon_image("chevron_down", 14, 14), self.expand_all, {}),
            ("command", "Collapse all", get_icon_image("chevron_up", 14, 14), self.collapse_all, {})
        )

    def set_widget_image(self, path):
        if self._current is None:
            return
        try:
            image = Image.open(path)
        except Exception as e:
            print(e)
            return
        image = ImageTk.PhotoImage(image=image)
        self._current.config(image=image)
        # Protect image from garbage collection
        self._current.image = image

    def change_widget_id(self, id_):
        if self._current is None:
            return
        self._current.id = id_
        self.studio.widget_modified(self._current, self)

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
            if prop in self._special_handlers:
                self._special_handlers.get(prop)(value)
            else:
                self._current.configure(**{prop: value})
        except Exception:
            logging.log(logging.ERROR, f"Could not set style {prop} as {value}", )

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
        list(map(lambda identity: add(StyleItem(frame, identities[identity], self.apply), ), identities))
        prop = widget.properties
        frame = self._all
        list(map(lambda definition: add(StyleItem(frame, prop[definition], self.apply), ), prop))
        self.layout_for(widget)
        self.remove_empty()

    def layout_for(self, widget):
        frame = self._layout
        frame.clear_children()
        layout_def = widget.layout.definition_for(widget)
        frame.label = f"Layout ({widget.layout.layout_strategy.name})"
        for definition in layout_def:
            self.add(StyleItem(frame, layout_def[definition], self.apply_layout))
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
        self._toggle_btn.config(text=get_icon("chevron_up"))

    def clear_all(self):
        for frame in self.frames:
            frame.clear_children()

    def collapse_all(self):
        for frame in self.frames:
            frame.collapse()
        self._expanded = False
        self._toggle_btn.config(text=get_icon("chevron_down"))

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
