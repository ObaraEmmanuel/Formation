# ======================================================================= #
# Copyright (C) 2021 Hoverset Group.                                      #
# ======================================================================= #

import abc

__all__ = (
    "CANVAS_PROPERTIES",
    "CANVAS_ITEMS",
    "CanvasItem",
    "Arc",
    "Bitmap",
    "Image",
    "Line",
    "Oval",
    "Polygon",
    "Rectangle",
    "Text",
    "Window"
)

CANVAS_PROPERTIES = {
    "activebitmap": {
        "display_name": "active bitmap",
        "type": "bitmap",
        "name": "activebitmap"
    },
    "_activedash": {
        "display_name": "active dash",
        "type": "",
        "name": "activedash"
    },
    "activefill": {
        "display_name": "active fill",
        "type": "color",
        "name": "activefill"
    },
    "activeimage": {
        "display_name": "active image",
        "type": "image",
        "name": "activeimage"
    },
    "activeoutline": {
        "display_name": "active outline",
        "type": "color",
        "name": "activeoutline"
    },
    "activeoutlinestipple": {
        "display_name": "active outline stipple",
        "type": "bitmap",
        "name": "activeoutlinestipple"
    },
    "activestipple": {
        "display_name": "active stipple",
        "type": "bitmap",
        "name": "activestipple"
    },
    "activewidth": {
        "display_name": "active width",
        "type": "dimension",
        "units": "pixels",
        "name": "activewidth"
    },
    "_angle": {
        "display_name": "angle",
        "type": "",
        "name": "angle"
    },
    "arrow": {
        "display_name": "arrow",
        "type": "choice",
        "options": ("none", "first", "last", "both"),
        "name": "arrow"
    },
    "_arrowshape": {
        "display_name": "arrow shape",
        "type": "",
        "name": "arrowshape"
    },
    "capstyle": {
        "display_name": "cap style",
        "type": "choice",
        "options": ("", "butt", "projecting", "round"),
        "name": "capstyle"
    },
    "_dash": {
        "display_name": "dash",
        "type": "",
        "name": "dash"
    },
    "dashoffset": {
        "display_name": "dash offset",
        "type": "dimension",
        "units": "pixels",
        "name": "dashoffset"
    },
    "disabledbitmap": {
        "display_name": "disabled bitmap",
        "type": "bitmap",
        "name": "disabledbitmap"
    },
    "_disableddash": {
        "display_name": "disabled dash",
        "type": "",
        "name": "disableddash"
    },
    "disabledfill": {
        "display_name": "disabled fill",
        "type": "color",
        "name": "disabledfill"
    },
    "disabledimage": {
        "display_name": "disabled image",
        "type": "image",
        "name": "disabledimage"
    },
    "disabledoutline": {
        "display_name": "disabled outline",
        "type": "color",
        "name": "disabledoutline"
    },
    "disabledoutlinestipple": {
        "display_name": "disabled outline stipple",
        "type": "bitmap",
        "name": "disabledoutlinestipple"
    },
    "disabledstipple": {
        "display_name": "disabled stipple",
        "type": "bitmap",
        "name": "disabledstipple"
    },
    "disabledwidth": {
        "display_name": "disabled width",
        "type": "dimension",
        "units": "pixels",
        "name": "disabledwidth"
    },
    "_extent": {
        "display_name": "extent",
        "type": "",
        "name": "extent"
    },
    "fill": {
        "display_name": "fill",
        "type": "color",
        "name": "fill"
    },
    "height": {
        "display_name": "height",
        "type": "dimension",
        "units": "pixels",
        "name": "height"
    },
    "joinstyle": {
        "display_name": "join style",
        "type": "choice",
        "options": ("", "round", "bevel", "miter"),
        "name": "joinstyle"
    },
    "_offset": {
        "display_name": "offset",
        "type": "",
        "name": "offset"
    },
    "outline": {
        "display_name": "outline",
        "type": "color",
        "name": "outline"
    },
    "_outlineoffset": {
        "display_name": "outline offset",
        "type": "",
        "name": "outlineoffset"
    },
    "outlinestipple": {
        "display_name": "outline stipple",
        "type": "bitmap",
        "name": "outlinestipple"
    },
    "smooth": {
        "display_name": "smooth",
        "type": "boolean",
        "name": "smooth"
    },
    "splinesteps": {
        "display_name": "spline steps",
        "type": "number",
        "name": "splinesteps"
    },
    "_start": {
        "display_name": "start",
        "type": "",
        "name": "start"
    },
    "stipple": {
        "display_name": "stipple",
        "type": "bitmap",
        "name": "stipple"
    },
    "style": {
        "display_name": "style",
        "type": "choice",
        "options": ("pieslice", "arc", "chord"),
        "name": "style"
    },
    "tags": {
        "display_name": "tags",
        "type": "text",
        "name": "tags"
    },
    "width": {
        "display_name": "width",
        "type": "dimension",
        "units": "pixels",
        "name": "width"
    },
    "_window": {
        "display_name": "window",
        "type": "",
        "name": "window"
    }
}


