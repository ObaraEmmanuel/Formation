from hoverset.ui.widgets import Canvas, FontStyle, PanedWindow


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
