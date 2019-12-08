"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import studio.ui.editors as editors
from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Canvas, Entry, Button, Window
from hoverset.ui.icons import get_icon


def get_editor(parent, definition):
    type_ = definition.get("type").capitalize()
    editor = getattr(editors, type_, editors.Text)
    return editor(parent, definition)


class CollapseFrame(Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark)
        self._label_frame = Frame(self, **self.style.bright, height=20)
        self._label_frame.pack(side="top", fill="x", padx=2)
        self._label_frame.pack_propagate(0)
        self._label = Label(self._label_frame, **self.style.bright, **self.style.text_bright)
        self._label.pack(side="left")
        self._collapse_btn = Button(self._label_frame, width=20, **self.style.bright, **self.style.text_bright)
        self._collapse_btn.config(text=get_icon("triangle_up"))
        self._collapse_btn.pack(side="right", fill="y")
        self._collapse_btn.on_click(self.toggle)
        self.body = Frame(self, **self.style.dark)
        self.body.pack(side="top", fill="both", pady=2)
        self._collapsed = False

    def collapse(self, *_):
        if not self._collapsed:
            self.body.pack_forget()
            self._collapse_btn.config(text=get_icon("triangle_down"))
            self.pack_propagate(0)
            self.config(height=20)
            self._collapsed = True

    def clear_children(self):
        self.body.clear_children()

    def expand(self, *_):
        if self._collapsed:
            self.body.pack(side="top", fill="both")
            self.pack_propagate(1)
            self._collapse_btn.config(text=get_icon("triangle_up"))
            self._collapsed = False

    def toggle(self, *_):
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

    @property
    def label(self):
        return self._label["text"]

    @label.setter
    def label(self, value):
        self._label.config(text=value)


class StyleItem(Frame):

    def __init__(self, parent, style_definition, style_pane):
        super().__init__(parent.body)
        self.definition = style_definition
        self.style_pane = style_pane
        self.config(**self.style.dark)
        self._label = Label(self, **parent.style.dark_text_passive, text=style_definition.get("display_name"),
                            anchor="w")
        self._label.grid(row=0, column=0, sticky='ew')
        # self._label.config(**parent.style.dark_highlight_active)
        self._editor = get_editor(self, style_definition)
        self._editor.grid(row=0, column=1, sticky='ew')
        self.grid_columnconfigure(1, weight=1, uniform=1)
        self.grid_columnconfigure(0, weight=1, uniform=1)
        self._editor.set(style_definition.get("value"))
        self._editor.on_change(self.on_change)

    def on_change(self, value):
        try:
            self.style_pane.apply(self.definition.get("name"), value)
        except Exception:
            pass


class StylePane(Frame):

    def __init__(self, master, studio, **cnf):
        super().__init__(master, **cnf)
        self.studio = studio
        self.config(**self.style.dark)
        self.items = []

        self._header = Frame(self, **self.style.dark, **self.style.dark_highlight_dim, height=30)
        self._header.pack(side="top", fill="x", pady=2, padx=2)
        self._header.pack_propagate(0)

        self.body = ScrolledFrame(self, **self.style.dark)
        self.body.pack(side="top", fill="both", expand=True)

        Label(self._header, **self.style.dark_text_passive, text="Style pane").pack(side="left")

        self._id = CollapseFrame(self.body.body, **self.style.dark)
        self._id.pack(side="top", fill="x", pady=4)
        self._id.label = "Widget identity"

        self._all = CollapseFrame(self.body.body, **self.style.dark)
        self._all.pack(side="top", fill="x", pady=4)
        self._all.label = "All attributes"

        self._empty_frame = Frame(self.body)
        self.show_empty()
        self._current = None

        self._special_handlers = {
            "id": self.change_widget_id
        }

    def change_widget_id(self, id_):
        print("changing")
        if self._current is None:
            return
        self._current.id = id_
        self.studio.widget_modified(self._current)

    def add(self, style_item):
        self.items.append(style_item)
        style_item.pack(fill="x", pady=1)

    def apply(self, prop, value):
        if self._current is None:
            return
        print(prop)
        if prop in self._special_handlers:
            self._special_handlers.get(prop)(value)
        else:
            self._current.config(**{prop: value})

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
        self._all.clear_children()
        self._id.clear_children()
        self.items = []
        if widget is None:
            self._all.collapse()
            self._id.collapse()
            self.show_empty()
            return
        self._all.expand()
        self._id.expand()
        identities = widget.identity
        for identity in identities:
            self.add(StyleItem(self._id, identities[identity], self),)
        prop = widget.properties
        for definition in prop:
            if not definition.startswith("_"):
                self.add(StyleItem(self._all, prop[definition], self),)
        self.remove_empty()
