from hoverset.ui.icons import get_icon_image, get_icon
from hoverset.ui.widgets import Canvas, FontStyle, Frame, Entry, Button, Label
from studio.ui.editors import get_editor


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
        self.__ref = Frame(self.body, height=0, width=0, **self.style.dark)
        self.__ref.pack(side="top")
        self._collapsed = False

    def update_state(self):
        self.__ref.pack(side="top")

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


class SideBar(Canvas):

    def __init__(self, master):
        super().__init__(master)
        self.config(**self.style.dark, **self.style.no_highlight, width=20)
        self.features = {}

    def remove(self, feature):
        self.delete(feature.indicator)
        self.features.pop(feature)
        self._redraw()

    def _redraw(self):
        y = 0
        for feature in self.features:
            indicator = self.features[feature]
            font = FontStyle(self, self.itemconfig(indicator).get("font", "TkDefaultFont")[3])
            y += font.measure(feature.name) + 20
            self.coords(indicator, 18, y)

    def add_feature(self, feature):
        indicator = self.create_text(0, 0, angle=90, text=feature.name, fill=self.style.dark_on_hover.get("background"),
                                     anchor="sw", activefill=self.style.dark_on_hover.get("background"))
        font = FontStyle(self, self.itemconfig(indicator).get("font", "TkDefaultFont")[3])
        y = font.measure(feature.name) + self.bbox("all")[3] + 20
        self.coords(indicator, 18, y)
        self.tag_bind(indicator, "<Button-1>", lambda event: self.toggle_feature(feature))
        feature.indicator = indicator
        self.features[feature] = indicator

    def change_feature(self, new, old):
        self.tag_unbind(old.indicator, "<Button-1>")
        self.tag_bind(old.indicator, "<Button-1>", lambda event: self.toggle_feature(new))
        self.features.pop(old)
        self.features[new] = old.indicator
        new.indicator = old.indicator

    def deselect(self, feature):
        self.itemconfig(feature.indicator, fill=self.style.dark_text.get("foreground"))

    def select(self, feature):
        self.itemconfig(feature.indicator, fill=self.style.dark_on_hover.get("background"))

    def close_all(self):
        for feature in self.features:
            self.deselect(feature)

    def toggle_feature(self, feature):
        feature.toggle()


class SearchBar(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.no_highlight, **self.style.dark)
        self._entry = Entry(self, **self.style.dark_input)
        self._clear_btn = Button(self, image=get_icon_image("close", 15, 15),
                                 **self.style.dark_button, width=25, height=25)
        self._clear_btn.pack(side="right", fill="y")
        self._clear_btn.on_click(self._clear)
        Label(self, **self.style.dark_text, image=get_icon_image("search", 15, 15)).pack(side="left")
        self._entry.pack(side="left", fill="both", expand=True, padx=2)
        self._entry.on_entry(self._change)
        self._on_change = None
        self._on_clear = None

    def on_query_change(self, func, *args, **kwargs):
        self._on_change = lambda val: func(val, *args, **kwargs)

    def on_query_clear(self, func, *args, **kwargs):
        self._on_clear = lambda: func(*args, **kwargs)

    def _clear(self, *_):
        if self._on_clear:
            self._on_clear()

    def _change(self, *_):
        if self._on_change:
            self._on_change(self._entry.get())


class StyleItem(Frame):

    def __init__(self, parent, style_definition, on_change=None):
        super().__init__(parent.body)
        self.definition = style_definition
        self.name = style_definition.get("name")
        self.config(**self.style.dark)
        self._label = Label(self, **parent.style.dark_text_passive, text=style_definition.get("display_name"),
                            anchor="w")
        self._label.grid(row=0, column=0, sticky='ew')
        # self._label.config(**parent.style.dark_highlight_active)
        self._editor = get_editor(self, style_definition)
        self._editor.grid(row=0, column=1, sticky='ew')
        self.grid_columnconfigure(1, weight=1, uniform=1)
        self.grid_columnconfigure(0, weight=1, uniform=1)
        self._on_change = on_change
        self._editor.set(style_definition.get("value"))
        self._editor.on_change(self._change)

    def _change(self, value):
        if self._on_change:
            self._on_change(self.name, value)

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda name, val: callback(name, val, *args, **kwargs)

    def hide(self):
        self.grid_propagate(False)
        self.configure(height=0, width=0)

    def show(self):
        self.grid_propagate(True)

    def set(self, value):
        self._editor.set(value)
