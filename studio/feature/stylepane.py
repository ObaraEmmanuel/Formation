"""
Contains all the widget representations used in the designer and specifies all the styles that can be applied to them
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

from PIL import Image, ImageTk

from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Button
from hoverset.ui.icons import get_icon, get_icon_image

from studio.ui import editors
from studio.feature import BaseFeature


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


class LayoutItem(StyleItem):

    def on_change(self, value):
        try:
            self.style_pane.apply_layout(self.definition.get("name"), value)
        except Exception as e:
            print(f"error setting layout: \n{e}")
            pass


class StylePane(BaseFeature):
    name = "Style pane"
    side = "right"
    icon = "edit"

    def __init__(self, master, studio, **cnf):
        super().__init__(master, studio, **cnf)
        self.items = []
        self.body = ScrolledFrame(self, **self.style.dark)
        self.body.pack(side="top", fill="both", expand=True)

        self._toggle_btn = Button(self._header, text=get_icon("chevron_down"), **self.style.dark_button, width=25,
                                  height=25)
        self._toggle_btn.pack(side="right")
        self._toggle_btn.on_click(self._toggle)

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
            ("command", "Expand all", get_icon_image("chevron_down", 14, 14), self.expand_all, {}),
            ("command", "Collapse all", get_icon_image("chevron_up", 14, 14), self.collapse_all, {})
        )

    def clone(self, parent):
        new = StylePane(parent, self.studio)
        new.styles_for(self._current)
        if self._expanded:
            new.expand_all()
        else:
            new.collapse_all()
        return new

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
        style_item.pack(fill="x", pady=1)

    def apply(self, prop, value):
        if self._current is None:
            return
        if prop in self._special_handlers:
            self._special_handlers.get(prop)(value)
        else:
            self._current.config(**{prop: value})

    def apply_layout(self, prop, value):
        self._current.layout.apply(prop, value, self._current)
        self.studio.designer.adjust_highlight(self._current)

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
        list(map(lambda identity: add(StyleItem(frame, identities[identity], self), ), identities))
        prop = widget.properties
        frame = self._all
        list(map(lambda definition: add(StyleItem(frame, prop[definition], self), ), prop))
        self.layout_for(widget)
        self.remove_empty()

    def layout_for(self, widget):
        frame = self._layout
        frame.clear_children()
        layout_def = widget.layout.definition_for(widget)
        for definition in layout_def:
            self.add(LayoutItem(frame, layout_def[definition], self), )
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