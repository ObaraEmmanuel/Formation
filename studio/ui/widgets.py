import logging
import math
from tkinter import ttk, TclError

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import Canvas, FontStyle, Frame, Entry, Button, Label, ScrollableInterface, EventMask, Spinner
from studio.ui import geometry
from studio.i18n import _


class CoordinateIndicator(Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        Label(self, **self.style.text_accent_1, text="x: ", width=3).pack(side='left')
        self._x = Label(self, **self.style.text, width=5, anchor='w')
        self._x.pack(side='left')
        Label(self, **self.style.text_accent_1, text="y: ", width=3).pack(side='left')
        self._y = Label(self, **self.style.text, width=5, anchor='w')
        self._y.pack(side='left')

    def set_coord(self, x, y):
        self._y['text'] = int(y)
        self._x['text'] = int(x)


class CollapseFrame(Frame):
    __icons_loaded = False
    EXPAND = None
    COLLAPSE = None

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self._load_icons()
        self.config(**self.style.surface)
        self._label_frame = Frame(self, **self.style.bright, height=20)
        self._label_frame.pack(side="top", fill="x", padx=2)
        self._label_frame.pack_propagate(0)
        self._label = Label(self._label_frame, **self.style.bright, **self.style.text_bright)
        self._label.pack(side="left")
        self._collapse_btn = Button(self._label_frame, width=20, **self.style.bright, **self.style.text_bright)
        self._collapse_btn.config(image=self.COLLAPSE)
        self._collapse_btn.pack(side="right", fill="y")
        self._collapse_btn.on_click(self.toggle)
        self.body = Frame(self, **self.style.surface)
        self.body.pack(side="top", fill="both", pady=2)
        self.__ref = Frame(self.body, height=0, width=0, **self.style.surface)
        self.__ref.pack(side="top")
        self._collapsed = False

    @classmethod
    def _load_icons(cls):
        if cls.__icons_loaded:
            return
        cls.EXPAND = get_icon_image("triangle_down", 14, 14)
        cls.COLLAPSE = get_icon_image("triangle_up", 14, 14)

    def update_state(self):
        self.__ref.pack(side="top")

    def collapse(self, *_):
        if not self._collapsed:
            self.body.pack_forget()
            self._collapse_btn.config(image=self.EXPAND)
            self.pack_propagate(0)
            self.config(height=20)
            self._collapsed = True

    def clear_children(self):
        self.body.clear_children()

    def expand(self, *_):
        if self._collapsed:
            self.body.pack(side="top", fill="both")
            self.pack_propagate(1)
            self._collapse_btn.config(image=self.COLLAPSE)
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
        self.config(**self.style.surface, **self.style.no_highlight, width=20)
        self.features = {}

    def remove(self, feature):
        self.delete(feature.indicator)
        self.features.pop(feature)
        self._redraw()

    def _redraw(self):
        y = 0
        features = sorted(self.features.keys(), key=lambda x: x.get_pref("pane::index"))
        for feature in features:
            indicator = self.features[feature]
            font = FontStyle(self, self.itemconfig(indicator).get("font", "TkDefaultFont")[3])
            y += font.measure(feature.display_name) + 20
            self.coords(indicator, 18, y)

    def add_feature(self, feature):
        indicator = self.create_text(
            0, 0, angle=90, text=feature.display_name, fill=self.style.colors.get("accent"),
            anchor="sw", activefill=self.style.colors.get("primarydarkaccent")
        )
        self.tag_bind(indicator, "<Button-1>", lambda event: self.toggle_feature(feature))
        feature.indicator = indicator
        self.features[feature] = indicator
        self._redraw()

    def change_feature(self, new, old):
        self.tag_unbind(old.indicator, "<Button-1>")
        self.tag_bind(old.indicator, "<Button-1>", lambda event: self.toggle_feature(new))
        self.features.pop(old)
        self.features[new] = old.indicator
        new.indicator = old.indicator

    def deselect(self, feature):
        self.itemconfig(feature.indicator, fill=self.style.colors.get("primary"))

    def select(self, feature):
        self.itemconfig(feature.indicator, fill=self.style.colors.get("accent"))

    def close_all(self):
        for feature in self.features:
            self.deselect(feature)

    def toggle_feature(self, feature):
        feature.toggle()


class SearchBar(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.no_highlight, **self.style.surface)
        self._entry = Entry(self, **self.style.input, **self.style.no_highlight)
        self._clear_btn = Button(self, image=get_icon_image("close", 15, 15),
                                 **self.style.button, width=25, height=25)
        self._clear_btn.pack(side="right", fill="y")
        self._clear_btn.on_click(self._clear)
        Label(self, **self.style.text, image=get_icon_image("search", 15, 15)).pack(side="left")
        self._entry.pack(side="left", fill="both", expand=True, padx=2)
        self._entry.on_entry(self._change)
        self._on_change = None
        self._on_clear = None

    def focus_set(self):
        super().focus_set()
        self._entry.focus_set()

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


class DesignPad(ScrollableInterface, Frame):
    PADDING = 10

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._frame = Canvas(self, **kwargs, **self.style.no_highlight, **self.style.surface)
        self._frame.grid(row=0, column=0, sticky='nswe')
        self._scroll_y = ttk.Scrollbar(master, orient='vertical', command=self._y_scroll)
        self._scroll_x = ttk.Scrollbar(master, orient='horizontal', command=self._x_scroll)
        self._frame.configure(yscrollcommand=self._scroll_y.set, xscrollcommand=self._scroll_x.set)
        self.columnconfigure(0, weight=1)  # Ensure the design_pad gets the rest of the left horizontal space
        self.rowconfigure(0, weight=1)
        self._frame.bind('<Configure>', self.on_configure)
        self.bind('<Configure>', self.on_configure)
        self._child_map = {}
        self._on_scroll = None
        # Ensure scroll_region always begins at 0, 0
        # To achieve this we need a line/point at position 2, 2 with the minimum possible width of 1
        # Without this workaround positioning on the design pad becomes unstable
        self._frame.create_line(2, 2, 2, 2)

    def on_mousewheel(self, event):
        try:
            if event.state & EventMask.CONTROL and self._scroll_x.winfo_ismapped():
                self.handle_wheel(self._frame, event)
            elif self._scroll_y.winfo_ismapped():
                self.handle_wheel(self._frame, event)
        except TclError:
            pass

    def scroll_position(self):
        return self._scroll_y.get()

    def on_scroll(self, callback, *args, **kwargs):
        self._on_scroll = lambda: callback(*args, **kwargs)

    def _y_scroll(self, *args):
        self._frame.yview(*args)
        if self._on_scroll:
            self._on_scroll()

    def _x_scroll(self, *args):
        self._frame.xview(*args)
        if self._on_scroll:
            self._on_scroll()

    def _show_y_scroll(self, flag):
        if flag and not self._scroll_y.winfo_ismapped():
            self._scroll_y.grid(in_=self, row=0, column=1, sticky='ns')
        elif not flag:
            self._scroll_y.grid_forget()
        self.update_idletasks()

    def _show_x_scroll(self, flag):
        if flag and not self._scroll_x.winfo_ismapped():
            self._scroll_x.grid(in_=self, row=1, column=0, sticky='ew')
        elif not flag:
            self._scroll_x.grid_forget()
        self.update_idletasks()

    def on_configure(self, *_):
        try:
            self.update_idletasks()
            scroll_region = self._frame.bbox('all')
        except TclError:
            return
        if not scroll_region:
            logging.error("failed to acquire scroll region")
            return

        scroll_w = scroll_region[2] - scroll_region[0]
        scroll_h = scroll_region[3] - scroll_region[1]

        self._show_y_scroll(scroll_h > self.winfo_height())
        self._show_x_scroll(scroll_w > self.winfo_width())

        self._frame.config(scrollregion=scroll_region)

    def canvasx(self, x):
        return self._frame.canvasx(x)

    def canvasy(self, y):
        return self._frame.canvasy(y)

    def canvas_bounds(self, bounds):
        return (
            self.canvasx(bounds[0]), self.canvasy(bounds[1]),
            self.canvasx(bounds[2]), self.canvasy(bounds[3]),
        )

    def bound_limits(self):
        """
        Get the maximum scrolling bounds relative to current view point

        :return: tuple representing max bounding rectangle
        """
        return (
            self.canvasx(0) * -1,
            self.canvasy(0) * -1,
            math.inf,
            math.inf,
        )

    def place_child(self, child, **kw):
        x = kw.get("x", 0)
        y = kw.get("y", 0)
        w = kw.get("width", 1)
        h = kw.get("height", 1)
        self.forget_child(child)
        if child in self._child_map:
            self.config_child(child, **kw)
        else:
            window = self._frame.create_window(x, y, window=child, width=w, height=h, anchor='nw')
            self._child_map[child] = window
        self.on_configure()

    def bbox(self, child):
        # return the canvas bbox if possible else use the normal bound
        # canvas bbox is more accurate
        if self._child_map.get(child) is not None:
            return self._frame.bbox(self._child_map[child])
        return geometry.relative_bounds(geometry.bounds(child), self._frame)

    def config_child(self, child, **kw):
        x1, y1, x2, y2 = self.bbox(child)
        x = kw.get("x", x1)
        y = kw.get("y", y1)
        w = kw.get("width", x2 - x1)
        h = kw.get("height", y2 - y1)
        if not kw:
            return {
                "x": x, "y": y, "width": w, "height": h
            }
        self._frame.coords(self._child_map[child], x, y)
        self._frame.itemconfigure(self._child_map[child], width=w, height=h)
        self.on_configure()

    def forget_child(self, child):
        if self._child_map.get(child) is not None:
            self._frame.delete(self._child_map[child])
            self._child_map.pop(child)

    def lift_child(self, child, above_this=None):
        above_this = self._child_map[above_this] if above_this in self._child_map else 'all'
        if self._child_map.get(child) is not None:
            self._frame.tag_raise(self._child_map[child], above_this)

    def configure(self, cnf=None, **kw):
        self._frame.configure(cnf, **kw)
        return super().configure(cnf, **kw)

    config = configure


class Pane(Frame):

    def __init__(self, master, **cnf):
        super(Pane, self).__init__(master, **cnf)
        self.config(**self.style.surface)
        self.drag_text = "Pane"
        self._header = Frame(self, **self.style.surface, **self.style.highlight_dim, height=30)
        self._header.pack(side="top", fill="x")
        self._header.pack_propagate(0)
        self._header.render_drag = self._render_header_drag
        self._header.drag_start_pos = self._header_drag_start_pos
        self._header.on_drag = self.on_pane_drag
        self._header.on_drag_end = self._header_drag_end
        self._search_bar = SearchBar(self._header, height=20)
        self._search_bar.on_query_clear(self.on_search_clear)
        self._search_bar.on_query_change(self.on_search_query)
        self._drag_label = None

    def _render_header_drag(self, window):
        self._drag_label = Label(window, **self.style.text_accent, text=self.drag_text)
        self._drag_label.config(**self.style.highlight_passive)
        self._drag_label.pack()

    def _header_drag_start_pos(self, event):
        if not self._drag_label:
            return event.x_root, event.y_root
        w, h = self._drag_label.winfo_reqwidth() // 2, self._drag_label.winfo_reqheight() // 2
        return event.x_root - w, event.y_root - h

    def _header_drag_end(self, event):
        self._drag_label = None
        self.on_pane_drop(event)

    def on_pane_drag(self, event):
        """
        Called when the pane is being dragged. Use this to perform any necessary operations
        """
        pass

    def on_pane_drop(self, event):
        """
        Called when the pane is dropped. Use this to perform any necessary finalizations
        """
        pass

    def on_search_query(self, query: str):
        """
        Called when inbuilt search feature is queried. Use the query string to display the
        necessary search results
        :param query: String of current search query
        :return: None
        """
        pass

    def on_search_clear(self):
        """
        Called when the user terminates the search bar. Ensure you make a call to the super
        method for the bar to actually get closed. This method can be used to restore the
        feature state to when not performing a search
        :return:
        """
        self.quit_search()
        pass

    def start_search(self, *_):
        self._search_bar.place(relwidth=1, relheight=1)
        self._search_bar.lift()
        self._search_bar.focus_set()

    def quit_search(self, *_):
        self._search_bar.place_forget()


class ThemeBar(Frame):

    def __init__(self, master, **cnf):
        super(ThemeBar, self).__init__(master, **cnf)
        self.config(**self.style.surface)
        self._label = Label(self, **self.style.text_passive, text=_("Theme"))
        self._label.pack(side="left", fill="y", padx=3)
        self._theme = Spinner(self)
        self._theme.pack_propagate(0)
        self._theme.config(width=100)
        self._theme.on_change(self._set_theme)
        self._theme.pack(side="left", fill="y", padx=3)
        self._sub_theme = Spinner(self)
        self._sub_theme.pack_propagate(0)
        self._sub_theme.config(width=50)
        self._sub_theme.on_change(self._set_subtheme)
        self._sub_theme.pack(side="left", fill="y")

    def _update_subthemes(self, theme):
        if not theme.sub_themes:
            self._sub_theme.pack_forget()
            return
        self._sub_theme.pack(side="left", fill="y")
        self._sub_theme.set_values(theme.sub_themes)

    def _set_subtheme(self, sub_theme):
        self._theme.get().set(sub_theme)
        self._sub_theme.set(sub_theme)
        self.event_generate("<<ThemeBarChanged>>")

    def _set_theme(self, theme):
        theme.set()
        self._update_subthemes(theme)
        self.event_generate("<<ThemeBarChanged>>")

    def load_themes(self, themes):
        self._theme.set_values(themes)

    def get(self):
        return self._theme.get(), self._sub_theme.get()

    def set(self, theme, sub_theme=None):
        theme.set(sub_theme)
        self._theme.set(theme)
        self._update_subthemes(theme)
        if sub_theme:
            self._sub_theme.set(sub_theme)
