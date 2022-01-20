# ======================================================================= #
# Copyright (C) 2021 Hoverset Group.                                      #
# ======================================================================= #
import abc
from collections import defaultdict

from formation.formats import Node
from hoverset.data.keymap import KeyMap, CharKey

from hoverset.ui.icons import get_icon_image as icon
from hoverset.ui.widgets import EventMask
from hoverset.util.execution import Action
from hoverset.data.actions import Routine
from hoverset.ui.menu import MenuUtils, EnableIf

from studio.tools._base import BaseTool
from studio.feature.components import ComponentPane, SelectToDrawGroup
from studio.feature.stylepane import StyleGroup
from studio.ui.tree import NestedTreeView
from studio.lib import generate_id
from studio.lib.canvas import *
from studio.lib.legacy import Canvas
from studio.parsers.loader import BaseStudioAdapter, DesignBuilder


class Coordinate:
    pool = defaultdict(list)
    active = set()
    min_radius = 3
    max_radius = 5

    def __init__(self, canvas, controller, x, y):
        self.radius = self.min_radius
        self.canvas = canvas
        self.controller = controller
        self.x = x
        self.y = y
        self._id = canvas.create_oval(
            x - self.radius, y - self.radius, x + self.radius, y + self.radius,
            fill=self.controller.tool.studio.style.colors["accent"],
            tags=("coordinate", "controller")
        )
        canvas.tag_bind(self._id, "<ButtonRelease-1>", self._end_drag)
        canvas.tag_bind(self._id, "<Motion>", self._drag)
        canvas.tag_bind(self._id, "<Enter>", lambda _: self.grow_effect())
        canvas.tag_bind(self._id, "<Leave>", lambda _: self.grow_effect(True))
        MenuUtils.bind_canvas_context(self.canvas, self._id, self._context_menu)
        self.active.add(self)
        self._listeners = []

    def grow_effect(self, shrink=False):
        self.radius = self.min_radius if shrink else self.max_radius
        self.place()

    def add_listener(self, func, *args, **kwargs):
        def callback():
            func(*args, **kwargs)
        self._listeners.append(callback)
        return callback

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def retire(self):
        # remove from view without deleting
        self.canvas.itemconfigure(self._id, state='hidden')
        self.pool["canvas"].append(self)
        self._listeners = []

    def place(self, x=None, y=None):
        x = self.x if x is None else x
        y = self.y if y is None else y
        self.canvas.coords(
            self._id,
            x - self.radius, y - self.radius, x + self.radius, y + self.radius
        )
        self.x = x
        self.y = y
        for listener in self._listeners:
            listener()

    def shift(self, delta_x, delta_y):
        self.place(self.x + delta_x, self.y + delta_y)

    def revive(self, controller, x, y):
        self.controller = controller
        self.canvas.itemconfigure(self._id, state='normal')
        self.place(x, y)
        self.active.add(self)

    def _context_menu(self, event):
        self.controller.on_coord_context(self, event)

    def _drag(self, event):
        if not event.state & EventMask.MOUSE_BUTTON_1:
            return
        self.x = self.canvas.canvasx(event.x)
        self.y = self.canvas.canvasy(event.y)
        self.place()
        self.controller.on_coord_change(self)

    def _end_drag(self, _):
        self.controller.on_release()

    @classmethod
    def acquire(cls, canvas, controller, x, y):
        if cls.pool[canvas]:
            coord = cls.pool[canvas][0]
            cls.pool[canvas].remove(coord)
            coord.revive(controller, x, y)
            return coord
        return cls(canvas, controller, x, y)


class Link:
    pool = defaultdict(list)
    active = set()

    def __init__(self, canvas, controller, coord1, coord2):
        self.canvas = canvas
        self.controller = controller
        self._id = canvas.create_line(
            coord1.x, coord1.y, coord2.x, coord2.y,
            fill=self.controller.tool.studio.style.colors["accent"],
            tag=("link", "controller"), dash=(5, 4), width=2
        )
        self.link_coord(coord1, coord2)
        canvas.tag_bind(self._id, "<ButtonRelease-1>", self._end_drag)
        MenuUtils.bind_canvas_context(self.canvas, self._id, self._context_menu)
        canvas.tag_bind(self._id, "<Motion>", self._drag)
        self.active.add(self)
        self._coord_latch = None

    def _to_canvas_coord(self, x, y):
        return self.canvas.canvasx(x), self.canvas.canvasy(y)

    def _context_menu(self, event):
        self.controller.on_link_context(self, event)

    def _drag(self, event):
        if not event.state & EventMask.MOUSE_BUTTON_1:
            return
        if self._coord_latch:
            x, y = self._to_canvas_coord(event.x, event.y)
            xl, yl = self._coord_latch
            self.controller.on_move(x - xl, y - yl)
            self._coord_latch = x, y
        else:
            self._coord_latch = self._to_canvas_coord(event.x, event.y)

    def _end_drag(self, _):
        self.controller.on_release()
        self._coord_latch = None

    def place(self, coord1, coord2):
        self.canvas.coords(self._id, coord1.x, coord1.y, coord2.x, coord2.y)
        self.canvas.tag_lower(self._id, "coordinate")

    def link_coord(self, coord1, coord2):
        coord1.add_listener(self.coord_changed)
        coord2.add_listener(self.coord_changed)
        self.coord1 = coord1
        self.coord2 = coord2
        self.place(coord1, coord2)

    def unlink_coord(self):
        self.coord1 = self.coord2 = None
        self._listeners = []

    def revive(self, controller, coord1, coord2):
        self.controller = controller
        self.canvas.itemconfigure(self._id, state='normal')
        self.link_coord(coord1, coord2)
        self.active.add(self)

    def retire(self):
        # remove from view without deleting
        self.canvas.itemconfigure(self._id, state='hidden')
        self.pool["canvas"].append(self)
        self.unlink_coord()

    def coord_changed(self):
        self.place(self.coord1, self.coord2)

    @classmethod
    def acquire(cls, canvas, controller, coord1, coord2):
        if cls.pool[canvas]:
            coord = cls.pool[canvas][0]
            cls.pool[canvas].remove(coord)
            coord.revive(controller, coord1, coord2)
            return coord
        return cls(canvas, controller, coord1, coord2)