class CanvasItem(abc.ABC):
    OVERRIDES = {}
    icon = "canvas"
    display_name = "Item"

    def __init__(self, canvas, *args, **options):
        self.canvas = canvas
        self._id = self._create(*args, **options)
        self.name = ""
        # tree node associated with widget
        self.node = None

    def configure(self, option=None, **options):
        return self.canvas.itemconfigure(self._id, option, **options)

    config = configure

    def coords(self, *args):
        return self.canvas.coords(self._id, *args)

    def bind(self, sequence=None, function=None, add=None):
        return self.canvas.tag_bind(self._id, sequence, function, add)

    def unbind(self, sequence, func_id=None):
        return self.canvas.tag_unbind(self._id, sequence, func_id)

    def lower(self, below_this):
        return self.canvas.tag_lower(self._id, below_this)

    def lift(self, above_this):
        return self.canvas.tag_raise(self._id, above_this)

    def move(self, x_amount, y_amount):
        self.canvas.move(self._id, x_amount, y_amount)

    @abc.abstractmethod
    def _create(self, *args, **options):
        pass


class Arc(CanvasItem):
    icon = "arc"
    display_name = "Arc"

    def __init__(self, canvas, x0, y0, x1, y1, **options):
        super(Arc, self).__init__(canvas, x0, y0, x1, y1, **options)

    def _create(self, *args, **options):
        return self.canvas.create_arc(*args, **options)


class Bitmap(CanvasItem):
    icon = "bitmap"
    display_name = "Bitmap"

    def __init__(self, canvas, x, y, **options):
        super(Bitmap, self).__init__(canvas, x, y, **options)

    def _create(self, *args, **options):
        return self.canvas.create_bitmap(*args, **options)


class Image(CanvasItem):
    icon = "image_dark"
    display_name = "Image"

    def __init__(self, canvas, x, y, **options):
        super(Image, self).__init__(canvas, x, y, **options)

    def _create(self, *args, **options):
        return self.canvas.create_image(*args, **options)


class Line(CanvasItem):
    icon = "line"
    display_name = "Line"

    def __init__(self, canvas, x0, y0, x1, y1, *args, **options):
        super(Line, self).__init__(canvas, x0, y0, x1, y1, *args, **options)

    def _create(self, *args, **options):
        return self.canvas.create_line(*args, **options)


class Oval(CanvasItem):
    icon = "oval"
    display_name = "Oval"

    def __init__(self, canvas, x0, y0, x1, y1, **options):
        super(Oval, self).__init__(canvas, x0, y0, x1, y1, **options)

    def _create(self, *args, **options):
        return self.canvas.create_oval(*args, **options)


class Polygon(CanvasItem):
    icon = "polygon"
    display_name = "Polygon"

    def __init__(self, canvas, x0, y0, x1, y1, *args, **options):
        super(Polygon, self).__init__(canvas, x0, y0, x1, y1, *args, **options)

    def _create(self, *args, **options):
        return self.canvas.create_polygon(*args, **options)


class Rectangle(CanvasItem):
    icon = "rectangle"
    display_name = "Rectangle"

    def __init__(self, canvas, x0, y0, x1, y1, **options):
        super(Rectangle, self).__init__(canvas, x0, y0, x1, y1, **options)

    def _create(self, *args, **options):
        return self.canvas.create_rectangle(*args, **options)


class Text(CanvasItem):
    icon = "canvas_text"
    display_name = "Text"

    def __init__(self, canvas, x, y, **options):
        super(Text, self).__init__(canvas, x, y, **options)

    def _create(self, *args, **options):
        return self.canvas.create_text(*args, **options)


class Window(CanvasItem):
    icon = "window"
    display_name = "Window"

    def __init__(self, canvas, x, y, **options):
        super(Window, self).__init__(canvas, x, y, **options)

    def _create(self, *args, **options):
        return self.canvas.create_window(*args, **options)


CANVAS_ITEMS = (
    Arc, Bitmap, Image, Line, Oval, Polygon, Rectangle, Text
)
