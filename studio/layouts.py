"""
Layout classes uses in the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from hoverset.ui.icons import get_icon
from studio.ui import geometry


class BaseLayoutStrategy:
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    DEFINITION = {
        "width": {
            "display_name": "width",
            "type": "dimension",
            "units": "pixels",
            "name": "width"
        },
        "height": {
            "display_name": "height",
            "type": "dimension",
            "units": "pixels",
            "name": "height"
        },
    }
    name = "Layout"  # A default name just in case
    icon = "frame"

    def __init__(self, container):
        self.parent = container.parent
        self.container = container
        self._restoration_data = {}  # Where we store information on removed widgets to allow restoration

    @property
    def level(self):
        return self.container.level

    @property
    def children(self):
        return self.container._children

    @property
    def temporal_children(self):
        return self.container.temporal_children

    def bounds(self):
        return geometry.bounds(self.container)

    def add_widget(self, widget, bounds):
        widget.level = self.level + 1
        widget.layout = self.container

    def widget_released(self, widget):
        pass

    def move_widget(self, widget, bounds):
        if widget in self.children:
            self.remove_widget(widget)
        if widget not in self.temporal_children:
            self.temporal_children.append(widget)
            widget.level = self.level + 1
            widget.layout = self.container
            # Lift widget above the last child of layout if any otherwise lift above the layout
            widget.lift((self.children[-1:] or [self.container])[0])
        self._move(widget, bounds)

    def _move(self, widget, bounds):
        # Make the bounds relative to the layout for proper positioning
        bounds = geometry.relative_bounds(bounds, self.container)
        self.container.position(widget, bounds)

    def resize_widget(self, widget, bounds):
        self._move(widget, bounds)

    def restore_widget(self, widget):
        pass

    def get_restore(self, widget):
        raise NotImplementedError("Layout should provide restoration data")

    def remove_widget(self, widget):
        if widget in self.children:
            self.children.remove(widget)
        if widget in self.temporal_children:
            self.temporal_children.remove(widget)

    def add_new(self, widget, x, y):
        self.parent.add(widget, x, y, layout=self.container)

    def apply(self, prop, value, widget):
        pass

    @classmethod
    def definition_for(cls, widget):
        definition = {**cls.DEFINITION}
        definition["width"]["value"] = widget.winfo_width()
        definition["height"]["value"] = widget.winfo_height()
        return definition

    def initialize(self):
        for child in self.children:
            self.add_widget(child, geometry.bounds(child))


class FrameLayoutStrategy(BaseLayoutStrategy):
    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,
        "x": {
            "display_name": "x",
            "type": "dimension",
            "units": "pixels",
            "name": "x"
        },
        "y": {
            "display_name": "y",
            "type": "dimension",
            "units": "pixels",
            "name": "y"
        },
        "bordermode": {
            "display_name": "border mode",
            "type": "choice",
            "options": ("outside", "inside"),
            "name": "bordermode"
        }
    }
    name = "FrameLayout"
    icon = "frame"

    def add_widget(self, widget, bounds):
        super().add_widget(widget, bounds)
        super().remove_widget(widget)
        self.move_widget(widget, bounds)
        self.children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        self._restoration_data[widget] = self.get_restore(widget)
        widget.place_forget()

    def restore_widget(self, widget, data=None):
        data = self._restoration_data[widget] if data is None else data
        self.children.append(widget)
        widget.layout = self.container
        widget.level = self.level + 1
        widget.place(**data)

    def get_restore(self, widget):
        return widget.place_info()

    def apply(self, prop, value, widget):
        widget.place_configure(**{prop: value})

    @classmethod
    def definition_for(cls, widget):
        definition = super().definition_for(widget)
        bounds = geometry.relative_bounds(geometry.bounds(widget), widget.layout)
        definition["x"]["value"] = bounds[0]
        definition["y"]["value"] = bounds[1]
        return definition


class LinearLayoutStrategy(BaseLayoutStrategy):
    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,
        "ipadx": {
            "display_name": "internal padding x",
            "type": "dimension",
            "units": "pixels",
            "name": "ipadx"
        },
        "ipady": {
            "display_name": "internal padding y",
            "type": "dimension",
            "units": "pixels",
            "name": "ipady"
        },
        "padx": {
            "display_name": "padding x",
            "type": "dimension",
            "units": "pixels",
            "name": "padx"
        },
        "pady": {
            "display_name": "padding y",
            "type": "dimension",
            "units": "pixels",
            "name": "pady"
        },
        "anchor": {
            "display_name": "anchor",
            "type": "anchor",
            "multiple": False,
            "name": "anchor"
        },
        "expand": {
            "display_name": "expand",
            "type": "boolean",
            "name": "expand"
        },
        "fill": {
            "display_name": "fill",
            "type": "choice",
            "options": ("x", "y", "none", "both"),
            "name": "fill"
        },
        "side": {
            "display_name": "side",
            "type": "choice",
            "options": ("top", "bottom", "right", "left"),
            "name": "side"
        },
    }
    name = "LinearLayout"
    icon = "frame"

    def __init__(self, container):
        super().__init__(container)
        self._orientation = self.HORIZONTAL
        self.temp_info = {}

    def add_widget(self, widget, bounds):
        super().remove_widget(widget)
        if widget in self._restoration_data:
            self.restore_widget(widget)
            return
        super().add_widget(widget, bounds)
        if self._orientation == self.HORIZONTAL:
            widget.pack(in_=self.container)
        elif self._orientation == self.VERTICAL:
            widget.pack(in_=self.container, side="left")
        self.children.append(widget)

    def redraw(self):
        print("packing...")
        for widget in self.children:
            widget.pack(**self._pack_info(widget))

    def resize_widget(self, widget, bounds):
        if not self.temp_info:
            self.temp_info = self._pack_info(widget)
        self._move(widget, bounds)

    def _pack_info(self, widget):
        try:
            return widget.pack_info()
        except Exception:
            return self.temp_info or {"in_": self.container}

    def widget_released(self, widget):
        self.redraw()
        self.temp_info = None

    def remove_widget(self, widget):
        self._restoration_data[widget] = self.get_restore(widget)
        super().remove_widget(widget)
        widget.pack_forget()

    def restore_widget(self, widget, data=None):
        # We need to be able to return a removed widget back to its initial position once removed
        restoration_data = self._restoration_data.get(widget) if data is None else data
        self.children.insert(restoration_data[1], widget)
        widget.level = self.level + 1
        widget.layout = self.container
        widget.pack(**restoration_data[0])
        self.redraw()

    def get_restore(self, widget):
        # Restoration is sensitive to the position of the widget in the packing order therefore store
        # the restoration data in the form of a tuple (pack_info, pack_index)
        return widget.pack_info(), self.children.index(widget)

    def set_orientation(self, orient):
        if orient == self.VERTICAL:
            self.clear_children()
            for child in self.children:
                child.pack(in_=self.container, side="left", fill="y")
        elif orient == self.HORIZONTAL:
            self.clear_children()
            for child in self.children:
                child.pack(in_=self.container, side="top", fill="x")
        else:
            raise ValueError("Value must be BaseLayoutStrategy.HORIZONTAL or BaseLayoutStrategy.VERTICAL")

    def clear_children(self):
        for child in self.children:
            child.pack_forget()

    def apply(self, prop, value, widget):
        if prop in ("width", "height"):
            widget.configure(**{prop: value})
        else:
            widget.pack_configure(**{prop: value})

    @classmethod
    def definition_for(cls, widget):
        definition = super().definition_for(widget)
        info = widget.pack_info()
        for prop in ("anchor", "padx", "pady", "ipady", "ipadx", "expand", "fill"):
            definition[prop]["value"] = info.get(prop)

        definition["width"]["value"] = widget["width"]
        if "height" in widget.keys():
            definition["height"]["value"] = widget["height"]
        else:
            definition.pop('height')
        return definition


class GenericLinearLayoutStrategy(BaseLayoutStrategy):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.HORIZONTAL
        self._children = []

    def get_restore(self, widget):
        pass

    def get_last(self):
        if len(self._children):
            last = self._children[-1]
            last.update_idletasks()
            return last.winfo_y() - self.container.winfo_y() + last.winfo_height()
        else:
            return 0

    def get_offset(self, index):
        if index >= 0:
            last = self._children[index]
            last.update_idletasks()
            return last.winfo_y() - self.container.winfo_y() + last.winfo_height()
        else:
            return 0

    def add_widget(self, widget, bounds):
        super().add_widget(widget, bounds)
        width, height = geometry.dimensions(bounds)
        self.attach(widget, width, height)
        self.children.append(widget)

    def attach(self, widget, width, height):
        y = self.get_last()
        widget.place(in_=self.container, x=0, y=y, width=width, height=height, bordermode="outside")

    def redraw(self, widget):
        from_ = self._children.index(widget)
        temp = self._children[from_:]
        self._children = self._children[:from_]
        dimensions = {}
        for child in temp:
            dimensions[child] = [child.winfo_width(), child.winfo_height()]
            child.place_forget()
        for child in temp:
            self.attach(child, *dimensions[child])
            self._children.append(child)

    def resize_widget(self, widget, bounds):
        super().resize_widget(widget, bounds)
        widget.update_idletasks()
        self.redraw(widget)

    def remove_widget(self, widget):
        from_ = self._children.index(widget)
        dimensions = {}
        for child in self._children[from_:]:
            dimensions[child] = [child.winfo_width(), child.winfo_height()]
            child.place_forget()
        temp = self._children[from_ + 1:]
        self._children = self._children[:from_]
        for child in temp:
            self.attach(child, *dimensions[child])
            self._children.append(child)

    def clear_children(self):
        for child in self.children:
            child.place_forget()


class VerticalLinearLayout(LinearLayoutStrategy):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.VERTICAL


class GridLayoutStrategy(BaseLayoutStrategy):
    name = 'GridLayout'
    icon = get_icon("grid")

    def __init__(self, master):
        super().__init__(master)

    def add_new(self, widget, x, y):
        pass

    def get_restore(self, widget):
        pass


layouts = (
    FrameLayoutStrategy, LinearLayoutStrategy
)