class Controller(abc.ABC):

    def __init__(self, canvas, tool, item=None, **kw):
        self.canvas = canvas
        self.tool = tool
        self.item = item
        self._on_change = None
        self.coords = []
        self.links = []

    def update(self):
        pass

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda item: func(item, *args, **kwargs)

    def _change(self):
        if self._on_change:
            self._on_change(self.item)

    def highlight(self, item):
        self.item = item
        # raise controller elements to the top
        self.canvas.tag_raise("controller")

    @abc.abstractmethod
    def get_coords(self):
        pass

    def on_coord_change(self, coord):
        pass

    def on_coord_context(self, coord, event):
        pass

    def on_link_context(self, link, event):
        pass

    def on_move(self, delta_x, delta_y, propagated=False):
        for coord in self.coords:
            coord.shift(delta_x, delta_y)
        self.item.move(delta_x, delta_y)
        if not propagated:
            self.tool.propagate_move(delta_x, delta_y, self.item)

    def on_release(self):
        self.tool.on_layout_change()

    def release(self):
        for coord in self.coords:
            coord.retire()
        for link in self.links:
            link.retire()
        self.coords.clear()
        self.links.clear()


class SquareController(Controller):

    def __init__(self, canvas, tool, item=None, **kw):
        super(SquareController, self).__init__(canvas, tool, item, **kw)
        self.nw = Coordinate.acquire(canvas, self, 20, 20)
        self.ne = Coordinate.acquire(canvas, self, 20, 20)
        self.se = Coordinate.acquire(canvas, self, 20, 20)
        self.sw = Coordinate.acquire(canvas, self, 20, 20)
        self.n = Link.acquire(canvas, self, self.nw, self.ne)
        self.s = Link.acquire(canvas, self, self.sw, self.se)
        self.e = Link.acquire(canvas, self, self.ne, self.se)
        self.w = Link.acquire(canvas, self, self.nw, self.sw)
        self.coords = [self.ne, self.nw, self.se, self.sw]
        self.links = [self.n, self.w, self.e, self.s]
        if item:
            self.highlight(item)

    def highlight(self, item):
        super(SquareController, self).highlight(item)
        x1, y1, x2, y2 = item.coords()
        self.nw.place(x1, y1)
        self.ne.place(x2, y1)
        self.se.place(x2, y2)
        self.sw.place(x1, y2)

    def update(self):
        self.highlight(self.item)

    def on_coord_change(self, coord):
        x, y = coord.x, coord.y
        if coord == self.nw:
            self.ne.place(y=y)
            self.sw.place(x=x)
        elif coord == self.ne:
            self.nw.place(y=y)
            self.se.place(x=x)
        elif coord == self.sw:
            self.nw.place(x=x)
            self.se.place(y=y)
        elif coord == self.se:
            self.ne.place(x=x)
            self.sw.place(y=y)
        else:
            return
        self.item.coords(self.get_coords())
        self._change()

    def get_coords(self):
        return (
            self.nw.x, self.nw.y,
            self.se.x, self.se.y
        )


class LinearController(Controller):
    _closed = False

    def __init__(self, canvas, tool, item=None, **kw):
        super(LinearController, self).__init__(canvas, tool, item, **kw)
        if item:
            self.highlight(item)
        self._link_context = MenuUtils.make_dynamic((
            ("command", "add point", icon("add", 14, 14), self._add_point, {}),
        ), tool.studio, tool.studio.style)
        self._coord_context = MenuUtils.make_dynamic((
            ("command", "remove", icon("close", 14, 14), self._remove_point, {}),
        ), tool.studio, tool.studio.style)
        self._active_link = None
        self._active_coord = None
        self._active_point = None

    def on_link_context(self, link, event):
        MenuUtils.popup(event, self._link_context)
        self._active_link = link
        self._active_point = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def on_coord_context(self, coord, event):
        MenuUtils.popup(event, self._coord_context)
        self._active_coord = coord
        self._active_point = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def _add_point(self):
        if not self._active_link:
            return
        index = self.coords.index(self._active_link.coord1) + 1
        new_coord = Coordinate.acquire(self.canvas, self, *self._active_point)
        self.coords.insert(index, new_coord)
        self.item.coords(self.get_coords())
        self.update()
        self.tool.on_layout_change()

    def _remove_point(self):
        if not self._active_coord:
            return
        self.coords.remove(self._active_coord)
        self._active_coord.retire()
        self.item.coords(self.get_coords())
        self.update()
        self.tool.on_layout_change()

    def on_coord_change(self, coord):
        self.item.coords(self.get_coords())
        self._change()

    def get_coords(self):
        return [coord for c in self.coords for coord in (c.x, c.y)]

    def update(self):
        # there is no smarter way to adjust links and coordinates
        # clear them and reapply
        self.release()
        self.highlight(self.item)

    def highlight(self, item):
        coords = item.coords()
        self.release()
        prev = Coordinate.acquire(self.canvas, self, *coords[:2])
        self.coords.append(prev)
        for i in range(2, len(coords), 2):
            # just in case the length of coordinates is odd
            if i + 1 >= len(coords):
                break
            cd = Coordinate.acquire(self.canvas, self, coords[i], coords[i + 1])
            self.coords.append(cd)
            self.links.append(Link.acquire(self.canvas, self, prev, cd))
            prev = cd

        if self._closed:
            self.links.append(Link.acquire(self.canvas, self, prev, self.coords[0]))

        # ensure you have at least one item with "controller" tag before calling super
        super(LinearController, self).highlight(item)


class ClosedLinearController(LinearController):
    _closed = True


class PointController(Controller):

    def __init__(self, canvas, tool, item=None, **kw):
        super(PointController, self).__init__(canvas, tool, item, **kw)
        self._border = None
        if item:
            self.highlight(item)

    def get_coords(self):
        return [self.coords[0].x, self.coords[0].y]

    def on_coord_change(self, coord):
        self.item.coords(self.get_coords())
        self._change()

    def on_move(self, delta_x, delta_y, propagated=False):
        super(PointController, self).on_move(delta_x, delta_y, propagated)
        self.highlight(self.item)

    def _get_border_coords(self, item):
        bbox = item.bbox() or (*item.coords(), *item.coords())
        x1, y1, x2, y2 = bbox
        x1, y1, x2, y2 = x1 - 2, y1 - 2, x2 + 2, y2 + 2
        return x1, y1, x2, y1, x2, y2, x1, y2, x1, y1

    def update(self):
        self.canvas.coords(self._border, *self._get_border_coords(self.item))

    def highlight(self, item):
        coords = self._get_border_coords(item)
        if self._border:
            self.canvas.coords(self._border, *coords)
        else:
            self._border = self.canvas.create_line(
                *coords, fill=self.tool.studio.style.colors["accent"],
                tag="controller", dash=(5, 4), width=2
            )
        super(PointController, self).highlight(item)

    def __del__(self):
        if self._border:
            self.canvas.delete(self._border)


class Draw(abc.ABC):

    def __init__(self, tool):
        self.tool = tool
        self.active_item = None

    @property
    def canvas(self):
        return self.tool.canvas

    def canvas_coord(self, x, y):
        return self.canvas.canvasx(x), self.canvas.canvasy(y)

    @abc.abstractmethod
    def on_button_press(self, event):
        pass

    @abc.abstractmethod
    def on_button_release(self, event):
        pass

    @abc.abstractmethod
    def on_double_press(self, event):
        pass

    @abc.abstractmethod
    def on_motion(self, event):
        pass


class SquareDraw(Draw):

    def __init__(self, tool):
        super(SquareDraw, self).__init__(tool)
        self.coords = (0, 0, 0, 0)
        self.item = None
        self.draw_start = False

    def on_button_press(self, event):
        x, y = self.canvas_coord(event.x, event.y)
        self.coords = (x, y, x, y)
        self.draw_start = True

    def on_button_release(self, event):
        self.draw_start = False
        if self.item:
            self.tool.on_item_added(self.item)
            self.item = None

    def on_double_press(self, event):
        pass

    def on_motion(self, event):
        if not self.draw_start:
            return
        x, y = self.canvas_coord(event.x, event.y)
        if self.item is None:
            self.item = self.tool.create_item(self.tool.current_draw, self.coords)
        self.coords = (*self.coords[:2], x, y)
        self.item.coords(*self.coords)


