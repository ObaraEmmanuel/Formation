# ======================================================================= #
# Copyright (C) 2021 Hoverset Group.                                      #
# ======================================================================= #
import abc
from collections import defaultdict

from hoverset.ui.widgets import EventMask

from studio.tools._base import BaseTool
from studio.feature.components import ComponentPane, SelectToDrawGroup
from studio.lib.canvas import *
from studio.lib.legacy import Canvas


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
        self._dragging = False
        self._id = canvas.create_oval(
            x-self.radius, y-self.radius, x+self.radius, y+self.radius,
            fill="red", tags=("coordinate", "controller")
        )
        canvas.tag_bind(self._id, "<ButtonPress-1>", self._start_drag)
        canvas.tag_bind(self._id, "<ButtonRelease-1>", self._end_drag)
        canvas.tag_bind(self._id, "<Motion>", self._drag)
        canvas.tag_bind(self._id, "<Enter>", lambda _: self.grow_effect())
        canvas.tag_bind(self._id, "<Leave>", lambda _: self.grow_effect(True))
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

    def _start_drag(self, _):
        self._dragging = True

    def retire(self):
        # remove from view without deleting
        self.place(-50, -50)
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
        self.place(x, y)
        self.active.add(self)

    def _drag(self, event):
        if not self._dragging:
            return
        self.x = self.canvas.canvasx(event.x)
        self.y = self.canvas.canvasy(event.y)
        self.place()
        self.controller.on_coord_change(self)

    def _end_drag(self, _):
        self._dragging = False
        self.controller.on_release()

    @classmethod
    def acquire(cls, canvas, controller, x, y):
        if len(cls.pool[canvas]):
            coord = cls.pool[canvas][0]
            cls.pool[canvas].remove(coord)
            coord.revive(controller, x, y)
            return coord
        else:
            return cls(canvas, controller, x, y)


class Link:
    pool = defaultdict(list)
    active = set()

    def __init__(self, canvas, controller, coord1, coord2):
        self.canvas = canvas
        self.controller = controller
        self._dragging = False
        self._id = canvas.create_line(
            coord1.x, coord1.y, coord2.x, coord2.y,
            fill="red", tag=("link", "controller"), dash=(5, 4), width=2
        )
        self.link_coord(coord1, coord2)
        canvas.tag_bind(self._id, "<ButtonPress-1>", self._start_drag)
        canvas.tag_bind(self._id, "<ButtonRelease-1>", self._end_drag)
        canvas.tag_bind(self._id, "<Motion>", self._drag)
        self.active.add(self)
        self._coord_latch = 0, 0

    def _to_canvas_coord(self, x, y):
        return self.canvas.canvasx(x), self.canvas.canvasy(y)

    def _start_drag(self, event):
        self._coord_latch = self._to_canvas_coord(event.x, event.y)
        self._dragging = True

    def _drag(self, event):
        if not self._dragging:
            return
        x, y = self._to_canvas_coord(event.x, event.y)
        xl, yl = self._coord_latch
        self.controller.on_move(x-xl, y-yl)
        self._coord_latch = x, y

    def _end_drag(self, _):
        self.controller.on_release()
        self._dragging = False

    def place(self, coord1, coord2):
        self.canvas.coords(self._id, coord1.x, coord1.y, coord2.x, coord2.y)
        self.canvas.tag_lower(self._id, "coordinate")

    def link_coord(self, coord1, coord2):
        coord1.add_listener(self.coord_changed)
        coord2.add_listener(self.coord_changed)
        self.coord1 = coord1
        self.coord2 = coord2
        self.place(coord1, coord2)

    def revive(self, controller, coord1, coord2):
        self.controller = controller
        self.link_coord(coord1, coord2)
        self.active.add(self)

    def retire(self):
        # remove from view without deleting
        self.canvas.coords(self._id, -50, -50, -50, -50)
        self.pool["canvas"].append(self)
        self._listeners = []

    def coord_changed(self):
        self.place(self.coord1, self.coord2)

    @classmethod
    def acquire(cls, canvas, controller, coord1, coord2):
        if len(cls.pool[canvas]):
            coord = cls.pool[canvas][0]
            cls.pool[canvas].remove(coord)
            coord.revive(controller, coord1, coord2)
            return coord
        else:
            return cls(canvas, controller, coord1, coord2)


