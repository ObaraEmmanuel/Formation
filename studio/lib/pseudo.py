import functools
import tkinter
from enum import Enum

from hoverset.ui.icons import get_icon, get_icon_image
from studio import layouts
from studio.lib.properties import get_properties
from studio.ui.highlight import WidgetHighlighter
from studio.ui.tree import MalleableTree


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
        self.level = 0
        self.layout = None
        self._properties = get_properties(self)
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

    def get_prop(self, prop):
        return self[prop]

    @property
    def properties(self):
        for key in self._properties:
            self._properties[key]["value"] = self.get_prop(key)
        return self._properties

    def create_menu(self):
        """
        Add actions to the widget drop down. Override this method and use hoverset
        menu format to add items to the menu
        :return:
        """
        return ()


class Container(PseudoWidget):
    LAYOUTS = layouts.layouts

    def setup_widget(self):
        self.parent = self.master
        self._level = 0
        self._children = []
        self.temporal_children = []
        self._highlighter = WidgetHighlighter(self.master)
        if len(self.LAYOUTS) == 0:
            raise ValueError("No layouts have been defined")
        self.layout_strategy = layouts.FrameLayoutStrategy(self)
        super().setup_widget()

    def show_highlight(self, *_):
        self._highlighter.highlight(self)

    def clear_highlight(self):
        self._highlighter.clear()
        self._temporal_children = []

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self._level = value
        # We need to change the levels of of the layout's _children
        # Failure to do this results in nasty crashes since the layout may be passed to one of its child layouts
        # which will try to position the layout (its parent!) within its self. A recursion hell!
        for child in self._children:
            child.level = self.level + 1

    def position_layout(self, layout):
        """
        Position the layout to occupy the available space on the container widget. Different containers have different
        strategies to achieve this behaviour therefore override to obtained the required layout
        :param layout: The layout to be positioned
        :return:
        """
        layout.pack(fill="both", expand=True)

    def get_prop(self, prop):
        if prop == 'layout':
            return self.layout_strategy.name
        return super().get_prop(prop)

    @property
    def properties(self):
        prop = super().properties
        prop["layout"] = {
            "name": "layout",
            "display_name": "layout",
            "type": "layout",
            "allow_blank": False,
            "options": Container.LAYOUTS,
            "value": self.layout_strategy.__class__,
        }
        return prop

    def _get_layout_by_name(self, name):
        layout = list(filter(lambda l: l.name == name, self.LAYOUTS))
        if len(layout) == 1:
            return layout[0]
        elif len(layout) == 0:
            raise ValueError(f"No layout with name {name} found!")
        else:
            raise ValueError(f"Multiple implementations of layout {name} found")

    def _switch_layout(self, layout_class):
        if layout_class == self.layout_strategy.__class__:
            return
        self.layout_strategy = layout_class(self)
        self.layout_strategy.initialize()

    def configure(self, cnf=None, **kwargs, ):
        if cnf is None:
            cnf = {}
        if 'layout' in kwargs:
            self._switch_layout(kwargs['layout'])
            kwargs.pop('layout')
        return super().configure(cnf, **kwargs)

    def _get_layouts_as_menu(self):
        return [
            ("command", i.name, get_icon_image(i.icon, 14, 14),
             functools.partial(self._switch_layout, i), {}
             ) for i in self.LAYOUTS
        ]

    def create_menu(self):
        return (
            ("separator",),
            ("cascade", "Change layout", get_icon_image("grid", 14, 14), None, {"menu": (
                self._get_layouts_as_menu()
            )})
        )

    def parse_bounds(self, bounds):
        return {
            "x": bounds[0],
            "y": bounds[1],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }

    def position(self, widget, bounds):
        widget.place(in_=self, **self.parse_bounds(bounds))

    #  =========================================== Rerouting methods ==================================================

    def restore_widget(self, widget):
        self.layout_strategy.restore_widget(widget)

    def add_widget(self, widget, bounds):
        self.layout_strategy.add_widget(widget, bounds)

    def widget_released(self, widget):
        self.layout_strategy.widget_released(widget)

    def move_widget(self, widget, bounds):
        self.layout_strategy.move_widget(widget, bounds)

    def resize_widget(self, widget, bounds):
        self.layout_strategy.resize_widget(widget, bounds)

    def get_restore(self, widget):
        return self.layout_strategy.get_restore(widget)

    def remove_widget(self, widget):
        self.layout_strategy.remove_widget(widget)

    def add_new(self, widget, x, y):
        self.layout_strategy.add_new(widget, x, y)

    def apply(self, prop, value, widget):
        self.layout_strategy.apply(prop, value, widget)

    def definition_for(self, widget):
        return self.layout_strategy.__class__.definition_for(widget)


class LabelFrameCorrection:

    def _set_correction(self):
        if hasattr(self, '_corrected'):
            return
        self._ref_point = tkinter.Frame(self)
        self._ref_point.lower()
        self._ref_point.place(x=0, y=0)
        self._corrected = True

    def parse_bounds(self, bounds):
        self._set_correction()
        return {
            "x": bounds[0] - self._ref_point.winfo_x(),
            "y": bounds[1] - self._ref_point.winfo_y(),
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }
