from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import Canvas, FontStyle, Frame, Entry, Button, Label


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