class Controller(abc.ABC):

    def __init__(self, canvas, tool, item=None, **kw):
        self.canvas = canvas
        self.tool = tool
        self.item = item
        self._on_change = None
        self.coords = []
        self.links = []

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda item: func(item, *args, **kwargs)

    def _change(self):
        if self._on_change:
            self._on_change(self.item)

    def highlight(self, item):
        self.item = item
        item.lower("controller")

    @abc.abstractmethod
    def get_coords(self):
        pass

    def on_coord_change(self, coord):
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

    def on_coord_change(self, coord):
        self.item.coords(self.get_coords())
        self._change()

    def get_coords(self):
        return [coord for c in self.coords for coord in (c.x, c.y)]

    def highlight(self, item):
        coords = item.coords()
        self.release()
        prev = Coordinate.acquire(self.canvas, self, *coords[:2])
        self.coords.append(prev)
        for i in range(2, len(coords), 2):
            # just in case the length of coordinates is odd
            if i+1 >= len(coords):
                break
            cd = Coordinate.acquire(self.canvas, self, coords[i], coords[i+1])
            self.coords.append(cd)
            self.links.append(Link.acquire(self.canvas, self, prev, cd))
            prev = cd

        if self._closed:
            self.links.append(Link.acquire(self.canvas, self, prev, self.coords[0]))


class ClosedLinearController(LinearController):
    _closed = True


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
            self.item = self.tool.create_item(self.tool.current_draw, *self.coords)
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
            self.item = self.tool.create_item(self.tool.current_draw, *self.coords)
        x, y = self.canvas_coord(event.x, event.y)
        # set the last two coordinates
        self.coords[-2:] = [x, y]
        self.item.coords(*self.coords)


class CanvasTool(BaseTool):

    name = "Canvas"
    icon = "paint"

    def __init__(self, studio, manager):
        super(CanvasTool, self).__init__(studio, manager)
        self._component_pane: ComponentPane = self.studio.get_feature(ComponentPane)
        self.item_select = self._component_pane.register_group(
            "Canvas", CANVAS_ITEMS, SelectToDrawGroup, self._evaluator
        )
        self.items = defaultdict(list)
        self.item_select.on_select(self.set_draw)
        self.canvas = None
        self._cursor = "arrow"
        self.current_draw = None
        self.selected_items = []

        self.square_draw = SquareDraw(self)
        self.line_draw = LinearDraw(self)

        self.draw_map = {
            Oval: self.square_draw,
            Rectangle: self.square_draw,
            Arc: self.square_draw,
            Line: self.line_draw,
            Polygon: self.line_draw
        }

        self.controller_map = {
            Oval: SquareController,
            Rectangle: SquareController,
            Arc: SquareController,
            Line: LinearController,
            Polygon: ClosedLinearController
        }

    def initialize_canvas(self):
        if self.canvas and not getattr(self.canvas, "_cv_initialized", False):
            self.canvas.bind(
                "<ButtonPress-1>", self._draw_dispatch("on_button_press"), True)
            self.canvas.bind(
                "<ButtonRelease>", self._draw_dispatch("on_button_release"), True)
            self.canvas.bind(
                "<Double-Button-1>", self._draw_dispatch("on_double_press"), True)
            self.canvas.bind(
                "<Motion>", self._draw_dispatch("on_motion"), True)
            self.canvas._cv_initialized = True

    def create_item(self, component, *args):
        item = component(self.canvas, *args)
        self.items[self.canvas].append(item)
        item.bind("<Button-1>", self._handle_select(item), True)
        return item

    def _handle_select(self, item):

        def handler(event):
            if self.current_draw is not None:
                return
            if event.state & EventMask.CONTROL:
                self.select_item(item, True)
            else:
                self.select_item(item)

        return handler

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

    def select_item(self, item, multi=False):
        if multi:
            if item in self.selected_items:
                self.remove_controller(item)
                self.selected_items.remove(item)
            else:
                controller = self.set_controller(item)
                if not controller:
                    return
                self.selected_items.append(item)
        else:
            for i in self.selected_items:
                if i == item:
                    continue
                self.remove_controller(i)
            if item in self.selected_items:
                self.selected_items = [item]
            elif self.set_controller(item):
                self.selected_items = [item]

    def on_select(self, widget):
        if self.canvas == widget:
            return
        if self.canvas is not None:
            self._reset_cursor()
        if isinstance(widget, Canvas):
            self.canvas = widget
            self._cursor = widget["cursor"]
            self._set_cursor()
            self.initialize_canvas()
        else:
            self.canvas = None

    def on_layout_change(self):
        pass

    def on_item_added(self, item):
        pass

    def propagate_move(self, delta_x, delta_y, source=None):
        for item in self.selected_items:
            if item != source:
                item._controller.on_move(delta_x, delta_y, True)
