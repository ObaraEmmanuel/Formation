import functools
import logging
import os.path
import tkinter
import tkinter.ttk
from enum import Enum

from hoverset.data.images import load_tk_image, load_image, load_image_to_widget
from hoverset.ui.icons import get_icon_image
from hoverset.ui.menu import MenuUtils
from hoverset.util.execution import import_path
from studio.lib import layouts
from studio.lib.variables import VariableManager
from studio.lib.properties import get_properties
from studio.ui.highlight import WidgetHighlighter
from studio.ui.tree import MalleableTree


class Groups(Enum):
    widget = 'Widget'
    input = 'Input'
    container = 'Container'
    layout = 'Layout'
    custom = 'Custom'


class _ImageIntercept:
    __slots__ = []

    @staticmethod
    def set(widget, value, prop='image'):
        try:
            if os.path.isfile(str(value)):
                image = load_image(value)
                load_image_to_widget(widget, image, prop)
            else:
                # if value is invalid remove image
                widget.config({prop: ''})
            # for the sake of consistency we set the path regardless
            setattr(widget, f'{prop}_path', value)
        except Exception as e:
            logging.error(e)
            return

    @staticmethod
    def get(widget, prop='image'):
        return getattr(widget, f'{prop}_path', '')


class _IdIntercept:
    __slots__ = []

    @staticmethod
    def set(widget, value, _):
        widget.id = value

    @staticmethod
    def get(widget, _):
        return widget.id


class _VariableIntercept:
    __slots__ = []

    @staticmethod
    def set(widget, value, prop):
        if hasattr(value, 'handle'):
            setattr(widget, f"__{prop}", value.handle.name)
        else:
            setattr(widget, f"__{prop}", value)
        if isinstance(value, str):
            var = list(filter(lambda x: x.name == value, VariableManager.variables))
            if var:
                value = var[0].var
        widget.config(**{prop: value})

    @staticmethod
    def get(widget, prop):
        if hasattr(widget, f"__{prop}"):
            return getattr(widget, f"__{prop}")
        return widget[prop]


class PseudoWidget:
    display_name = 'Widget'
    group = Groups.widget
    icon = "play"
    impl = None
    # special handlers (intercepts) for attributes that need additional processing
    # to interface with the studio easily
    _intercepts = {
        "image": _ImageIntercept,
        "selectimage": _ImageIntercept,
        "tristateimage": _ImageIntercept,
        "id": _IdIntercept,
        "textvariable": _VariableIntercept,
        "variable": _VariableIntercept,
        "listvariable": _VariableIntercept
    }

    def setup_widget(self):
        self.level = 0
        self.layout = None
        self.recent_layout_info = None
        self._properties = get_properties(self)
        self.set_name(self.id)
        self.node = None
        self.__on_context = None
        self.last_menu_position = (0, 0)
        MenuUtils.bind_context(self, self.__handle_context_menu, add='+')

    def set_name(self, name):
        pass

    def get_image_path(self):
        if hasattr(self, "image_path"):
            return self.image_path
        return self['image']

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
        intercept = self._intercepts.get(prop)
        if intercept:
            return intercept.get(self, prop)
        return self[prop]

    def configure(self, options=None, **kw):
        for opt in list(kw.keys()):
            intercept = self._intercepts.get(opt)
            if intercept:
                intercept.set(self, kw[opt], opt)
                kw.pop(opt)
        return super().config(**kw)

    def bind_all(self, sequence, func=None, add=None):
        # we should be able to bind studio events
        # for complex hierarchies in custom widgets
        # this also overrides the default bind_all behaviour which
        # may cause problems for the studio if an external custom widget uses it
        def _deep_bind(widget):
            widget.bind(sequence, func, add)
            for child in widget.winfo_children():
                _deep_bind(child)

        _deep_bind(self)

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

    def winfo_parent(self):
        return str(self.layout)

    def on_context_menu(self, callback, *args, **kwargs):
        self.__on_context = lambda e: callback(e, *args, **kwargs)

    def __handle_context_menu(self, event):
        self.last_menu_position = event.x_root, event.y_root
        if self.__on_context:
            return self.__on_context(event)

    def copy_config_to(self, widget):
        widget.configure(**self.get_altered_options())

    def get_altered_options(self):
        # second last item denotes the default value
        try:
            defaults = self.configure()
            defaults = {x: defaults[x][-2] for x in defaults}
        except TypeError:
            logging.error("options failed for" + str(self.id))
            return {}
        options = self.properties
        # Get options whose values are different from their default values
        return {opt: self.get_prop(opt) for opt in options if str(defaults.get(opt)) != str(self.get_prop(opt))}


