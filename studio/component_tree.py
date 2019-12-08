from studio.lib.pseudo import PseudoWidget
from studio.ui.tree import MalleableTree
from hoverset.ui.widgets import Frame, Label
from hoverset.ui.icons import get_icon


class ComponentTreeView(MalleableTree):

    class Node(MalleableTree.Node):

        def __init__(self, master=None, **config):
            super().__init__(master, **config)
            self.widget: PseudoWidget = config.get("widget")
            self.name_pad.config(text=self.widget.id)
            self.icon_pad.config(text=self.widget.icon)

        def widget_modified(self, widget):
            self.widget = widget
            self.name_pad.config(text=self.widget.id)
            self.icon_pad.config(text=self.widget.icon)


class ComponentTree(Frame):

    def __init__(self, master, studio,  **cnf):
        super().__init__(master, **cnf)
        self.studio = studio
        self._header = Frame(self, **self.style.dark, **self.style.dark_highlight_dim, height=30)
        self._header.pack(side="top", fill="x")
        self._header.pack_propagate(0)
        self.config(**self.style.dark)
        Label(self._header, **self.style.dark_text_passive, text="Component tree").pack(side="left")

        self._tree = ComponentTreeView(self)
        self._tree.pack(side="top", fill="both", expand=True, pady=4)
        # self._tree.sample()

        self._node_map = {}
        self._selected = None

    def add(self, widget: PseudoWidget, parent=None):
        parent: ComponentTreeView.Node = self._node_map.get(parent)
        if parent is None:
            node = self._tree.add_as_node(widget=widget)
        else:
            node = parent.add_as_node(widget=widget)
        self._node_map[widget] = node

    def select(self, widget):
        node = self._node_map.get(widget)
        if node:
            node.select()
            self._selected = node
        elif widget is None:
            if self._selected:
                self._selected.deselect()
                self._selected = None

    def widget_modified(self, widget, widget2=None):
        widget2 = widget2 if widget2 else widget
        self._node_map[widget2].widget_modified(widget2)
