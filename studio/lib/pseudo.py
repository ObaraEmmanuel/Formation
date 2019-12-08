from enum import Enum

from hoverset.ui.icons import get_icon
from studio.ui.tree import MalleableTree
from studio.properties import get_properties


class Groups(Enum):
    widget = 'Widget'
    input = 'Input'
    container = 'Container'
    layout = 'Layout'


class PseudoWidget:
    display_name = 'Widget'
    group = Groups.widget
    icon = get_icon("play")
    impl = None

    def setup_widget(self):
        self._properties = get_properties(self)
        print(self._properties)
        self.set_name(self.id)
        self.node = None

    def set_name(self, name):
        pass

    def set_tree_reference(self, node: MalleableTree.Node):
        self.node = node
        self.node.is_terminal = self._is_terminal

    def deselect_(self):
        if self.node is None:
            return
        self.node.deselect()

    def select_(self):
        if self.node is None:
            return
        self.node.deselect()

    @property
    def identity(self):
        return {
            "class": {
                "name": "class",
                "display_name": "class",
                "type": "text",
                "readonly": True,
                "value": f"{self.impl.__module__}.{self.impl.__name__}"
            },
            "id": {
                "name": "id",
                "display_name": "widget id",
                "type": "text",
                "readonly": False,
                "value": self.id
            },
        }

    @property
    def properties(self):
        for key in self._properties:
            self._properties[key]["value"] = self[key]
        return self._properties
