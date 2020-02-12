"""
Layout classes uses in the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from studio.ui import geometry
from studio.ui.highlight import WidgetHighlighter, EdgeIndicator

COMMON_PROPERTIES = {
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
}


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
        self.container.clear_highlight()

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

    def react_to_pos(self, x, y):
        pass


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
        **COMMON_PROPERTIES,
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

        if "width" in widget.keys():
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
    icon = "grid"
    EXPAND = 0x1
    CONTRACT = 0X2

    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,
        **COMMON_PROPERTIES,
        "sticky": {
            "display_name": "sticky",
            "type": "anchor",
            "multiple": True,
            "name": "sticky"
        },
        "row": {
            "display_name": "row",
            "type": "number",
            "name": "row"
        },
        "column": {
            "display_name": "column",
            "type": "number",
            "name": "column"
        },
        "columnspan": {
            "display_name": "column span",
            "type": "number",
            "name": "columnspan"
        },
        "rowspan": {
            "display_name": "row span",
            "type": "number",
            "name": "rowspan"
        },
    }

    def __init__(self, master):
        super().__init__(master)
        self._restoration_data = {}
        self._highlighter = WidgetHighlighter(self.container.parent)
        self._edge_indicator = EdgeIndicator(self.container.parent)
        self._temp = {}

    def get_restore(self, widget):
        pass

    def react_to(self, bounds):
        bounds = geometry.relative_bounds(bounds, self.container)
        col, row = self.container.grid_location(bounds[0], bounds[1])
        widget = self.container.grid_slaves(row, col)
        if len(widget):
            self._highlighter.highlight(widget[0])

    def restore_widget(self, widget):
        pass

    def _redraw_widget(self, widget):
        widget.grid(**self._grid_info(widget))

    def _redraw(self, row, column, row_shift, column_shift):
        for child in self.container.grid_slaves():
            info = child.grid_info()
            if info['column'] >= column:
                child.grid_configure(column=info["column"] + column_shift)
        for child in self.container.grid_slaves(None, column):
            info = child.grid_info()
            if info["row"] >= row:
                child.grid_configure(row=info["row"] + row_shift)

    def _adjust_rows(self, from_row=0):
        rows = self.container.grid_size()[1]
        for row in range(from_row, rows):
            if not len(self.container.grid_slaves(row)):
                for child in self.container.grid_slaves(row + 1):
                    info = child.grid_info()
                    child.grid_configure(row=info["row"] - 1)

    def _adjust_columns(self, from_col):
        cols = self.container.grid_size()[1]
        for col in range(from_col, cols):
            if not len(self.container.grid_slaves(None, col)):
                for child in self.container.grid_slaves(None, col + 1):
                    info = child.grid_info()
                    child.grid_configure(column=info["column"] - 1)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        info = widget.grid_info()
        self.clear_indicators()
        if not info:
            return
        row, col, row_span, col_span = info["row"], info["column"], info["rowspan"], info["columnspan"]
        widget.grid_forget()
        if not len(self.container.grid_slaves(row)):
            self._adjust_rows(from_row=row)
        if not len(self.container.grid_slaves(None, col)):
            self._adjust_columns(from_col=col)

    def _grid_info(self, widget):
        info = widget.grid_info()
        if info:
            return info
        else:
            info = self._temp.get(widget, {})
            info.update({"in_": self.container})
            return info

    def widget_released(self, widget):
        self._redraw_widget(widget)
        self._temp = None
        self.clear_indicators()

    def resize_widget(self, widget, bounds):
        if not self._temp:
            self._temp = self._grid_info(widget)
        self._move(widget, bounds)

    def _move(self, widget, bounds):
        super()._move(widget, bounds)
        self._location_analysis(bounds)

    def add_widget(self, widget, bounds):
        super().remove_widget(widget)
        super().add_widget(widget, bounds)
        row, col, row_shift, column_shift = self._location_analysis(bounds)
        self._redraw(max(0, row), max(0, col), row_shift, column_shift)
        widget.grid(in_=self.container, row=max(0, row), column=max(0, col))
        self.children.append(widget)
        self.clear_indicators()

    def _widget_at(self, row, column):
        return self.container.grid_slaves(column, row)

    def _location_analysis(self, bounds):
        self.clear_indicators()
        self._edge_indicator.update_idletasks()
        bounds = geometry.relative_bounds(bounds, self.container)
        x, y = bounds[0], bounds[1]
        col, row = self.container.grid_location(x, y)
        x, y = geometry.upscale_bounds(bounds, self.container)[:2]
        slaves = self.container.grid_slaves(max(0, row), max(0, col))
        if len(slaves) == 0:
            self.container.update_idletasks()
            bbox = self.container.grid_bbox(col, row)
            bounds = *bbox[:2], bbox[0] + bbox[2], bbox[1] + bbox[3]
            # Make bounds relative to designer
            bounds = geometry.upscale_bounds(bounds, self.container)
        else:
            bounds = geometry.bounds(slaves[0])
        y_offset, x_offset = 10, 10  # 0.15*(bounds[3] - bounds[1]), 0.15*(bounds[2] - bounds[0])
        # If the position is empty no need to alter the row or column
        resize = 1 if len(slaves) else 0
        if y - bounds[1] < y_offset:
            self._edge_indicator.top(bounds)
            return row, col, resize, 0
        elif bounds[3] - y < y_offset:
            self._edge_indicator.bottom(bounds)
            return row + resize, col, resize, 0
        elif x - bounds[0] < x_offset:
            self._edge_indicator.left(bounds)
            return row, col, 0, resize
        elif bounds[2] - x < x_offset:
            self._edge_indicator.right(bounds)
            return row, col + resize, 0, resize
        else:
            self._highlighter.highlight_bounds(bounds)
            return row, col, 0, 0

    def clear_indicators(self):
        self._highlighter.clear()
        self._edge_indicator.clear()

    def apply(self, prop, value, widget):
        if prop in ("width", "height"):
            widget.configure(**{prop: value})
        else:
            widget.grid_configure(**{prop: value})

    def react_to_pos(self, x, y):
        self._location_analysis((*geometry.resolve_position((x, y), self.container.parent), 0, 0))

    @classmethod
    def definition_for(cls, widget):
        definition = super().definition_for(widget)
        info = widget.grid_info()
        for prop in ("sticky", "padx", "pady", "ipady", "ipadx", "row", "column", "columnspan", "rowspan"):
            definition[prop]["value"] = info.get(prop)
        if "width" in widget.keys():
            definition["width"]["value"] = widget["width"]
        if "height" in widget.keys():
            definition["height"]["value"] = widget["height"]
        else:
            definition.pop('height')
        return definition


layouts = (
    FrameLayoutStrategy, LinearLayoutStrategy, GridLayoutStrategy
)