class Container(PseudoWidget):
    LAYOUTS = layouts.layouts

    def setup_widget(self):
        self.parent = self.designer = self._get_designer()
        self._level = 0
        self._children = []
        self.temporal_children = []
        self._highlighter = WidgetHighlighter(self.master)
        if len(self.LAYOUTS) == 0:
            raise ValueError("No layouts have been defined")
        self.layout_strategy = layouts.PlaceLayoutStrategy(self)
        self.layout_var = tkinter.StringVar()
        self.layout_var.set(self.layout_strategy.name)
        super().setup_widget()

    def _get_designer(self):
        return self.master

    def show_highlight(self, *_):
        self._highlighter.highlight(self)

    def clear_highlight(self):
        self._highlighter.clear()
        self._temporal_children = []
        self.layout_strategy.clear_indicators()

    def lift(self, above_this):
        super().lift(above_this)
        for child in self._children:
            child.lift(self)

    def react(self, x, y):
        self.designer.set_active_container(self)
        self.react_to_pos(x, y)
        self.show_highlight()

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

    def get_layout_by_name(self, name):
        layout = list(
            filter(
                lambda l: l.name == name or l.name == layouts.aliases.get(name),
                self.LAYOUTS
            )
        )

        if len(layout) == 1:
            return layout[0]
        if len(layout) == 0:
            raise ValueError(f"No layout with name {name} found!")
        else:
            raise ValueError(f"Multiple implementations of layout {name} found")

    def _switch_layout(self, layout_class):
        if isinstance(layout_class, str):
            layout_class = self.get_layout_by_name(layout_class)
        if layout_class == self.layout_strategy.__class__:
            return
        former = self.layout_strategy
        self.layout_strategy = layout_class(self)
        self.layout_var.set(self.layout_strategy.name)
        self.layout_strategy.initialize(former)

    def configure(self, **kwargs):
        if 'layout' in kwargs:
            self._switch_layout(kwargs['layout'])
            kwargs.pop('layout')
        return super().configure(**kwargs)

    def _set_layout(self, layout):
        self.designer.studio.style_pane.apply_style("layout", layout, self)

    def _get_layouts_as_menu(self):
        layout_templates = [
            ("radiobutton", i.name, get_icon_image(i.icon, 14, 14),
             functools.partial(self._set_layout, i),
             {"value": i.name, "variable": self.layout_var}
             ) for i in self.LAYOUTS
        ]
        return (("cascade", "Change layout", get_icon_image("grid", 14, 14), None, {"menu": (
            layout_templates
        )}),)

    def create_menu(self):
        return (
            ("separator",),
            *self._get_layouts_as_menu()
        )

    def parse_bounds(self, bounds):
        return {
            "x": bounds[0],
            "y": bounds[1],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }

    def position(self, widget, bounds):
        widget.place(in_=self, **self.parse_bounds(bounds), bordermode=tkinter.OUTSIDE)

    #  =========================================== Rerouting methods ==================================================

    def restore_widget(self, widget, restore_point):
        self.layout_strategy.restore_widget(widget, restore_point)

    def add_widget(self, widget, bounds=None, **kwargs):
        self.layout_strategy.add_widget(widget, bounds, **kwargs)

    def widget_released(self, widget):
        self.layout_strategy.widget_released(widget)

    def change_start(self, widget):
        self.layout_strategy.change_start(widget)

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
        return self.layout_strategy.definition_for(widget)

    def react_to_pos(self, x, y):
        # react to position
        self.layout_strategy.react_to_pos(x, y)

    def copy_layout(self, widget, from_):
        self.layout_strategy.copy_layout(widget, from_)

    def get_altered_options_for(self, widget):
        return self.layout_strategy.get_altered_options(widget)

    def get_all_info(self):
        return self.layout_strategy.get_all_info()

    def config_all_widgets(self, data):
        self.layout_strategy.config_all_widgets(data)