class LinearDraw(Draw):

    def __init__(self, tool):
        super(LinearDraw, self).__init__(tool)
        self.coords = [0, 0, 0, 0]
        self.item = None
        self.draw_start = False

    def on_button_press(self, event):
        x, y = self.canvas_coord(event.x, event.y)
        if not self.draw_start:
            self.coords = [x, y, x, y]
        else:
            self.coords.extend([x, y])
            self.item.coords(*self.coords)
        self.draw_start = True

    def on_button_release(self, event):
        pass

    def on_double_press(self, event):
        self.draw_start = False
        if self.item:
            # remove last point which is usually a duplicate
            self.item.coords(*self.coords[:-2])
            self.tool.on_item_added(self.item)
            self.item = None

    def on_motion(self, event):
        if not self.draw_start:
            return
        if self.item is None:
            self.item = self.tool.create_item(self.tool.current_draw, self.coords)
        x, y = self.canvas_coord(event.x, event.y)
        # set the last two coordinates
        self.coords[-2:] = [x, y]
        self.item.coords(*self.coords)


class PointDraw(Draw):

    def __init__(self, tool, **default_opts):
        super(PointDraw, self).__init__(tool)
        self.default_opts = default_opts

    def on_button_press(self, event):
        if event.state & EventMask.CONTROL:
            return
        x, y = self.canvas_coord(event.x, event.y)
        self.item = self.tool.create_item(
            self.tool.current_draw, (x, y), **self.default_opts
        )

    def on_button_release(self, event):
        self.tool.on_item_added(self.item)
        self.item = None

    def on_double_press(self, event):
        pass

    def on_motion(self, event):
        pass


class TextDraw(PointDraw):

    def on_button_press(self, event):
        super(TextDraw, self).on_button_press(event)
        self.item.configure(text=self.item.name)


class CanvasStyleGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        self.tool = cnf.pop('tool', None)
        super().__init__(master, pane, **cnf)
        self.label = "Canvas Item"
        self.prop_keys = None
        self._prev_prop_keys = set()
        self._empty_message = "Select canvas item to see styles"

    @property
    def cv_items(self):
        # selected canvas items
        return self.tool.selected_items

    def supports_widget(self, widget):
        return isinstance(widget, Canvas)

    def can_optimize(self):
        # probably needs a rethink if we consider definition overrides
        # in canvas items but there isn't much of that so this will do
        return self.prop_keys == self._prev_prop_keys

    def compute_prop_keys(self):
        items = self.cv_items
        if not items:
            self.prop_keys = set()
        else:
            self.prop_keys = None
            # determine common configs for multi-selected items
            for item in self.cv_items:
                if self.prop_keys is None:
                    self.prop_keys = set(item.configure())
                else:
                    self.prop_keys &= set(item.configure())
            if len(items) > 1:
                # id cannot be set for multi-selected items
                self.prop_keys.remove('id')

    def on_widget_change(self, widget):
        self._prev_prop_keys = self.prop_keys
        self.compute_prop_keys()
        super(CanvasStyleGroup, self).on_widget_change(widget)
        self.style_pane.remove_loading()

    def _get_prop(self, prop, widget):
        # not very useful to us
        return None

    def _get_key(self, widget, prop):
        # generate a key identifying the multi-selection state and prop modified
        return f"{','.join(map(lambda x: str(x._id), self.cv_items))}:{prop}"

    def _get_action_data(self, widget, prop):
        return {item: {prop: item.cget(prop)} for item in self.cv_items}

    def _apply_action(self, prop, value, widget, data):
        for item in data:
            item.configure(data[item])
            if item._controller:
                item._controller.update()
        if self.tool.canvas == widget:
            self.on_widget_change(widget)
        self.tool.on_items_modified(data.keys())

    def _set_prop(self, prop, value, widget):
        for item in self.cv_items:
            item.configure({prop: value})
            if item._controller:
                item._controller.update()
        self.tool.on_items_modified(self.cv_items)

    def get_definition(self):
        if not self.cv_items:
            return {}
        rough_definition = self.cv_items[0].properties
        if len(self.cv_items) == 1:
            # for single item no need to refine definitions any further
            return rough_definition
        resolved = {}
        for prop in self.prop_keys:
            if prop not in rough_definition:
                continue
            definition = resolved[prop] = rough_definition[prop]
            # use default for value
            definition.update(value=definition['default'])
        return resolved


class CanvasTreeView(NestedTreeView):
    class Node(NestedTreeView.Node):

        def __init__(self, master=None, **config):
            super().__init__(master, **config)
            self.item: CanvasItem = config.get("item")
            self.item.node = self
            self._color = self.style.colors["secondary1"]
            self.name_pad.configure(text=self.item.name)
            self.icon_pad.configure(
                image=icon(self.item.icon, 15, 15, color=self._color)
            )
            self.editable = True
            self.strict_mode = True

        def widget_modified(self, widget):
            self.item = widget
            self.name_pad.configure(text=self.item.name)
            self.icon_pad.configure(
                image=icon(self.item.icon, 15, 15, color=self._color)
            )

        def select(self, event=None, silently=False):
            super(CanvasTreeView.Node, self).select(event, silently)
            if event:
                self.item.canvas.focus_set()

    def __init__(self, canvas, **kw):
        super(CanvasTreeView, self).__init__(canvas.node, **kw)
        self._cv_node = canvas.node
        self.canvas = canvas
        self._is_mapped = False
        self.allow_multi_select(True)

    def add(self, node):
        super(CanvasTreeView, self).add(node)
        # if we have a node we make ourselves visible
        if self not in self._cv_node.nodes:
            self._cv_node.add(self)
            
    def insert(self, index=None, *nodes):
        super(CanvasTreeView, self).insert(index, *nodes)
        # also make sure nodes is not empty
        if self not in self._cv_node.nodes and nodes:
            self._cv_node.add(self)

    def remove(self, node):
        super(CanvasTreeView, self).remove(node)
        # if no nodes are left we hide ourselves
        if not self.nodes:
            self._cv_node.remove(self)

    def reorder(self, reorder_data):
        # rearrange nodes based on data containing {item: index, ...}
        for item in reorder_data:
            self.insert(reorder_data[item], item.node)


