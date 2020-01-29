"""
Layout classes uses in the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from hoverset.ui.widgets import Frame

from studio.ui import geometry
from studio.ui.highlight import WidgetHighlighter


class BaseLayout(Frame):
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

    def __init__(self, master):
        super().__init__(master)
        self.parent = master
        self._children = []
        self._temporal_children = []
        self._restoration_data = {}  # Where we store information on removed widgets to allow restoration
        self._level = 0
        self._highlighter = WidgetHighlighter(self.parent)

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self._level = value
        # We need to change the levels of of the layout's children
        # Failure to do this results in nasty crashes since the layout may be passed to one of its child layouts
        # which will try to position the layout (its parent!) within its self. A recursion hell!
        for child in self._children:
            child.level = self.level + 1

    def highlight(self, *_):
        self._highlighter.highlight(self)

    def clear_highlight(self):
        self._highlighter.clear()
        self._temporal_children = []

    def bounds(self):
        return geometry.bounds(self)

    def add_widget(self, widget, bounds):
        widget.level = self.level + 1
        widget.layout = self

    def lift(self, *_):
        super().lift(*_)
        for child in self._children:
            child.lift(self)

    def widget_released(self, widget):
        pass

    def move_widget(self, widget, bounds):
        if widget in self._children:
            self.remove_widget(widget)
        if widget not in self._temporal_children:
            self._temporal_children.append(widget)
            widget.level = self.level + 1
            widget.layout = self
            # Lift widget above the last child of layout if any otherwise lift above the layout
            widget.lift((self._children[-1:] or [self])[0])
        self._move(widget, bounds)

    def _move(self, widget, bounds):
        bounds = geometry.relative_bounds(bounds, self)  # Make the bounds relative to the layout for proper positioning
        place_bounds = self.parse_bounds(bounds)
        widget.place(in_=self, **place_bounds)

    def resize_widget(self, widget, bounds):
        self._move(widget, bounds)

    def restore_widget(self, widget):
        pass

    def get_restore(self, widget):
        raise NotImplementedError("Layout should provide restoration data")

    def remove_widget(self, widget):
        if widget in self._children:
            self._children.remove(widget)
        if widget in self._temporal_children:
            self._temporal_children.remove(widget)

    def parse_bounds(self, bounds):
        return {
            "x": bounds[0],
            "y": bounds[1],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }

    def add_new(self, widget, x, y):
        self.parent.add(widget, x, y, layout=self)

    def apply(self, prop, value, widget):
        pass

    @classmethod
    def definition_for(cls, widget):
        definition = {**cls.DEFINITION}
        definition["width"]["value"] = widget.winfo_width()
        definition["height"]["value"] = widget.winfo_height()
        return definition


class FrameLayout(BaseLayout):
    DEFINITION = {
        **BaseLayout.DEFINITION,
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

    def __init__(self, master):
        super().__init__(master)

    def add_widget(self, widget, bounds):
        super().add_widget(widget, bounds)
        super().remove_widget(widget)
        self.move_widget(widget, bounds)
        self._children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        self._restoration_data[widget] = self.get_restore(widget)
        widget.place_forget()

    def restore_widget(self, widget, data=None):
        data = self._restoration_data[widget] if data is None else data
        self._children.append(widget)
        widget.layout = self
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


class LinearLayout(BaseLayout):
    DEFINITION = {
        **BaseLayout.DEFINITION,
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

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.HORIZONTAL
        self.temp_info = {}

    def add_widget(self, widget, bounds):
        super().remove_widget(widget)
        if widget in self._restoration_data:
            self.restore_widget(widget)
            return
        super().add_widget(widget, bounds)
        if self._orientation == self.HORIZONTAL:
            widget.pack(in_=self)
        elif self._orientation == self.VERTICAL:
            widget.pack(in_=self, side="left")
        self._children.append(widget)

    def redraw(self):
        for widget in self._children:
            widget.pack(**self._pack_info(widget))

    def resize_widget(self, widget, bounds):
        if not self.temp_info:
            self.temp_info = self._pack_info(widget)
        self._move(widget, bounds)

    def _pack_info(self, widget):
        try:
            return widget.pack_info()
        except Exception:
            return self.temp_info or {"in_": self}

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
        self._children.insert(restoration_data[1], widget)
        widget.level = self.level + 1
        widget.layout = self
        widget.pack(**restoration_data[0])
        self.redraw()

    def get_restore(self, widget):
        # Restoration is sensitive to the position of the widget in the packing order therefore store
        # the restoration data in the form of a tuple (pack_info, pack_index)
        return widget.pack_info(), self._children.index(widget)

    def set_orientation(self, orient):
        if orient == self.VERTICAL:
            self.clear_children()
            for child in self._children:
                child.pack(in_=self, side="left", fill="y")
        elif orient == self.HORIZONTAL:
            self.clear_children()
            for child in self._children:
                child.pack(in_=self, side="top", fill="x")
        else:
            raise ValueError("Value must be BaseLayout.HORIZONTAL or BaseLayout.VERTICAL")

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
            del definition["height"]
        return definition


class GenericLinearLayout(BaseLayout):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.HORIZONTAL
        self._children = []

    def get_last(self):
        if len(self._children):
            last = self._children[-1]
            last.update_idletasks()
            return last.winfo_y() - self.winfo_y() + last.winfo_height()
        else:
            return 0

    def get_offset(self, index):
        if index >= 0:
            last = self._children[index]
            last.update_idletasks()
            return last.winfo_y() - self.winfo_y() + last.winfo_height()
        else:
            return 0

    def add_widget(self, widget, bounds):
        super().add_widget(widget, bounds)
        width, height = geometry.dimensions(bounds)
        self.attach(widget, width, height)
        self._children.append(widget)

    def attach(self, widget, width, height):
        y = self.get_last()
        widget.place(in_=self, x=0, y=y, width=width, height=height, bordermode="outside")

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


class VerticalLinearLayout(LinearLayout):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.VERTICAL


class GridLayout(BaseLayout):

    def __init__(self, master):
        super().__init__(master)

    def add_new(self, widget, x, y):
        pass