class TabContainer(Container):

    def setup_widget(self):
        super().setup_widget()
        self.layout_strategy = layouts.TabLayoutStrategy(self)

    def _get_layouts_as_menu(self):
        # Prevent changing of layout from tab layout
        return ()

    def create_menu(self):
        return super().create_menu() + (
            ("command", "Add tab", get_icon_image("add", 14, 14), self._add_tab, {}),
        )

    def _add_tab(self):
        from studio.lib import legacy
        self.add_new(legacy.Frame, 0, 0)

    @property
    def properties(self):
        prop = super().properties
        prop.pop("layout")
        return prop

    def tab(self, widget, **kw):
        if not kw:
            # Intercept the return value and change image to the image path
            config = super().tab(widget)
            config['image'] = getattr(widget, '_tab_image_path', config['image'])
            return config
        if 'image' in kw:
            # load image at path before passing the image value
            # only load if value actually available
            if kw['image']:
                widget._tab_image_path = kw['image']
                image = load_tk_image(kw['image'])
                widget._tab_image = image  # shield from garbage collection
                kw['image'] = image  # update value with actual image
        return super().tab(widget, **kw)

    def _switch_layout(self, layout_class):
        if layout_class != self.layout_strategy.__class__:
            raise RuntimeError(f"Attempted to alter layout of notebook from TabLayout to {layout_class}")


class PanedContainer(TabContainer):
    def setup_widget(self):
        super(TabContainer, self).setup_widget()
        self.layout_strategy = layouts.PanedLayoutStrategy(self)

    def create_menu(self):
        return super(TabContainer, self).create_menu() + (
            ("command", "Add pane", get_icon_image("add", 14, 14), self._add_pane, {}),
        )

    def _add_pane(self):
        # add a legacy frame as a child
        from studio.lib import legacy
        self.add_new(legacy.Frame, 0, 0)


class WidgetMeta(type):

    def __new__(mcs, name, bases, dct):
        if dct.pop("is_container", False):
            # automatically pick specialization
            if any(issubclass(t, (tkinter.PanedWindow, tkinter.ttk.PanedWindow)) for t in bases):
                base = PanedContainer
            elif any(issubclass(t, tkinter.ttk.Notebook) for t in bases):
                base = TabContainer
            else:
                base = Container
        else:
            base = PseudoWidget

        if dct.get("impl"):
            impl = dct["impl"]
        elif bases:
            impl = bases[0]
        else:
            raise RuntimeError(
                "Could not deduce base implementation for custom widget. "
                "Inherit from base implementation or set the 'impl' attribute "
                "to the base class"
            )

        attrs = dict(display_name=name, impl=impl, icon='play', group=Groups.custom)
        attrs.update(dct)
        obj_class = super().__new__(mcs, name, (base, *bases), attrs)
        return obj_class

    def __call__(cls, master, _id):
        obj = super(WidgetMeta, cls).__call__(master)
        setattr(obj, "id", _id)
        obj.setup_widget()
        return obj


def auto_find_load_custom(*modules):
    # locate and load all custom widgets in modules
    # module can be a module or a path to module file
    custom_widgets = []
    for module in modules:
        if isinstance(module, str):
            module = import_path(module)
        for attr in dir(module):
            if type(getattr(module, attr)) == WidgetMeta:
                custom_widgets.append(getattr(module, attr))
    return custom_widgets