class CanvasStudioAdapter(BaseStudioAdapter):
    _tool = None

    @classmethod
    def assert_tool(cls):
        # make sure tool is initialized
        if cls._tool is None:
            raise RuntimeError("Canvas tool not initialized. Could not load canvas.")

    @classmethod
    def generate(cls, widget, parent=None):
        cls.assert_tool()
        # if canvas is selected there is a chance its cursor has been modified by tool
        # below lies a hack to set the right cursor and restore it after loading is complete
        cursor = None
        if widget == cls._tool.canvas:
            cursor = widget["cursor"]
            widget.config(cursor=cls._tool._cursor)
        node = BaseStudioAdapter.generate(widget, parent)
        if cursor:
            widget.config(cursor=cursor)
        if getattr(widget, "_cv_initialized", False):
            for item in widget._cv_items:
                opts = {
                    "name": item.name,
                    "coords": ",".join(map(lambda c: str(round(c)), item.coords())),
                    "attr": item.altered_options()
                }
                if not item.name:
                    opts.pop("name", None)
                Node(node, item.__class__.__name__, opts)

        return node

    @classmethod
    def load(cls, node, designer, parent, bounds=None):
        widget = BaseStudioAdapter.load(node, designer, parent, bounds=None)
        cls.assert_tool()
        if node.children:
            cls._tool.initialize_canvas(widget)
        for sub_node in node:
            if sub_node.type not in CANVAS_ITEM_MAP:
                # ignore non canvas items
                continue
            # use a copy just in case something gets popped down the line
            config = dict(sub_node.attrib.get("attr", {}))
            # add name to config as id so the intercepts can set it for us
            config["id"] = sub_node.attrib.get("name", "")
            coords = sub_node.attrib.get("coords", "").split(",")
            if len(coords) < 2:
                raise ValueError("Not enough coordinates provided.")
            component = CANVAS_ITEM_MAP[sub_node.type]
            item = component(widget, *coords)
            item.configure(config)
            cls._tool.create_item(
                component, item=item, canvas=widget, silently=True
            )
        return widget


