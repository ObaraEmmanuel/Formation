"""
Layout classes uses in the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from collections import defaultdict

from studio.ui import geometry
from studio.ui.highlight import WidgetHighlighter, EdgeIndicator

COMMON_DEFINITION = {
    "ipadx": {
        "display_name": "internal padding x",
        "type": "dimension",
        "units": "pixels",
        "name": "ipadx",
    },
    "ipady": {
        "display_name": "internal padding y",
        "type": "dimension",
        "units": "pixels",
        "name": "ipady",
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
            "name": "width",
            "default": None,
        },
        "height": {
            "display_name": "height",
            "type": "dimension",
            "units": "pixels",
            "name": "height",
            "default": None
        },
    }
    name = "base"  # A default name just in case
    icon = "frame"
    manager = "place"  # Default layout manager in use
    realtime_support = False  # dictates whether strategy supports realtime updates to its values, most do not

    def __init__(self, container):
        self.parent = container.parent
        self.container = container

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

    def add_widget(self, widget, bounds=None, **kwargs):
        widget.level = self.level + 1
        widget.layout = self.container
        try:
            widget.lift(self.container)
        except Exception:
            pass
        self.container.clear_highlight()

    def widget_released(self, widget):
        pass

    def change_start(self, widget):
        widget.recent_layout_info = self.get_restore(widget)

    def move_widget(self, widget, bounds):
        if widget in self.children:
            self.remove_widget(widget)
        if widget not in self.temporal_children:
            self.temporal_children.append(widget)
            widget.level = self.level + 1
            widget.layout = self.container
            # Lift widget above the last child of layout if any otherwise lift above the layout
            try:
                widget.lift((self.children[-1:] or [self.container])[0])
            except Exception:
                pass
        self._move(widget, bounds)

    def _move(self, widget, bounds):
        # Make the bounds relative to the layout for proper positioning
        bounds = geometry.relative_bounds(bounds, self.container)
        self.container.position(widget, bounds)

    def resize_widget(self, widget, bounds):
        self._move(widget, bounds)

    def restore_widget(self, widget, data=None):
        raise NotImplementedError("Layout should provide restoration method")

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

    def info(self, widget):  # noqa
        return {}

    def get_all_info(self):
        return {widget: self.info(widget) for widget in self.children}

    def config_all_widgets(self, data):
        for child in self.children:
            if child in data:
                self.config_widget(child, data[child])

    def config_widget(self, widget, config):
        raise NotImplementedError("Layout should provide configuration method")

    def get_def(self, widget):
        # May be overridden to return dynamic definitions based on the widget
        # Always use a copy to avoid messing with definition
        return dict(self.DEFINITION)

    def definition_for(self, widget):
        info = self.info(widget)
        # Ensure we use the dynamic definitions
        definition = self.get_def(widget)
        for key in definition:
            # will throw a key error if a definition value is not found in info
            definition[key]["value"] = info[key]
        return definition

    def initialize(self, former_strategy=None):
        # create a list of children and their bounds which won't change during iteration
        bounding_map = [(child, geometry.bounds(child)) for child in self.children]
        if former_strategy:
            former_strategy.clear_all()
        for child, bounds in bounding_map:
            self.add_widget(child, bounds)

    def react_to_pos(self, x, y):
        pass

    def copy_layout(self, widget, from_):
        pass

    def clear_indicators(self):
        pass

    def get_altered_options(self, widget):
        options = defaultdict(dict)
        definitions = self.definition_for(widget)
        for definition in definitions.values():
            if definition.get("value") != definition.get("default", 0):
                options[definition["name"]] = definition["value"]
        return options

    def clear_all(self):
        # Unmap all children from a container
        # Layouts must provide an implementation as it may differ from layout to layout
        # This method is important in removing all child widgets before we switch layouts
        # (especially from grid to pack and vice versa) which may raise errors when used simultaneously
        raise NotImplementedError("Clear all procedure required")


class PlaceLayoutStrategy(BaseLayoutStrategy):
    # TODO Add support for anchor
    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,
        "x": {
            "display_name": "x",
            "type": "dimension",
            "units": "pixels",
            "name": "x",
            "default": None
        },
        "y": {
            "display_name": "y",
            "type": "dimension",
            "units": "pixels",
            "name": "y",
            "default": None
        },
        "bordermode": {
            "display_name": "border mode",
            "type": "choice",
            "options": ("outside", "inside", "ignore"),
            "name": "bordermode",
            "default": "inside",
        }
    }
    name = "place"
    icon = "frame"
    manager = "place"
    realtime_support = True

    def clear_all(self):
        for child in self.children:
            child.place_forget()

    def add_widget(self, widget, bounds=None, **kwargs):
        super().add_widget(widget, bounds)
        super().remove_widget(widget)
        if bounds:
            self.move_widget(widget, bounds)
        kwargs['in'] = self.container
        widget.place_configure(**kwargs)
        self.children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        widget.place_forget()

    def config_widget(self, widget, config):
        widget.place_configure(**config)

    def restore_widget(self, widget, data=None):
        data = widget.recent_layout_info if data is None else data
        self.children.append(widget)
        widget.layout = self.container
        widget.level = self.level + 1
        widget.place_configure(**data.get("info", {}))

    def get_restore(self, widget):
        return {
            "info": widget.place_info(),
            "container": self.container,
        }

    def apply(self, prop, value, widget):
        widget.place_configure(**{prop: value})

    def info(self, widget):
        info = widget.place_info() or {}
        return info

    def copy_layout(self, widget, from_):
        info = from_.place_info()
        info["in_"] = self.container
        widget.place(**info)
        self.children.append(widget)
        super().add_widget(widget, (0, 0, 0, 0))


class PackLayoutStrategy(BaseLayoutStrategy):
    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,
        **COMMON_DEFINITION,
        "anchor": {
            "display_name": "anchor",
            "type": "anchor",
            "multiple": False,
            "name": "anchor",
            "default": "center"
        },
        "expand": {
            "display_name": "expand",
            "type": "boolean",
            "name": "expand",
            "default": False
        },
        "fill": {
            "display_name": "fill",
            "type": "choice",
            "options": ("x", "y", "none", "both"),
            "name": "fill",
            "default": "none"
        },
        "side": {
            "display_name": "side",
            "type": "choice",
            "options": ("top", "bottom", "right", "left"),
            "name": "side",
            "default": "top"
        },
    }
    name = "pack"
    icon = "frame"
    manager = "pack"

    def __init__(self, container):
        super().__init__(container)
        self._orientation = self.HORIZONTAL
        self.temp_info = {}
        # Store for info on temporarily removed widgets to allow restoration
        self._restoration_data = {}

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        if self._orientation == self.HORIZONTAL:
            widget.pack(in_=self.container)
        elif self._orientation == self.VERTICAL:
            widget.pack(in_=self.container, side="left")
        self.config_widget(widget, kwargs)
        self.children.append(widget)

    def redraw(self):
        for widget in self.children:
            widget.pack(**self._pack_info(widget))

    def _redraw(self, start_index=0):
        affected = self.children[start_index:]
        cache = {}
        for child in affected:
            cache[child] = self._pack_info(child)
            child.pack_forget()
        for child in affected:
            child.pack(**cache.get(child, {}))

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
        restoration_data = widget.recent_layout_info if data is None else data
        self.children.insert(restoration_data.get("index", -1), widget)
        widget.level = self.level + 1
        widget.layout = self.container
        widget.pack(in_=self.container)
        self.config_widget(widget, restoration_data.get("info", {}))
        self._redraw()

    def get_restore(self, widget):
        return {
            "info": widget.pack_info(),
            "container": self.container,
            "index": self.children.index(widget)
        }

    def set_orientation(self, orient):
        if orient == self.VERTICAL:
            self.clear_all()
            for child in self.children:
                child.pack(in_=self.container, side="left", fill="y")
        elif orient == self.HORIZONTAL:
            self.clear_all()
            for child in self.children:
                child.pack(in_=self.container, side="top", fill="x")
        else:
            raise ValueError("Value must be BaseLayoutStrategy.HORIZONTAL or BaseLayoutStrategy.VERTICAL")

    def apply(self, prop, value, widget):
        if prop in ("width", "height"):
            widget.configure(**{prop: value})
        else:
            widget.pack_configure(**{prop: value})

    def config_widget(self, widget, config):
        for prop in ("width", "height"):
            if prop in config:
                widget.configure(**{prop: config[prop]})
                config.pop(prop)

        widget.pack_configure(**config)

    def get_def(self, widget):
        # Use copy since we are going to modify definition
        definition = dict(self.DEFINITION)
        keys = widget.keys()
        for prop in ("width", "height"):
            if prop not in keys:
                definition.pop(prop)
        return definition

    def info(self, widget):
        info = widget.pack_info() or {}
        keys = widget.keys()
        for prop in ("width", "height"):
            if prop in keys:
                info.update({prop: widget[prop]})
        return info

    def copy_layout(self, widget, from_):
        info = from_.pack_info()
        info["in_"] = self.container
        widget.pack(**info)
        self.children.append(widget)
        super().add_widget(widget, (0, 0, 0, 0))

    def clear_all(self):
        for child in self.children:
            child.pack_forget()


class GenericLinearLayoutStrategy(BaseLayoutStrategy):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.HORIZONTAL
        self._children = []

    def config_widget(self, widget, config):
        pass

    def clear_all(self):
        pass

    def get_restore(self, widget):
        pass

    def restore_widget(self, widget, data=None):
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

    def add_widget(self, widget, bounds=None, **kwargs):
        super().add_widget(widget, bounds, **kwargs)
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


class VerticalLinearLayout(PackLayoutStrategy):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.VERTICAL


class GridLayoutStrategy(BaseLayoutStrategy):
    name = "grid"
    icon = "grid"
    manager = "grid"
    EXPAND = 0x1
    CONTRACT = 0X2

    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,
        **COMMON_DEFINITION,
        "sticky": {
            "display_name": "sticky",
            "type": "anchor",
            "multiple": True,
            "name": "sticky",
            "default": ''
        },
        "row": {
            "display_name": "row",
            "type": "number",
            "name": "row",
            "default": None,
        },
        "column": {
            "display_name": "column",
            "type": "number",
            "name": "column",
            "default": None,
        },
        "columnspan": {
            "display_name": "column span",
            "type": "number",
            "name": "columnspan",
            "default": 1
        },
        "rowspan": {
            "display_name": "row span",
            "type": "number",
            "name": "rowspan",
            "default": 1
        },
    }

    GRID_CONFIG_DEFINITION = {
        "minsize": {
            "display_name": "minsize",
            "type": "dimension",
            "units": "pixels",
            "name": "minsize",
            "default": 0,
        },
        "pad": {
            "display_name": "pad",
            "type": "dimension",
            "units": "pixels",
            "name": "pad",
            "default": 0
        },
        "weight": {
            "display_name": "weight",
            "type": "number",
            "name": "weight",
            "default": 0
        },
        "uniform": {
            "display_name": "uniform",
            "type": "text",
            "name": "uniform",
            "default": None
        }
    }

    COLUMN_DEF = {
        "display_name": "column",
        "type": "number",
        "name": "column",
        "readonly": True
    }

    ROW_DEF = {
        "display_name": "row",
        "type": "number",
        "name": "row",
        "readonly": True
    }

    def __init__(self, master):
        super().__init__(master)
        self._highlighter = WidgetHighlighter(self.container.parent)
        self._edge_indicator = EdgeIndicator(self.container.parent)
        self._temp = {}

    def get_restore(self, widget):
        return {
            "info": widget.grid_info(),
            "container": self.container,
        }

    def restore_widget(self, widget, data=None):
        data = widget.recent_layout_info if data is None else data
        self.children.append(widget)
        widget.level = self.level + 1
        widget.layout = self.container
        widget.grid(in_=self.container)
        self.config_widget(widget, data.get("info", {}))

    def react_to(self, bounds):
        bounds = geometry.relative_bounds(bounds, self.container)
        col, row = self.container.grid_location(bounds[0], bounds[1])
        widget = self.container.grid_slaves(row, col)
        if len(widget):
            self._highlighter.highlight(widget[0])

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
        widget.grid_forget()

    def _grid_info(self, widget):
        info = widget.grid_info()
        if info:
            return info
        else:
            info = self._temp.get(widget, {})
            info.update({"in_": self.container})
            return info

    def config_widget(self, widget, config):
        for prop in ("width", "height"):
            if prop in config:
                widget.configure(**{prop: config[prop]})
                config.pop(prop)
        widget.grid_configure(**config)

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

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        if bounds is not None:
            row, col, row_shift, column_shift = self._location_analysis(bounds)
            self._redraw(max(0, row), max(0, col), row_shift, column_shift)
            kwargs.update({'in_': self.container, 'row': max(0, row), 'column': max(0, col)})
            widget.grid(**kwargs)
        else:
            widget.grid(in_=self.container)
            self.config_widget(widget, kwargs)
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

    def info(self, widget):
        info = widget.grid_info() or {}
        keys = widget.keys()
        for prop in ("width", "height"):
            if prop in keys:
                info.update({prop: widget[prop]})
        return info

    def get_def(self, widget):
        # Use copy since we are going to modify definition
        definition = dict(self.DEFINITION)
        keys = widget.keys()
        for prop in ("width", "height"):
            if prop not in keys:
                definition.pop(prop)
        return definition

    def get_row_def(self, widget=None, row=None):
        definition = dict(self.GRID_CONFIG_DEFINITION)
        row_info = self.container.rowconfigure(widget.grid_info()["row"] if row is None else row)
        for key in definition:
            definition[key]["value"] = row_info[key]
        return definition

    def get_column_def(self, widget=None, column=None):
        definition = dict(self.GRID_CONFIG_DEFINITION)
        column_info = self.container.columnconfigure(widget.grid_info()["column"] if column is None else column)
        for key in definition:
            definition[key]["value"] = column_info[key]
        return definition

    def copy_layout(self, widget, from_):
        info = from_.grid_info()
        info["in_"] = self.container
        widget.grid(**info)
        self.children.append(widget)
        super().add_widget(widget, (0, 0, 0, 0))

    def clear_all(self):
        # remove the children but still maintain them in the children list
        for child in self.children:
            child.grid_forget()


class TabLayoutStrategy(BaseLayoutStrategy):
    # TODO Extend support for side specific padding
    name = "TabLayout"
    icon = "notebook"
    manager = "tab"
    DEFINITION = {
        "text": {
            "display_name": "tab text",
            "type": "text",
            "name": "text",
            "default": None
        },
        "image": {
            "display_name": "tab image",
            "type": "image",
            "name": "image",
            "default": ''
        },
        "underline": {
            "display_name": "tab underline",
            "type": "number",
            "name": "underline",
            "default": -1
        },
        "compound": {
            "display_name": "compound",
            "type": "choice",
            "options": ("top", "bottom", "left", "right", 'none'),
            "name": "compound",
            "default": "none"
        },
        "sticky": {
            "display_name": "sticky",
            "type": "anchor",
            "multiple": True,
            "name": "sticky",
            "default": "nsew",
        },
        "padding": {
            "display_name": "padding",
            "type": "dimension",
            "units": "pixels",
            "name": "padding",
            "default": 0,
        },
        "state": {
            "display_name": "state",
            "name": "state",
            "type": "choice",
            "options": ("normal", "disabled", "hidden"),
            "default": 'normal'
        }
    }

    def __init__(self, master):
        super().__init__(master)
        self._current_tab = None
        self.container.bind("<<NotebookTabChanged>>", self._tab_switched)

    def config_widget(self, widget, config):
        self.container.tab(widget, **config)

    def restore_widget(self, widget, data=None):
        restoration_data = widget.recent_layout_info if data is None else data
        self.children.insert(restoration_data.get("index", -1), widget)
        widget.level = self.level + 1
        widget.layout = self.container
        self.container.add(widget)
        self.container.tab(widget, **restoration_data.get("info", {}))
        self._redraw(restoration_data.get("index", -1))

    def get_restore(self, widget):
        return {
            "info": self.info(widget),
            "container": self.container,
            "index": self.children.index(widget),
        }

    def _redraw(self, start_index=0):
        affected = self.children[start_index:]
        cache = {}
        for child in affected:
            cache[child] = self.info(child)
            self.container.forget(child)
        for child in affected:
            self.container.add(child)
            self.container.tab(child, **cache.get(child, {}))

    def resize_widget(self, widget, bounds):
        pass

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        self.container.add(widget, text=widget.id)
        self.container.tab(widget, **kwargs)
        self.children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        self.container.forget(widget)

    def info(self, widget):
        info = self.container.tab(widget) or {}
        if "padding" in info:
            # use the first padding value until we can support full padding
            info["padding"] = info["padding"][0]
        info["compound"] = info.get("compound", "") or "none"
        return info

    def apply(self, prop, value, widget):
        self.container.tab(widget, **{prop: value})

    def _tab_switched(self, *_):
        if self._current_tab:
            # Take its level down by one
            self._current_tab.level = self.level + 1
        self._current_tab = self.container.nametowidget(self.container.select())
        # Take its level one place above other tabs
        self._current_tab.level = self.level + 2

    def copy_layout(self, widget, from_):
        info = from_.layout.tab(from_)
        self.add_widget(widget, (0, 0, 0, 0), **info)

    def clear_all(self):
        # No implementation needed as the tab layout strategy never needs to change
        pass


class PanedLayoutStrategy(BaseLayoutStrategy):
    name = "PanedLayout"
    icon = "flip_horizontal"
    manager = "pane"
    DEFINITION = {
        **BaseLayoutStrategy.DEFINITION,  # width and height definition
        "padx": COMMON_DEFINITION.get("padx"),
        "pady": COMMON_DEFINITION.get("pady"),
        "sticky": {
            "display_name": "sticky",
            "type": "anchor",
            "multiple": True,
            "name": "sticky",
            "default": "nsew",
        },
        "hide": {
            "display_name": "hide",
            "type": "boolean",
            "name": "hide",
            "default": False
        },
        "stretch": {
            "display_name": "stretch",
            "type": "choice",
            "options": ["always", "first", "last", "middle", "never"],
            "default": "last",
            "name": "stretch"
        },
        "minsize": {
            "display_name": "minsize",
            "type": "dimension",
            "units": "pixels",
            "default": 0,
            "name": "minsize",
        }
    }

    def get_restore(self, widget):
        return {
            "info": self.info(widget),
            "index": self.children.index(widget),
            "container": self.container
        }

    def config_widget(self, widget, config):
        self._config(widget, **config)

    def restore_widget(self, widget, data=None):
        restoration_data = widget.recent_layout_info if data is None else data
        self.children.insert(restoration_data.get("index", -1), widget)
        widget.level = self.level + 1
        widget.layout = self.container
        self.container.add(widget)
        self._config(widget, **restoration_data.get("info", {}))
        self._redraw(restoration_data.get("index", -1))

    def _redraw(self, start_index=0):
        affected = self.children[start_index:]
        cache = {}
        for child in affected:
            cache[child] = self.info(child)
            self.container.forget(child)
        for child in affected:
            self.container.add(child)
            self._config(child, **cache.get(child, {}))

    def clear_all(self):
        pass

    def resize_widget(self, widget, bounds):
        pass

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        self.container.add(widget)
        self._config(widget, **kwargs)
        self.children.append(widget)

    def _config(self, widget, **kwargs):
        if not kwargs:
            return self.container.paneconfig(widget)
        self.container.paneconfig(widget, **kwargs)

    def get_def(self, widget):
        definition = dict(self.DEFINITION)
        # Give a hint on what the minsize attribute will affect
        # if panedwindow is in horizontal orient minsize affects min-width of
        # the children otherwise it affects height
        side = "width" if self.container["orient"] == "horizontal" else "height"
        definition["minsize"]["display_name"] = f"minsize ({side})"
        return definition

    def info(self, widget):
        info = self._config(widget) or {}
        # we only need to use the last value for every value returned by config
        return {k: info[k][-1] for k in info}

    def apply(self, prop, value, widget):
        self.container.paneconfig(widget, **{prop: value})

    def remove_widget(self, widget):
        super().remove_widget(widget)
        self.container.forget(widget)

    def copy_layout(self, widget, from_):
        info = from_.layout.paneconfig(from_)
        info = {i: info[i][-1] for i in info}  # The value is usually the last item in the tuple
        self.add_widget(widget, (0, 0, 0, 0), **info)


class NPanedLayoutStrategy(PanedLayoutStrategy):
    """
    Native paned window layout. Paned window behaviour is different in ttk
    """
    DEFINITION = {
        "weight": {
            "name": "weight",
            "display_name": "weight",
            "type": "float",
            "default": 0,
        }
    }
    name = "NativePanedLayout"

    def apply(self, prop, value, widget):
        self.container.pane(widget, **{prop: value})

    def _config(self, widget, **kwargs):
        if not kwargs:
            return self.container.pane(widget)
        self.container.pane(widget, **kwargs)

    def copy_layout(self, widget, from_):
        info = from_.layout.pane(from_)
        self.add_widget(widget, (0, 0, 0, 0), **info)

    def get_def(self, widget):
        # We need to override the hinting behaviour inherited since there's no
        # orient and minsize options
        return dict(self.DEFINITION)

    def info(self, widget):
        return self._config(widget) or {}


# Do not include tab layout since it requires special widgets like notebooks
# to function and this list is displayed in the layout options menu for containers
layouts = (
    PlaceLayoutStrategy, PackLayoutStrategy, GridLayoutStrategy
)

# enable backward compatibility for designs using old layout names
aliases = {
    "GridLayout": "grid",
    "LinearLayout": "pack",
    "FrameLayout": "place"
}
