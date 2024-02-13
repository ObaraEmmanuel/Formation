import tkinter

from hoverset.ui.widgets import Button, ToggleButton, Label
from hoverset.ui.icons import get_icon_image

from studio.ui.widgets import Pane
from studio.ui.tree import MalleableTreeView
from studio.feature.component_tree import ComponentTreeView
from studio.debugtools import common


class ElementTreeView(ComponentTreeView):

    class Node(MalleableTreeView.Node):
        # debugger widget to be ignored during loading
        # will be set at runtime
        debugger = None

        def __init__(self, master=None, **config):
            super().__init__(master, **config)
            self.widget = config.get("widget")
            self.widget.bind('<Map>', self.on_map, add=True)
            self.widget.bind('<Unmap>', self.on_unmap, add=True)
            setattr(self.widget, "_dbg_node", self)
            equiv = common.get_studio_equiv(self.widget)
            icon = equiv.icon if equiv else 'play'
            self.name_pad.configure(text=self.extract_name(self.widget))
            self.icon_pad.configure(image=get_icon_image(icon, 15, 15))
            self._loaded = False
            if not self.widget.winfo_ismapped():
                self.on_unmap()

        def on_map(self, *_):
            self.name_pad.configure(**self.style.text)

        def on_unmap(self, *_):
            self.name_pad.configure(**self.style.text_passive)

        @property
        def loaded(self):
            return self._loaded

        def update_preload_status(self, added):
            if self._loaded:
                return
            if added or self.widget.winfo_children():
                # widget can expand
                self._set_expander(self.COLLAPSED_ICON)
            else:
                self._set_expander(self.BLANK)

        def extract_name(self, widget):
            if isinstance(widget, tkinter.BaseWidget):
                return str(widget._name).strip("!")
            return 'root'

        def load(self):
            # lazy loading
            # nodes will be loaded when parent node is expanded
            if self._loaded:
                return
            for child in self.widget.winfo_children():
                if getattr(child, "_dbg_ignore", False):
                    continue
                self.add_as_node(widget=child).update_preload_status(False)
                if not getattr(child, "_dbg_hooked", False):
                    ElementTreeView.Node.debugger.hook_widget(child)
            self._loaded = True

        def expand(self):
            # load widgets first
            self.load()
            super().expand()

    def initialize_tree(self):
        super(ElementTreeView, self).initialize_tree()
        self._show_empty("No items detected")

    def expand_to(self, widget):
        parent = widget.nametowidget(widget.winfo_parent())
        hierarchy = [parent]
        while parent not in (self.Node.debugger.root, self.Node.debugger):
            parent = parent.nametowidget(parent.winfo_parent())
            hierarchy.append(parent)
        if not parent:
            return
        for p in reversed(hierarchy):
            p._dbg_node.expand()

        assert hasattr(widget, "_dbg_node")
        return widget._dbg_node


class ElementPane(Pane):
    name = "Widget tree"
    MAX_STARTING_DEPTH = 4

    def __init__(self, master, debugger):
        super(ElementPane, self).__init__(master)
        Label(self._header, **self.style.text_accent, text=self.name).pack(side="left")

        ElementTreeView.Node.debugger = debugger
        self._tree = ElementTreeView(self)
        self._tree.pack(side="top", fill="both", expand=True, pady=4)
        self._tree.allow_multi_select(True)
        self._tree.on_select(self.on_select)

        self._search_btn = Button(
            self._header, **self.style.button,
            image=get_icon_image("search", 15, 15), width=25, height=25,
        )
        self._search_btn.pack(side="right", padx=2)
        self._search_btn.on_click(self.start_search)

        self._reload_btn = Button(
            self._header, **self.style.button,
            image=get_icon_image("reload", 15, 15), width=25, height=25,
        )
        self._reload_btn.pack(side="right", padx=2)
        self._reload_btn.tooltip("reload tree")

        self._toggle_btn = Button(
            self._header, image=get_icon_image("chevron_down", 15, 15),
            **self.style.button, width=25, height=25
        )
        self._toggle_btn.pack(side="right", padx=2)

        self._select_btn = ToggleButton(
            self._header, **self.style.button,
            image=get_icon_image("cursor", 15, 15), width=25, height=25,
        )
        self._select_btn.pack(side="right", padx=2)
        self._select_btn.tooltip("select element to inspect")

        self.debugger = debugger
        self._tree.add_as_node(widget=debugger.root).update_preload_status(False)

        self.debugger.bind("<<WidgetCreated>>", self.on_widget_created)
        self.debugger.bind("<<WidgetDeleted>>", self.on_widget_deleted)
        self.debugger.bind("<<WidgetModified>>", self.on_widget_modified)

        tkinter.Misc.bind_all(self.debugger.root, "<Motion>", self.on_motion)
        tkinter.Misc.bind_all(self.debugger.root, "<Button-1>", self.on_widget_tap)
        tkinter.Misc.bind_all(self.debugger.root, "<Button-3>", self.on_widget_tap)
        tkinter.Misc.bind_all(self.debugger.root, "<Map>", self.on_widget_map)
        tkinter.Misc.bind_all(self.debugger.root, "<Unmap>", self.on_widget_unmap)
        self.highlighted = None

    @property
    def selected(self):
        return self._tree.get()

    def on_select(self):
        self.debugger.selection.set(map(lambda node: node.widget, self._tree.get()))

    def on_widget_tap(self, event):
        if self._select_btn.get():
            try:
                # widget = self.debugger.root.winfo_containing(event.x_root, event.y_root)
                widget = event.widget
                # print(widget)
                if widget.winfo_toplevel() == self.debugger or getattr(widget, "_dbg_ignore", False):
                    widget = None
            except (KeyError, AttributeError):
                widget = None

            if widget:
                node = self._tree.expand_to(widget)
                if node:
                    self._tree.see(node)
                    node.select(event)

    def on_motion(self, event):
        if self._select_btn.get():
            try:
                # widget = self.debugger.root.winfo_containing(event.x_root, event.y_root)
                widget = event.widget
                if widget.winfo_toplevel() == self.debugger or getattr(widget, "_dbg_ignore", False):
                    widget = None
                # print(f"motion : {widget} <> {event.widget}")
            except (KeyError, AttributeError):
                widget = None
            self.debugger.highlight_widget(widget)
            self.highlighted = widget

    def on_widget_created(self, _):
        widget = self.debugger.active_widget
        parent_node = getattr(widget.master, "_dbg_node", None)
        if parent_node:
            if parent_node.loaded:
                parent_node.add_as_node(widget=widget)
                self.debugger.hook_widget(widget)
            else:
                parent_node.update_preload_status(True)

    def on_widget_deleted(self, _):
        widget = self.debugger.active_widget
        parent_node = getattr(widget.master, "_dbg_node", None)
        if parent_node:
            if parent_node.loaded:
                node = widget._dbg_node
                if node in self.selected:
                    self._tree.toggle_from_selection(node)
                parent_node.remove(widget._dbg_node)
            else:
                parent_node.update_preload_status(False)

    def on_widget_modified(self, _):
        if self.debugger.active_widget not in self.selected:
            return

    def on_widget_map(self, _):
        pass

    def on_widget_unmap(self, _):
        pass