class CanvasTool(BaseTool):
    name = "Canvas"
    icon = "paint"

    def __init__(self, studio, manager):
        super(CanvasTool, self).__init__(studio, manager)
        self._component_pane: ComponentPane = self.studio.get_feature(ComponentPane)
        self.item_select = self._component_pane.register_group(
            "Canvas", CANVAS_ITEMS, SelectToDrawGroup, self._evaluator
        )
        self.style_group = studio.style_pane.add_group(
            CanvasStyleGroup, tool=self
        )

        CanvasStudioAdapter._tool = self
        # connect the canvas adapter to load canvas objects to the studio
        DesignBuilder.add_adapter(CanvasStudioAdapter, Canvas)

        self.items = []
        self.item_select.on_select(self.set_draw)
        self.canvas = None
        self._cursor = "arrow"
        self.current_draw = None
        self.selected_items = []
        self._clipboard = None
        self._latch_pos = 0, 0

        self._image_placeholder = icon("image_dark", 60, 60)

        self.square_draw = SquareDraw(self)
        self.line_draw = LinearDraw(self)
        self.text_draw = TextDraw(self)
        self.bitmap_draw = PointDraw(self, bitmap="gray25")
        self.image_draw = PointDraw(self, image=self._image_placeholder)

        self.draw_map = {
            Oval: self.square_draw,
            Rectangle: self.square_draw,
            Arc: self.square_draw,
            Line: self.line_draw,
            Polygon: self.line_draw,
            Text: self.text_draw,
            Bitmap: self.bitmap_draw,
            Image: self.image_draw,
        }

        self.controller_map = {
            Oval: SquareController,
            Rectangle: SquareController,
            Arc: SquareController,
            Line: LinearController,
            Polygon: ClosedLinearController,
            Text: PointController,
            Bitmap: PointController,
            Image: PointController,
        }

        self.keymap = KeyMap(None)
        CTRL = KeyMap.CTRL
        self.routines = (
            Routine(self.cut_items, 'CV_CUT', 'Cut selected items', 'canvas', CTRL + CharKey('x')),
            Routine(self.copy_items, 'CV_COPY', 'Copy selected items', 'canvas', CTRL + CharKey('c')),
            Routine(self.paste_items, 'CV_PASTE', 'Paste selected items', 'canvas', CTRL + CharKey('v')),
            Routine(self.delete_items, 'CV_DELETE', 'Delete selected items', 'canvas', KeyMap.DELETE),
            Routine(self.duplicate_items, 'CV_DUPLICATE', 'Duplicate selected items', 'canvas', CTRL + CharKey('d')),
            Routine(self._send_back, 'CV_BACK', 'Send item to back', 'canvas', CharKey(']')),
            Routine(self._bring_front, 'CV_FRONT', 'Bring item to front', 'canvas', CharKey('[')),
            Routine(lambda: self._send_back(1), 'CV_BACK_1', 'send item back one step', 'canvas', CTRL + CharKey(']')),
            Routine(lambda: self._bring_front(1), 'CV_FRONT_1', 'bring item forward one step', 'canvas',
                    CTRL + CharKey('[')),
        )
        self.keymap.add_routines(*self.routines)

        self._item_context_menu = MenuUtils.make_dynamic((
            EnableIf(
                lambda: self.selected_items,
                ("separator",),
                ("command", "copy", icon("copy", 14, 14), self._get_routine('CV_COPY'), {}),
                ("command", "duplicate", icon("copy", 14, 14), self._get_routine('CV_DUPLICATE'), {}),
                EnableIf(
                    lambda: self._clipboard is not None,
                    ("command", "paste", icon("clipboard", 14, 14), self._get_routine('CV_PASTE'), {})
                ),
                ("command", "cut", icon("cut", 14, 14), self._get_routine('CV_CUT'), {}),
                ("separator",),
                ("command", "delete", icon("delete", 14, 14), self._get_routine('CV_DELETE'), {}),
                ("separator",),
                ("command", "send to back", icon("send_to_back", 14, 14), self._get_routine('CV_BACK'), {}),
                ("command", "bring to front", icon("bring_to_front", 14, 14), self._get_routine('CV_FRONT'), {}),
                ("command", "back one step", icon("send_to_back", 14, 14), self._get_routine('CV_BACK_1'), {}),
                ("command", "forward one step", icon("bring_to_front", 14, 14), self._get_routine('CV_FRONT_1'), {}),
            ),
        ), self.studio, self.studio.style)

        self._canvas_menu = MenuUtils.make_dynamic((
            EnableIf(
                lambda: self._clipboard is not None,
                ("command", "paste", icon("clipboard", 14, 14),
                 self._get_routine('CV_PASTE'), {})
            ),
        ), self.studio, self.studio.style)

    @property
    def _ids(self):
        return [item.name for item_set in self.items for item in item_set._cv_items]

    def initialize_canvas(self, canvas=None):
        canvas = canvas or self.canvas
        if canvas and not getattr(canvas, "_cv_initialized", False):
            canvas.bind(
                "<ButtonPress-1>", self._draw_dispatch("on_button_press"), True)
            canvas.bind(
                "<ButtonRelease>", self._draw_dispatch("on_button_release"), True)
            canvas.bind(
                "<Double-Button-1>", self._draw_dispatch("on_double_press"), True)
            canvas.bind(
                "<Motion>", self._draw_dispatch("on_motion"), True)
            canvas.bind("<Control-Button-1>", self._enter_pointer_mode)
            canvas.bind("<Button-1>", self._latch_and_focus(canvas), True)
            self.keymap._bind(canvas)
            canvas.on_context_menu(self._show_canvas_menu(canvas))
            canvas._cv_tree = CanvasTreeView(canvas)
            canvas._cv_tree.on_structure_change(self._update_stacking, canvas)
            canvas._cv_tree.on_select(self._update_selection, canvas)
            canvas._cv_items = []
            canvas._cv_initialized = True

    @property
    def sorted_selected_items(self):
        return sorted(self.selected_items, key=self.canvas._cv_items.index)

    def _latch_and_focus(self, canvas):

        def func(event):
            canvas.focus_set()
            self._latch_pos = canvas.canvasx(event.x), canvas.canvasy(event.y)

        return func

    def _enter_pointer_mode(self, *_):
        if self.item_select._selected is None:
            return
        self.item_select._selected.deselect()

    def _show_item_menu(self, item):
        def show(event):
            if item in self.selected_items:
                MenuUtils.popup(event, self._item_context_menu)
        return show

    def _show_canvas_menu(self, canvas):

        def show(event):
            x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
            self._latch_pos = x, y
            if not canvas.find_overlapping(x, y, x, y):
                MenuUtils.popup(event, self._canvas_menu)
            return 'break'
        return show

    def _send_back(self, steps=None):
        if not self.selected_items:
            return
        items = self.sorted_selected_items
        if steps is None:
            self._update_stacking(
                self.canvas,
                # arrange starting from zero
                {item: index for index, item in enumerate(items)}
            )
        else:
            self._update_stacking(
                self.canvas,
                # clamp to ensure non-negative index
                {item: max(0, self.canvas._cv_items.index(item) - steps) for item in items}
            )

    def _bring_front(self, steps=None):
        if not self.selected_items:
            return
        # work with items in stacking order
        items = self.sorted_selected_items
        cv_items = self.canvas._cv_items
        if steps is None:
            end = len(cv_items) - 1
            self._update_stacking(
                self.canvas,
                # insert each item to the end of the list, will be done in stacking order
                {item: end for item in items}
            )
        else:
            self._update_stacking(
                self.canvas,
                # clamp the new index to within length of items
                {item: min(len(cv_items) - 1, cv_items.index(item) + steps) for item in items}
            )

    def _update_stacking(self, canvas, data=None, silently=False):
        if data:
            canvas._cv_tree.reorder(data)
        else:
            data = {}
        canvas._cv_items.sort(key=lambda x: canvas._cv_tree.nodes.index(x.node))
        prev_data = {}
        for index, item in enumerate(canvas._cv_items):
            if item._prev_index != index:
                # old data
                prev_data[item] = item._prev_index
                # new data
                data[item] = index
            item._prev_index = index
            if index > 0:
                item.lift(canvas._cv_items[index - 1]._id)
        if not silently and prev_data != data:
            self.studio.new_action(Action(
                lambda _: self._update_stacking(canvas, prev_data, True),
                lambda _: self._update_stacking(canvas, data, True)
            ))

    def _get_routine(self, key):
        for routine in self.routines:
            if routine.key == key:
                return routine

    def create_item(self, component, coords=(), item=None, canvas=None, silently=False, **kwargs):
        canvas = canvas or self.canvas
        if item is None:
            opts = dict(**component.defaults)
            opts.update(kwargs)
            item = component(canvas, *coords, **opts)
            # generate a unique id
            item.name = generate_id(component, self._ids)
        canvas._cv_items.append(item)
        item._prev_index = canvas._cv_items.index(item)
        node = canvas._cv_tree.add_as_node(item=item)
        item.bind("<ButtonRelease-1>", lambda e: self._handle_select(item, e), True)
        item.bind("<ButtonRelease-1>", lambda e: self._handle_end(item, e), True)
        item.bind("<Motion>", lambda e: self._handle_move(item, e), True)
        MenuUtils.bind_context(item, self._show_item_menu(item))
        MenuUtils.bind_all_context(node, self._show_item_menu(item))
        if not silently:
            self.studio.new_action(Action(
                lambda _: self.remove_items([item], silently=True),
                lambda _: self.restore_items([item])
            ))
        return item

    def remove_items(self, items, silently=False):
        if not items:
            return
        # ideally all items will have the same canvas
        canvas = items[0].canvas
        items = sorted(items, key=canvas._cv_items.index)
        self.deselect_items(items)
        for item in items:
            item.hide()
            canvas._cv_items.remove(item)
            item.node.remove()
        if not silently:
            self.studio.new_action(Action(
                lambda _: self.restore_items(items),
                lambda _: self.remove_items(items, silently=True)
            ))

    def restore_items(self, items):
        for item in items:
            item.show()
            canvas = item.canvas
            if item._prev_index is not None:
                canvas._cv_items.insert(item._prev_index, item)
            canvas._cv_tree.insert(item._prev_index, item.node)

    def _get_copy_data(self):
        if not self.selected_items:
            return []
        items = self.sorted_selected_items
        for item in items:
            item.addtag('bound_check')
        bbox = self.canvas.bbox('bound_check') or items[0].coords()
        ref_x, ref_y = bbox[:2]
        self.canvas.dtag('bound_check', 'bound_check')
        return [item.serialize(ref_x, ref_y) for item in items]

    def copy_items(self):
        if self.selected_items:
            self._clipboard = self._get_copy_data()

    def cut_items(self):
        if self.selected_items:
            self.copy_items()
            self.delete_items()

    def duplicate_items(self):
        if self.selected_items:
            self.paste_items(self._get_copy_data())

    def paste_items(self, _clipboard=None):
        _clipboard = self._clipboard if _clipboard is None else _clipboard
        if _clipboard:
            items = []
            for item_data in _clipboard:
                item = CanvasItem.from_data(self.canvas, item_data, self._latch_pos)
                self.create_item(item.__class__, item=item, silently=True)
                items.append(item)
            # slightly displace latch position for next paste
            self._latch_pos = tuple(map(lambda x: x + 5, self._latch_pos))
            self.studio.new_action(Action(
                lambda _: self.remove_items(items, silently=True),
                lambda _: self.restore_items(items)
            ))

    def delete_items(self):
        self.remove_items(list(self.selected_items))

    def _handle_move(self, item, event):
        if not event.state & EventMask.MOUSE_BUTTON_1:
            # we need mouse button 1 to be down to qualify as a drag
            return
        if getattr(item, '_controller', None) and self.current_draw is None:
            if getattr(item, '_coord_latch', None):
                x0, y0 = item._coord_latch
                x, y = item.canvas.canvasx(event.x), item.canvas.canvasx(event.y)
                item._controller.on_move(x - x0, y - y0)
                item._coord_latch = x, y
            else:
                item._coord_latch = item.canvas.canvasx(event.x), item.canvas.canvasx(event.y)

    def _handle_end(self, item, event):
        if getattr(item, '_coord_latch', None) and self.current_draw is None:
            self.on_layout_change()
        item._coord_latch = None

    def _handle_select(self, item, event):
        if self.current_draw is not None or getattr(item, '_coord_latch', None):
            # if coord_latch has a value then it means we have been dragging
            # an item and the button release means end of drag and not selection
            return
        if event.state & EventMask.CONTROL:
            self.select_item(item, True)
        else:
            self.select_item(item)

    def _draw_dispatch(self, event_type):

        def handler(event):
            drawer = self.draw_map.get(self.current_draw)
            if drawer:
                getattr(drawer, event_type)(event)

        return handler

    def set_draw(self, component):
        self._set_cursor()
        self.current_draw = component

    def _reset_cursor(self):
        self.canvas.configure(cursor=self._cursor)

    def _set_cursor(self):
        if self.item_select.selected:
            self.canvas.configure(cursor="crosshair")
        else:
            self._reset_cursor()

    def _evaluator(self, widget):
        return isinstance(widget, Canvas)

    def set_controller(self, item):
        controller_class = self.controller_map.get(item.__class__)
        if controller_class:
            item._controller = controller_class(item.canvas, self, item)
            return item._controller

    def remove_controller(self, item):
        controller = getattr(item, "_controller", None)
        if controller:
            controller.release()
        item._controller = None

    def selection_changed(self):
        # called when canvas item selection changes
        self.style_group.on_widget_change(self.canvas)

    def _update_selection(self, canvas):
        # update selections from the canvas tree
        if canvas != self.canvas:
            self.studio.select(canvas)
        # call to studio should cause canvas to be selected
        assert self.canvas == canvas
        selected = set(self.selected_items)
        to_select = {node.item for node in canvas._cv_tree.get()}

        # deselect items currently selected that shouldn't be
        for item in selected - to_select:
            self.remove_controller(item)
            self.selected_items.remove(item)

        # select items to be selected that are not yet selected
        for item in to_select - selected:
            controller = self.set_controller(item)
            if not controller:
                return
            self.selected_items.append(item)

        self.selection_changed()

    def _clear_selection(self):
        if self.selected_items:
            for item in self.selected_items:
                self.remove_controller(item)
                item.canvas._cv_tree.deselect(item.node)

            self.selected_items.clear()
            self.selection_changed()

    def _deselect(self, item):
        self.remove_controller(item)
        self.selected_items.remove(item)
        item.canvas._cv_tree.deselect(item.node)

    def deselect_items(self, items):
        # only consider selected items
        items = set(items) & set(self.selected_items)
        if items:
            for item in items:
                if item in self.selected_items:
                    self._deselect(item)
            self.selection_changed()

    def select_item(self, item, multi=False):
        if multi:
            if item in self.selected_items:
                self._deselect(item)
            else:
                controller = self.set_controller(item)
                if not controller:
                    return
                self.selected_items.append(item)
                item.node.select(silently=True)
        else:
            for i in self.selected_items:
                if i == item:
                    continue
                self.remove_controller(i)
                i.canvas._cv_tree.deselect(i.node)
            if item in self.selected_items:
                self.selected_items = [item]
            elif self.set_controller(item):
                self.selected_items = [item]
                item.node.select(silently=True)

        self.selection_changed()

    def on_select(self, widget):
        if self.canvas == widget:
            return
        if self.canvas is not None:
            self._reset_cursor()
            self.release(self.canvas)
        if isinstance(widget, Canvas):
            self.canvas = widget
            self._cursor = widget["cursor"]
            self._set_cursor()
            self.initialize_canvas()
        else:
            if self.canvas is None:
                return
            self.release(self.canvas)
            self.canvas = None

    def release(self, canvas):
        if canvas is None or not getattr(canvas, "_cv_initialized", False):
            return
        self._clear_selection()

    def on_layout_change(self):
        prev_data = {item: item._coord_restore for item in self.selected_items}
        data = {item: item.coords() for item in self.selected_items}
        for item in self.selected_items:
            item._coord_restore = item.coords()
        self.studio.new_action(Action(
            lambda _: self.restore_layouts(prev_data),
            lambda _: self.restore_layouts(data)
        ))

    def restore_layouts(self, data):
        for item in data:
            item.coords(*data[item])
            if item._controller:
                item._controller.update()

    def on_item_added(self, item):
        item._coord_restore = item.coords()

    def on_items_modified(self, items):
        for item in items:
            item.node.widget_modified(item)

    def on_widget_delete(self, widget):
        if isinstance(widget, Canvas):
            if widget in self.items:
                self.items.remove(widget)

    def propagate_move(self, delta_x, delta_y, source=None):
        for item in self.selected_items:
            if item != source:
                item._controller.on_move(delta_x, delta_y, True)
