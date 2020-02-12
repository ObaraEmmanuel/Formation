from hoverset.ui.icons import get_icon_image, get_icon
from hoverset.ui.widgets import Button
from studio.feature import BaseFeature
from studio.lib.pseudo import PseudoWidget
from studio.ui.tree import MalleableTree


class ComponentTreeView(MalleableTree):

    class Node(MalleableTree.Node):

        def __init__(self, master=None, **config):
            super().__init__(master, **config)
            self.widget: PseudoWidget = config.get("widget")
            self.widget.node = self
            self.name_pad.config(text=self.widget.id)
            self.icon_pad.config(text=self.widget.icon)

        def widget_modified(self, widget):
            self.widget = widget
            self.name_pad.config(text=self.widget.id)
            self.icon_pad.config(text=self.widget.icon)


class ComponentTree(BaseFeature):
    name = "Component Tree"
    side = "left"
    icon = "treeview"

    def __init__(self, master, studio=None,  **cnf):
        super().__init__(master, studio, **cnf)
        self._tree = ComponentTreeView(self)
        self._tree.pack(side="top", fill="both", expand=True, pady=4)
        # self._tree.sample()
        self._tree.on_select(self._trigger_select)
        self._toggle_btn = Button(self._header, text=get_icon("chevron_down"), **self.style.dark_button, width=25,
                                  height=25)
        self._toggle_btn.pack(side="right")
        self._toggle_btn.on_click(self._toggle)

        self._node_map = {}
        self._selected = None
        self._expanded = False

    def create_menu(self):
        return (
            ("command", "Expand all", get_icon_image("chevron_down", 14, 14), self._expand, {}),
            ("command", "Collapse all", get_icon_image("chevron_up", 14, 14), self._collapse, {})
        )

    def _expand(self):
        self._tree.expand_all()
        self._toggle_btn.config(text=get_icon("chevron_up"))
        self._expanded = True

    def _collapse(self):
        self._tree.collapse_all()
        self._toggle_btn.config(text=get_icon("chevron_down"))
        self._expanded = False

    def _toggle(self, *_):
        if self._expanded:
            self._collapse()
        else:
            self._expand()

    def on_widget_add(self, widget: PseudoWidget, parent=None):
        if parent is None:
            node = self._tree.add_as_node(widget=widget)
        else:
            parent = parent.node
            node = parent.add_as_node(widget=widget)

        # Set up as follows
        # (type, label, icon, command/callback, additional_configuration={})
        # use also get_icon_image("image_key", width, height)
        node.set_up_context(self.studio.menu_template + widget.create_menu())

    def _trigger_select(self):
        if self._selected and self._selected.widget == self._tree.get().widget:
            return
        self.studio.select(self._tree.get().widget, self)
        self._selected = self._tree.get()

    def select(self, widget):
        if widget:
            node = widget.node
            self._selected = node
            node.select(None, True)  # Select node silently to avoid triggering a duplicate selection event
        elif widget is None:
            if self._selected:
                self._selected.deselect()
                self._selected = None

    def on_select(self, widget):
        self.select(widget)

    def on_widget_delete(self, widget):
        widget.node.remove()

    def on_widget_restore(self, widget):
        widget.layout.node.add(widget.node)

    def on_widget_layout_change(self, widget):
        node = widget.node
        if widget.layout == self.studio.designer:
            self._tree.insert(None, node)
        else:
            parent = widget.layout.node
            parent.insert(None, node)

    def on_widget_change(self, old_widget, new_widget=None):
        new_widget = new_widget if new_widget else old_widget
        new_widget.node.widget_modified(new_widget)
