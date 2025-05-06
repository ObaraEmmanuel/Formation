"""
Layout classes uses in the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from collections import defaultdict
from copy import deepcopy
import tkinter as tk

from studio.ui import geometry
from studio.ui.highlight import WidgetHighlighter, EdgeIndicator

COMMON_DEFINITION = {
    "ipadx": {
        "display_name": "internal padding x",
        "type": "dimension",
        "name": "ipadx",
    },
    "ipady": {
        "display_name": "internal padding y",
        "type": "dimension",
        "name": "ipady",
    },
    "padx": {
        "display_name": "padding x",
        "type": "dimension",
        "name": "padx"
    },
    "pady": {
        "display_name": "padding y",
        "type": "dimension",
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
            "name": "width",
            "default": None,
        },
        "height": {
            "display_name": "height",
            "type": "dimension",
            "name": "height",
            "default": None
        },
    }
    name = "base"  # A default name just in case
    icon = "frame"
    manager = "place"  # Default layout manager in use
    realtime_support = False  # dictates whether strategy supports realtime updates to its values, most do not
    dimensions_in_px = False  # Whether to use pixel units for width and height
    allow_resize = False  # Whether to allow resizing of widgets
    stacking_support = True  # Whether to allow modification of stacking order

    def __init__(self, container):
        self.parent = container.parent
        self.container = container

    @property
    def level(self):
        return self.container.level

    @property
    def children(self):
        return self.container._children

    def bounds(self):
        return geometry.bounds(self.container)

    def add_widget(self, widget, bounds=None, **kwargs):
        widget.level = self.level + 1
        widget.layout = self.container
        self.container.clear_highlight()

    def _insert(self, widget, index=None):
        if index is None:
            self.children.append(widget)
        else:
            self.children.insert(index, widget)

        self._update_stacking()

        if widget.prev_stack_index is None:
            widget.prev_stack_index = len(self.children) - 1

    def _update_stacking(self):
        for index, widget in enumerate(self.children):
            if index > 0:
                widget.lift(self.children[index - 1])
            else:
                widget.lift(self.container.body)

    def widgets_reordered(self):
        pass

    def start_move(self, widget):
        widget.recent_layout_info = self.get_restore(widget)
        widget.lift()
        widget.lift_handle()

    def start_resize(self, widget):
        widget.recent_layout_info = self.get_restore(widget)

    def move_widget(self, widget, delta):
        bounds = geometry.relative_bounds(self.bounds_from_delta(widget, delta), self.container.body)
        self.container.position(widget, bounds)

    def end_move(self, widget):
        pass

    def on_move_exit(self):
        pass

    def bounds_from_delta(self, widget, delta):
        # Make the bounds relative to the layout for proper positioning
        x1, y1, x2, y2 = widget.get_bounds()
        dx, dy = delta
        return [x1 + dx, y1 + dy, x2 + dx, y2 + dy]

    def resize_widget(self, widget, direction, delta):
        raise NotImplementedError("Layout should provide resize method")

    def restore_widget(self, widget, data=None):
        raise NotImplementedError("Layout should provide restoration method")

    def get_restore(self, widget):
        raise NotImplementedError("Layout should provide restoration data")

    def remove_widget(self, widget):
        if widget in self.children:
            self.children.remove(widget)

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
        if self.dimensions_in_px:
            return deepcopy(self.DEFINITION)
        props = deepcopy(self.DEFINITION)
        overrides = getattr(widget, 'DEF_OVERRIDES', {})
        for key in ('width', 'height'):
            if key in props and key in overrides:
                props[key] = {**props[key], **overrides[key]}
        return props

    def definition_for(self, widget):
        info = self.info(widget)
        # Ensure we use the dynamic definitions
        definition = self.get_def(widget)
        to_pop = set()
        for key in definition:
            if key not in info:
                to_pop.add(key)
            else:
                definition[key]["value"] = info[key]
        for key in to_pop:
            definition.pop(key)
        return definition

    def initialize(self, former_strategy=None):
        # create a list of children and their bounds which won't change during iteration
        bounding_map = [(child, geometry.bounds(child)) for child in self.children]
        if former_strategy:
            former_strategy.clear_all()
        for child, bounds in bounding_map:
            self.add_widget(child, bounds)

    def react_to_pos(self, bounds):
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
            "negative": True,
            "name": "x",
            "default": None,
            "parse": int
        },
        "y": {
            "display_name": "y",
            "type": "dimension",
            "negative": True,
            "name": "y",
            "default": None,
            "parse": int
        },
        "bordermode": {
            "display_name": "border mode",
            "type": "choice",
            "options": ("outside", "inside", "ignore"),
            "name": "bordermode",
            "default": "inside",
        },
        "relx": {
            "display_name": "relative x",
            "type": "float",
            "name": "relx",
            "default": 0,
            "parse": float
        },
        "rely": {
            "display_name": "relative y",
            "type": "float",
            "name": "rely",
            "default": 0,
            "parse": float
        },
        "relwidth": {
            "display_name": "relative width",
            "type": "float",
            "name": "relwidth",
            "default": "",
            "parse": float
        },
        "relheight": {
            "display_name": "relative height",
            "type": "float",
            "name": "relheight",
            "default": "",
            "parse": float
        },
    }
    name = "place"
    icon = "place"
    manager = "place"
    realtime_support = True
    dimensions_in_px = True
    allow_resize = True

    def clear_all(self):
        for child in self.children:
            child.place_forget()

    def add_widget(self, widget, bounds=None, **kwargs):
        super().add_widget(widget, bounds)
        super().remove_widget(widget)
        if bounds:
            bounds = geometry.relative_bounds(bounds, self.container.body)
            self.container.position(widget, bounds)
        kwargs['in'] = self.container.body
        widget.place_configure(**kwargs)
        self._insert(widget, widget.prev_stack_index if widget.layout == self.container else None)

    def _info_with_delta(self, widget, direction, delta):
        info = self.info(widget)
        if "width" not in info:
            info["width"] = widget.winfo_width()
        if "height" not in info:
            info["height"] = widget.winfo_height()
        info.update(x=int(info["x"]), y=int(info["y"]), width=int(info["width"]), height=int(info["height"]))
        dx, dy = delta
        if direction == "n":
            info.update(y=info["y"] + dy, height=info["height"] - dy)
        elif direction == "s":
            info["height"] = info["height"] + dy
        elif direction == "e":
            info["width"] = info["width"] + dx
        elif direction == "w":
            info.update(x=info["x"] + dx, width=info["width"] - dx)
        elif direction == "nw":
            info.update(x=info["x"] + dx, y=info["y"] + dy, width=info["width"] - dx, height=info["height"] - dy)
        elif direction == "ne":
            info.update(y=info["y"] + dy, width=info["width"] + dx, height=info["height"] - dy)
        elif direction == "sw":
            info.update(x=info["x"] + dx, width=info["width"] - dx, height=info["height"] + dy)
        elif direction == "se":
            info.update(width=info["width"] + dx, height=info["height"] + dy)
        elif direction == "all":
            info.update(x=info["x"] + dx, y=info["y"] + dy)
        return info

    def resize_widget(self, widget, direction, delta):
        info = self._info_with_delta(widget, direction, delta)
        widget.place_configure(**info)

    def end_move(self, widget):
        super().end_move(widget)
        self._update_stacking()

    def move_widget(self, widget, delta):
        info = widget.place_info() or {}
        ref = info.get("in")

        if ref != self.container.body:
            bounds = geometry.relative_bounds(self.bounds_from_delta(widget, delta), self.container.body)
            self.container.position(widget, bounds)
            return

        info = self._info_with_delta(widget, "all", delta)
        widget.place_configure(**info)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        widget.place_forget()

    def config_widget(self, widget, config):
        widget.place_configure(**config)

    def restore_widget(self, widget, data=None):
        data = widget.recent_layout_info if data is None else data
        self._insert(widget, widget.prev_stack_index if widget.layout == self.container else None)

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
        for k in info:
            parse = self.DEFINITION.get(k, {}).get("parse")
            if not parse or info[k] == '':
                continue
            info[k] = parse(info[k])
        return info

    def copy_layout(self, widget, from_):
        info = from_.place_info()
        info["in_"] = self.container.body
        widget.place(**info)
        self._insert(widget)
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
    icon = "pack"
    manager = "pack"
    stacking_support = False

    def __init__(self, container):
        super().__init__(container)
        self._edge_indicator = EdgeIndicator(self.container.parent)
        self.temp_info = {}

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        if bounds or not self.children:
            self._pack_at_bounds(widget, bounds, **kwargs)
        else:
            widget.pack(in_=self.container.body)
            self.config_widget(widget, kwargs)
            self._insert(widget)
        self._edge_indicator.clear()

    def _pack_at_bounds(self, widget, bounds, **kwargs):
        index, side = self._location_analysis(bounds)
        kwargs.update({"side": side})
        widget.pack(in_=self.container.body)
        self.config_widget(widget, kwargs)
        orig_index = self.children.index(widget) if widget in self.children else -1
        if orig_index >= 0:
            self.children.remove(widget)
            if orig_index < index:
                index -= 1
        self._insert(widget, index)
        self.redraw(index)

    def redraw(self, start_index=0):
        affected = self.children[start_index:]
        cache = {}
        for child in affected:
            cache[child] = self._pack_info(child)
            child.pack_forget()
        for child in affected:
            child.pack(**cache.get(child, {}))

    def resize_widget(self, widget, direction, delta):
        pass

    def _pack_info(self, widget):
        try:
            return widget.pack_info()
        except Exception:
            return self.temp_info or {"in_": self.container.body}

    def remove_widget(self, widget):
        super().remove_widget(widget)
        widget.pack_forget()

    def move_widget(self, widget, delta):
        super().move_widget(widget, delta)
        self._location_analysis(self.bounds_from_delta(widget, delta))

    def react_to_pos(self, bounds):
        bounds = geometry.resolve_bounds(bounds, self.container.parent)
        self._location_analysis(bounds)

    def _location_analysis(self, bounds):
        if not self.children:
            return 0, "top"
        self.clear_indicators()
        bounds = geometry.relative_bounds(bounds, self.container.body)
        x, y = geometry.center(bounds)
        target = None
        for w in self.children:
            if w.winfo_manager() != "pack":
                continue
            bounds = geometry.relative_bounds(geometry.bounds(w), self.container.body)
            if geometry.is_pos_within(bounds, (x, y)):
                target = w
                break
            target = w
        if target is None:
            return len(self.children), "top"
        bounds = geometry.relative_bounds(geometry.bounds(target), self.container.body)
        cx, cy = geometry.center(bounds)
        side = target.pack_info().get("side", "top")
        index = self.children.index(target)
        chart = {
            # side: (index offset if in top/left-half, index offset if in bottom/right-half)
            "top": (index, index + 1),
            "bottom": (index + 1, index),
            "left": (index, index + 1),
            "right": (index + 1, index)
        }
        chart_index = 0
        bounds = geometry.upscale_bounds(bounds, self.container.body)
        if side == "top" or side == "bottom":
            bounds = geometry.expand(bounds, 10, 'ew')
            if y > cy:
                self._edge_indicator.bottom(bounds)
                chart_index = 1
            else:
                self._edge_indicator.top(bounds)
        if side == "right" or side == "left":
            bounds = geometry.expand(bounds, 10, 'ns')
            if x > cx:
                self._edge_indicator.right(bounds)
                chart_index = 1
            else:
                self._edge_indicator.left(bounds)

        return chart[side][chart_index], side

    def clear_indicators(self):
        self._edge_indicator.clear()

    def start_move(self, widget):
        super().start_move(widget)

    def end_move(self, widget):
        super().end_move(widget)
        self._pack_at_bounds(widget, widget.get_bounds(), **widget.recent_layout_info.get("info", {}))
        self._update_stacking()
        self.clear_indicators()

    def restore_widget(self, widget, data=None):
        # We need to be able to return a removed widget back to its initial position once removed
        restoration_data = widget.recent_layout_info if data is None else data
        self._insert(widget, restoration_data.get("index", -1))
        widget.level = self.level + 1
        widget.layout = self.container
        widget.pack(in_=self.container.body)
        self.config_widget(widget, restoration_data.get("info", {}))
        self.redraw()

    def get_restore(self, widget):
        return {
            "info": widget.pack_info(),
            "container": self.container,
            "index": self.children.index(widget)
        }

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
        definition = super().get_def(widget)
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
        info["in_"] = self.container.body
        widget.pack(**info)
        self._insert(widget)
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
        if self._children:
            last = self._children[-1]
            last.update_idletasks()
            return last.winfo_y() - self.container.body.winfo_y() + last.winfo_height()
        return 0

    def get_offset(self, index):
        if index >= 0:
            last = self._children[index]
            last.update_idletasks()
            return last.winfo_y() - self.container.body.winfo_y() + last.winfo_height()
        return 0

    def add_widget(self, widget, bounds=None, **kwargs):
        super().add_widget(widget, bounds, **kwargs)
        width, height = geometry.dimensions(bounds)
        self.attach(widget, width, height)
        self._insert(widget)

    def attach(self, widget, width, height):
        y = self.get_last()
        widget.place(in_=self.container.body, x=0, y=y, width=width, height=height, bordermode="outside")

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
            self._insert(child)

    def resize_widget(self, widget, direction, delta):
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
            self._insert(child)

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
            "name": "minsize",
            "default": 0,
        },
        "pad": {
            "display_name": "pad",
            "type": "dimension",
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
        self._insert(widget, widget.prev_stack_index if widget.layout == self.container else None)
        widget.level = self.level + 1
        widget.layout = self.container
        widget.grid(in_=self.container.body)
        self.config_widget(widget, data.get("info", {}))

    def end_move(self, widget):
        super().end_move(widget)
        kw = widget.recent_layout_info.get("info", {})
        self._grid_at_bounds(widget, widget.get_bounds(), **kw)
        self._update_stacking()
        self.clear_indicators()

    def _redraw_widget(self, widget):
        widget.grid(**self._grid_info(widget))

    def _redraw(self, row, column, row_shift, column_shift):
        for child in self.container.body.grid_slaves():
            info = child.grid_info()
            if info['column'] >= column:
                child.grid_configure(column=info["column"] + column_shift)
        for child in self.container.body.grid_slaves(None, column):
            info = child.grid_info()
            if info["row"] >= row:
                child.grid_configure(row=info["row"] + row_shift)

    def _adjust_rows(self, from_row=0):
        rows = self.container.body.grid_size()[1]
        for row in range(from_row, rows):
            if not self.container.body.grid_slaves(row):
                for child in self.container.body.grid_slaves(row + 1):
                    info = child.grid_info()
                    child.grid_configure(row=info["row"] - 1)

    def _adjust_columns(self, from_col):
        cols = self.container.body.grid_size()[1]
        for col in range(from_col, cols):
            if not self.container.body.grid_slaves(None, col):
                for child in self.container.body.grid_slaves(None, col + 1):
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
        info = self._temp.get(widget, {})
        info.update({"in_": self.container.body})
        return info

    def config_widget(self, widget, config):
        for prop in ("width", "height"):
            if prop in config:
                widget.configure(**{prop: config[prop]})
                config.pop(prop)
        widget.grid_configure(**config)

    def resize_widget(self, widget, direction, delta):
        pass

    def move_widget(self, widget, delta):
        super().move_widget(widget, delta)
        self._location_analysis(self.bounds_from_delta(widget, delta))

    def on_move_exit(self):
        super().on_move_exit()
        self.clear_indicators()

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        if bounds is not None:
            self._grid_at_bounds(widget, bounds, **kwargs)
        else:
            widget.grid(in_=self.container.body)
            self.config_widget(widget, kwargs)
        self._insert(widget, widget.prev_stack_index if widget.layout == self.container else None)
        self.clear_indicators()

    def _grid_at_bounds(self, widget, bounds, **kwargs):
        row, col, row_shift, column_shift = self._location_analysis(bounds)
        self._redraw(max(0, row), max(0, col), row_shift, column_shift)
        kwargs.update({'in_': self.container.body, 'row': max(0, row), 'column': max(0, col)})
        widget.grid(**kwargs)

    def _widget_at(self, row, column):
        return self.container.body.grid_slaves(column, row)

    def _location_analysis(self, bounds):
        self.clear_indicators()
        self._edge_indicator.update_idletasks()
        bounds = geometry.relative_bounds(bounds, self.container.body)
        x, y = bounds[0], bounds[1]
        w, h = geometry.dimensions(bounds)
        col, row = self.container.body.grid_location(x, y)
        x, y = geometry.upscale_bounds(bounds, self.container.body)[:2]
        slaves = self.container.body.grid_slaves(max(0, row), max(0, col))
        if len(slaves) == 0:
            self.container.body.update_idletasks()
            bbox = self.container.body.grid_bbox(col, row)
            bounds = *bbox[:2], bbox[0] + bbox[2], bbox[1] + bbox[3]
            # Make bounds relative to designer
            bounds = geometry.upscale_bounds(bounds, self.container.body)
            if geometry.dimensions(bounds) == (0, 0):
                w, h = w or 50, h or 25
                bounds = bounds[0], bounds[1], bounds[0] + w, bounds[1] + h
        else:
            bounds = geometry.bounds(slaves[0])
        y_offset, x_offset = 10, 10  # 0.15*(bounds[3] - bounds[1]), 0.15*(bounds[2] - bounds[0])
        # If the position is empty no need to alter the row or column
        resize = 1 if slaves else 0
        if y - bounds[1] < y_offset:
            self._edge_indicator.top(bounds)
            return row, col, resize, 0
        if bounds[3] - y < y_offset:
            self._edge_indicator.bottom(bounds)
            return row + resize, col, resize, 0
        if x - bounds[0] < x_offset:
            self._edge_indicator.left(bounds)
            return row, col, 0, resize
        if bounds[2] - x < x_offset:
            self._edge_indicator.right(bounds)
            return row, col + resize, 0, resize
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

    def react_to_pos(self, bounds):
        bounds = geometry.resolve_bounds(bounds, self.container.parent)
        self._location_analysis(bounds)

    def info(self, widget):
        info = widget.grid_info() or {}
        keys = widget.keys()
        for prop in ("width", "height"):
            if prop in keys:
                info.update({prop: widget[prop]})
        return info

    def get_def(self, widget):
        definition = super().get_def(widget)
        keys = widget.keys()
        for prop in ("width", "height"):
            if prop not in keys:
                definition.pop(prop)
        return definition

    def get_row_def(self, widget=None, row=None):
        definition = dict(self.GRID_CONFIG_DEFINITION)
        row_info = self.container.body.rowconfigure(widget.grid_info()["row"] if row is None else row)
        for key in definition:
            definition[key]["value"] = row_info[key]
        return definition

    def get_column_def(self, widget=None, column=None):
        definition = dict(self.GRID_CONFIG_DEFINITION)
        column_info = self.container.body.columnconfigure(widget.grid_info()["column"] if column is None else column)
        for key in definition:
            definition[key]["value"] = column_info[key]
        return definition

    def copy_layout(self, widget, from_):
        info = from_.grid_info()
        info["in_"] = self.container.body
        widget.grid(**info)
        self._insert(widget)
        super().add_widget(widget, (0, 0, 0, 0))

    def clear_all(self):
        # remove the children but still maintain them in the children list
        for child in self.children:
            child.grid_forget()


class TabLayoutStrategy(BaseLayoutStrategy):
    # TODO Extend support for side specific padding
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
    name = "TabLayout"
    icon = "notebook"
    manager = "tab"
    stacking_support = True

    def __init__(self, master):
        super().__init__(master)
        self._current_tab = None
        self.container.body.bind("<<NotebookTabChanged>>", self._tab_switched)

    def config_widget(self, widget, config):
        self.container.body.tab(widget, **config)

    def end_move(self, widget):
        self.container.body.add(widget)
        self.container.body.tab(widget, **widget.recent_layout_info.get("info", {}))
        self._redraw(widget.recent_layout_info.get("index", -1))

    def restore_widget(self, widget, data=None):
        restoration_data = widget.recent_layout_info if data is None else data
        self._insert(widget, restoration_data.get("index", -1))
        widget.level = self.level + 1
        widget.layout = self.container
        self.container.body.add(widget)
        self.container.body.tab(widget, **restoration_data.get("info", {}))
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
        selected = self.container.select()
        for child in affected:
            cache[child] = self.info(child)
            self.container.body.forget(child)
        for i, child in enumerate(affected):
            self.container.body.add(child)
            self.container.body.tab(child, **cache.get(child, {}))
            if str(child) == selected:
                self.container.select(i)

    def resize_widget(self, widget, direction, delta):
        pass

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        self.container.body.add(widget, text=widget.id)
        self.container.body.tab(widget, **kwargs)
        self._insert(widget)
        length = len(self.container.tabs())
        if length > 1:
            self.container.select(length - 1)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        try:
            self.container.body.forget(widget)
        except tk.TclError:
            pass

    def info(self, widget):
        info = self.container.body.tab(widget) or {}
        if "padding" in info:
            # use the first padding value until we can support full padding
            info["padding"] = info["padding"][0]
        info["compound"] = info.get("compound", "") or "none"
        return info

    def apply(self, prop, value, widget):
        self.container.body.tab(widget, **{prop: value})

    def _tab_switched(self, *_):
        if self._current_tab:
            # Take its level down by one
            self._current_tab.level = self.level + 1
        self._current_tab = self.container.body.nametowidget(self.container.body.select())
        # Take its level one place above other tabs
        self._current_tab.level = self.level + 2

    def widgets_reordered(self):
        self._redraw(0)

    def copy_layout(self, widget, from_):
        info = from_.layout.body.tab(from_)
        self.add_widget(widget, (0, 0, 0, 0), **info)

    def clear_all(self):
        # No implementation needed as the tab layout strategy never needs to change
        pass


class PanedLayoutStrategy(BaseLayoutStrategy):
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
            "default": 0,
            "name": "minsize",
        }
    }
    name = "PanedLayout"
    icon = "flip_horizontal"
    manager = "pane"
    stacking_support = False

    def get_restore(self, widget):
        return {
            "info": self.info(widget),
            "index": self.children.index(widget),
            "container": self.container
        }

    def config_widget(self, widget, config):
        self._config(widget, **config)

    def end_move(self, widget):
        self.container.body.add(widget)
        self._config(widget, **widget.recent_layout_info.get("info", {}))
        self._redraw(widget.recent_layout_info.get("index", -1))

    def restore_widget(self, widget, data=None):
        restoration_data = widget.recent_layout_info if data is None else data
        self._insert(widget, restoration_data.get("index", -1))
        widget.level = self.level + 1
        widget.layout = self.container
        self.container.body.add(widget)
        self._config(widget, **restoration_data.get("info", {}))
        self._redraw(restoration_data.get("index", -1))

    def _redraw(self, start_index=0):
        affected = self.children[start_index:]
        cache = {}
        for child in affected:
            cache[child] = self.info(child)
            self.container.body.forget(child)
        for child in affected:
            self.container.body.add(child)
            self._config(child, **cache.get(child, {}))

    def clear_all(self):
        pass

    def resize_widget(self, widget, direction, delta):
        pass

    def add_widget(self, widget, bounds=None, **kwargs):
        super().remove_widget(widget)
        super().add_widget(widget, bounds, **kwargs)
        if str(widget) not in self.container.body.panes():
            self.container.body.add(widget)
        self._config(widget, **kwargs)
        self._insert(widget)

    def _config(self, widget, **kwargs):
        if not kwargs:
            return self.container.body.paneconfig(widget)
        self.container.body.paneconfig(widget, **kwargs)

    def get_def(self, widget):
        definition = super().get_def(widget)
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
        self.container.body.paneconfig(widget, **{prop: value})

    def remove_widget(self, widget):
        super().remove_widget(widget)
        try:
            self.container.body.forget(widget)
        except tk.TclError:
            pass

    def copy_layout(self, widget, from_):
        info = from_.layout.body.paneconfig(from_)
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
        self.container.body.pane(widget, **{prop: value})

    def _config(self, widget, **kwargs):
        if not kwargs:
            return self.container.body.pane(widget)
        self.container.body.pane(widget, **kwargs)

    def copy_layout(self, widget, from_):
        info = from_.layout.body.pane(from_)
        self.add_widget(widget, (0, 0, 0, 0), **info)

    def get_def(self, widget):
        # We need to override the hinting behaviour inherited since there's no
        # orient and minsize options
        return super(PanedLayoutStrategy, self).get_def(widget)

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
