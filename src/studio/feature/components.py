from functools import partial
from tkinter import BooleanVar

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Spinner, EventMask, Button
from hoverset.ui.windows import DragWindow
from studio.preferences import Preferences
from studio.feature._base import BaseFeature
from studio.feature.design import Designer
from studio.lib import legacy, native
from studio.lib.pseudo import PseudoWidget, Container

pref = Preferences.acquire()


class Component(Frame):
    drag_popup = None
    drag_active = None

    def __init__(self, master, component: PseudoWidget.__class__):
        super().__init__(master)
        self.config(**self.style.surface)
        self._icon = Label(self, **self.style.text_accent, image=get_icon_image(component.icon, 15, 15))
        self._icon.pack(side="left")
        self._text = Label(self, **self.style.text, anchor="w", text=component.display_name)
        self._text.pack(side="left", fill="x")
        self.bind("<Enter>", self.select)
        self.bind("<Leave>", self.deselect)
        self.component = component

        self.bind_all("<Motion>", self.drag)
        self.bind_all("<ButtonRelease-1>", self.release)

    def select(self, *_):
        self.config_all(**self.style.hover)

    def deselect(self, *_):
        self.config_all(**self.style.surface)

    def drag(self, event):
        # If cursor is moved while holding the left button down for the first time we begin drag
        if event.state & EventMask.MOUSE_BUTTON_1 and not self.drag_active:
            self.drag_popup = DragWindow(self.window).set_position(event.x_root, event.y_root)
            Label(self.drag_popup, text=self.component.display_name).pack()
            self.drag_active = True
        elif self.drag_active:
            widget = self.event_first(event, self, Designer)
            if isinstance(widget, Designer):
                widget.react(event)
            self.drag_popup.set_position(event.x_root, event.y_root)

    def release(self, event):
        if not self.drag_active:
            return
        self.drag_active = False
        self.drag_popup.destroy()
        self.drag_popup = None
        widget = self.event_first(event, self, Container)
        if isinstance(widget, Container):
            widget.add_new(self.component, event.x_root, event.y_root)


class Selector(Label):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.name = cnf.get("text")
        self.config(**self.style.text, anchor="w")

    def select(self):
        self.config(**self.style.hover)

    def deselect(self):
        self.config(**self.style.surface)

    def __eq__(self, other):
        if isinstance(other, Selector):
            return self.name == other.name
        else:
            super().__eq__(other)


class ComponentPane(BaseFeature):
    CLASSES = {
        "native": {"widgets": native.widgets},
        "legacy": {"widgets": legacy.widgets},
    }
    name = "Components"
    _var_init = False
    _defaults = {
        **BaseFeature._defaults,
        "widget_set": "native"
    }

    def __init__(self, master, studio=None, **cnf):
        if not self._var_init:
            self._init_var(studio)
        super().__init__(master, studio, **cnf)

        f = Frame(self, **self.style.surface)
        f.pack(side="top", fill="both", expand=True, pady=4)
        f.pack_propagate(0)

        self._widget_set = Spinner(self._header, width=150)
        self._widget_set.config(**self.style.no_highlight)
        self._widget_set.set_values(list(self.CLASSES.keys()))
        self._widget_set.pack(side="left")
        self._widget_set.on_change(self.collect_groups)
        self._select_pane = ScrolledFrame(f, width=150)
        self._select_pane.place(x=0, y=0, relwidth=0.4, relheight=1)

        self._search_btn = Button(self._header, image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)
        self._search_selector = Label(self._select_pane.body, **self.style.text, text="search", anchor="w")
        self._search_selector.configure(**self.style.hover)

        self._widget_pane = ScrolledFrame(f, width=150, bg="orange")
        self._select_pane.body.config(**self.style.surface)
        self._widget_pane.place(relx=0.4, y=0, relwidth=0.6, relheight=1)

        self._pool = {}
        self._selectors = []
        self._selected = None
        self._component_cache = None
        self.collect_groups(self.get_pref("widget_set"))

    def _init_var(self, master=None):
        self._var_init = True
        for widget_set in self.CLASSES:
            self.CLASSES[widget_set]["var"] = BooleanVar(master, False)

    def _widget_sets_as_menu(self):
        return [
            ("checkbutton",  # Type checkbutton
             i.capitalize(),  # Label as title case
             None,  # Image
             partial(self.collect_groups, i),  # The callback
             {"variable": self.CLASSES[i]["var"]}  # Additional config including the variable associated
             ) for i in self.CLASSES
        ]

    @property
    def selectors(self):
        return self._selectors

    def create_menu(self):
        return (
            ("command", "Search", get_icon_image("search", 14, 14), self.start_search, {}),
            ("cascade", "Widget set", None, None, {"menu": (
                *self._widget_sets_as_menu(),
            )}),
        )

    def collect_groups(self, widget_set):
        for other_set in [i for i in self.CLASSES if i != widget_set]:
            self.CLASSES[other_set]["var"].set(False)
        self.CLASSES[widget_set]["var"].set(True)
        self._widget_set.set(widget_set)
        self._select_pane.clear_children()
        self._pool = {}
        components = self.CLASSES.get(widget_set)["widgets"]
        for component in components:
            group = component.group.name
            if group in self._pool:
                self._pool[group].append(Component(self._widget_pane.body, component))
            else:
                self._pool[group] = [Component(self._widget_pane.body, component)]
        self.render_groups()
        # component pool has changed so invalidate the cache
        self._component_cache = None
        self.set_pref("widget_set", widget_set)

    def get_components(self):
        if self._component_cache:
            return self._component_cache
        else:
            # flatten component pool and store to cache
            self._component_cache = [j for i in self._pool.values() for j in i]
            return self._component_cache

    def select(self, selector):
        if self._selected is not None:
            self._selected.deselect()
        selector.select()
        self._selected = selector
        self._widget_pane.clear_children()
        for component in self._pool[selector.name]:
            component.pack(side="top", pady=2, fill="x")

    def render_groups(self):
        self._selectors = []
        for group in self._pool:
            self.add_selector(Selector(self._select_pane.body, text=group))
        if len(self._selectors):
            self.select(self._selectors[0])

    def add_selector(self, selector):
        self._selectors.append(selector)
        selector.bind("<Button-1>", lambda *_: self.select(selector))
        selector.pack(side="top", pady=2, fill="x")

    def hide_selectors(self):
        for selector in self._selectors:
            selector.pack_forget()

    def show_selectors(self):
        for selector in self._selectors:
            selector.pack(side="top", pady=2, fill="x")

    def start_search(self, *_):
        super().start_search()
        self._widget_pane.scroll_to_start()
        if self._selected is not None:
            self._selected.deselect()
        self.hide_selectors()
        self._search_selector.pack(side="top", pady=2, fill="x")
        self._widget_pane.clear_children()
        # Display all components by running an empty query
        self.on_search_query("")

    def on_search_clear(self):
        super().on_search_clear()
        if len(self._selectors):
            self.select(self._selectors[0])
        self._search_selector.pack_forget()
        self.show_selectors()

    def on_search_query(self, query):
        for component in self.get_components():
            if query.lower() in component.component.display_name.lower():
                component.pack(side="top", pady=2, fill="x")
            else:
                component.pack_forget()
