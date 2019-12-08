from hoverset.ui import widgets
from hoverset.ui.icons import get_icon
from hoverset.util.validators import numeric_limit
from .widgets import LabelCombo, LabelSpinBox
from .base import BaseComponent

import math
import functools
from threading import Thread
from PIL import Image


def threaded(func):

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        thread = Thread(target=func, args=args, kwargs=kwargs)
        if hasattr(func, "thread"):
            prev_thread = func.thread
            func.thread = thread
            prev_thread.join()
            thread.start()
        else:
            func.thread = thread
            thread.start()

    return wrap


def register_start(func):
    """
    Decorator for all methods that are registered to be called by the Motion event in CropAndResize class for the
    purposes of drag resize and drag movement. Warning! This decorator is tailored for use by only the CropAndResize
    class.
    :param func:
    :return:
    """

    @functools.wraps(func)
    def handler(self, event, register, *args, **kwargs):
        if register:
            self.resize_function = func
            self.canvas.update_idletasks()
            self.bbox_on_click = self.canvas.bbox("crop_rec")
            self.pos_on_click = self.pos_cache = event
        else:
            func(self, event, register, *args, **kwargs)

    return handler


class CropAndResize(BaseComponent, widgets.Frame):
    RADIUS = 5
    OUTLINE = 3
    ASPECT_RATIOS = {
        "None": None,
        "1:1 Square": (1, 1),
        "3:2": (3, 2),
        "4:3": (4, 3),
        "7:5": (7, 5),
        "10:8": (10, 8),
    }

    DIMENSIONS = {
        "None": None,
    }

    def __init__(self, component):
        super().__init__(component)
        self.app = component.app
        self.canvas = component.app.canvas
        self.config(self.style.dark)
        title = widgets.Label(self, **self.style.dark_text_accent_1, text="Crop", anchor='w')
        self.columnconfigure(0, minsize=145)
        self.columnconfigure(1, minsize=145)
        title.grid(row=0, column=0, columnspan=2, sticky='w', pady=5)
        crop = widgets.Button(self, **self.style.dark_text, **self.style.dark_highlight_passive, height=30,
                              text=get_icon("crop_resize") + " Crop")
        crop.grid(row=1, column=0, columnspan=1, sticky='ew', padx=1)
        crop.on_click(lambda *_: self.draw_crop())
        cancel_crop = widgets.Button(self, **self.style.dark_text, **self.style.dark_highlight_passive, height=30,
                                     text=get_icon("close") + " Cancel")
        cancel_crop.grid(row=1, column=1, sticky='ew', padx=1)
        cancel_crop.on_click(lambda *_: self.cancel_cropping())

        # -------------------------------------------- crop details ----------------------------------------------

        self.crop_details = widgets.Frame(self, **self.style.dark)
        self.crop_details.columnconfigure(0, minsize=145)
        self.crop_details.columnconfigure(1, minsize=145)
        self.aspect = LabelCombo(self.crop_details)
        self.aspect.set_values(list(self.ASPECT_RATIOS.keys()))
        self.aspect.grid(row=0, column=0, columnspan=2, sticky='ew', padx=1, pady=5)
        self.aspect.label.config(text="Aspect ratio", anchor="w")
        self.aspect.readonly()
        self.aspect.set("None")
        self.size = LabelCombo(self.crop_details)
        self.size.set_values(list(self.DIMENSIONS.keys()))
        self.size.grid(row=1, column=0, columnspan=2, sticky='ew', padx=1, pady=5)
        self.size.readonly()
        self.size.set("None")
        self._width = LabelSpinBox(self.crop_details)
        self._width.entry.config(width=5)
        self._width.grid(row=2, column=0, padx=1, pady=5)
        self._width.set_label("width")
        self._width.align_label("left")
        self._height = LabelSpinBox(self.crop_details)
        self._height.entry.config(width=5)
        self._height.grid(row=2, column=1, padx=1, pady=5)
        self._height.set_label("height")
        self._height.align_label("left")
        self.size.label.config(text="Dimensions", anchor="w")
        self.pack(side="top", fill="x", padx=5)
        self.nw, self.ne, self.se, self.sw = None, None, None, None
        self._bbox_on_click = None
        self.resize_function = None
        self.pos_on_click = None
        self.canvas.bind("<Motion>", self.resize)
        self.canvas.bind("<ButtonRelease>", self.clear_resize)
        self.pos_cache = None
        self.position_ratios = None
        self.crop_box_active = False

    @property
    def bbox_on_click(self, ):
        return self._bbox_on_click

    @bbox_on_click.setter
    def bbox_on_click(self, bbox=None):
        # We need to apply outline corrections every time the global bbox value is set to a value other than None
        self._bbox_on_click = bbox
        if bbox is not None:
            self._bbox_on_click = self.correct_outline(bbox)

    def resize(self, event):
        if self.resize_function:
            self.resize_function(self, event)

    def clear_resize(self, *_):
        # Clear all global resize functions and reset the resize function so that the motion event can't update
        # The crop box anymore
        self.resize_function = None
        self.bbox_on_click = None
        self.pos_on_click = None
        self.pos_cache = None

    def draw_crop(self, bbox=None):
        if self.crop_box_active:
            return
        radius = 5
        canvas = self.canvas
        x1, y1, x2, y2 = self.app.image_bounds() if bbox is None else bbox
        canvas.create_rectangle(x1, y1, x2, y2, tags=("crop", "crop_rec"), fill='', outline="#3d8aff",
                                width=self.OUTLINE)
        circle_options = {"tags": ("crop", "crop_circle"), "fill": "#3d8aff", "width": 0}
        self.nw = canvas.create_oval(x1 - radius, y1 - radius, x1 + radius, y1 + radius, **circle_options)
        self.ne = canvas.create_oval(x2 - radius, y1 - radius, x2 + radius, y1 + radius, **circle_options)
        self.sw = canvas.create_oval(x1 - radius, y2 - radius, x1 + radius, y2 + radius, **circle_options)
        self.se = canvas.create_oval(x2 - radius, y2 - radius, x2 + radius, y2 + radius, **circle_options)
        canvas.tag_bind("crop_circle", "<Enter>", lambda *_: canvas.config(cursor="circle"))
        canvas.tag_bind("crop_rec", "<Enter>", lambda *_: canvas.config(cursor="fleur"))
        canvas.tag_bind("crop", "<Leave>", lambda *_: canvas.config(cursor="arrow"))
        # Register resize functions on mouse button press
        canvas.tag_bind(self.ne, "<ButtonPress>", lambda e: self.ne_resize(e, True))
        canvas.tag_bind(self.nw, "<ButtonPress>", lambda e: self.nw_resize(e, True))
        canvas.tag_bind(self.se, "<ButtonPress>", lambda e: self.se_resize(e, True))
        canvas.tag_bind(self.sw, "<ButtonPress>", lambda e: self.sw_resize(e, True))
        canvas.tag_bind("crop_rec", "<ButtonPress>", lambda e: self.move(e, True))
        self.crop_box_active = True
        self.update_ui()
        # We need to redraw so as to initialize the position ratios
        self.redraw(self.app.image_bounds())

    @register_start
    def ne_resize(self, event=None):
        x1, *_, y2 = self.bbox_on_click
        x2 = max(min(self.app.image_bounds()[2], event.x), x1 + 40)
        y1 = min(max(self.app.image_bounds()[1], event.y), y2 - 40)
        self.redraw((x1, y1, x2, y2))

    @register_start
    def nw_resize(self, event=None):
        *_, x2, y2 = self.bbox_on_click
        x1 = min(max(self.app.image_bounds()[0], event.x), x2 - 40)
        y1 = min(max(self.app.image_bounds()[1], event.y), y2 - 40)
        self.redraw((x1, y1, x2, y2))

    @register_start
    def sw_resize(self, event=None):
        _, y1, x2, _ = self.bbox_on_click
        x1 = min(max(self.app.image_bounds()[0], event.x), x2 - 40)
        y2 = max(min(self.app.image_bounds()[3], event.y), y1 + 40)
        self.redraw((x1, y1, x2, y2))

    @register_start
    def se_resize(self, event=None):
        x1, y1, *_ = self.bbox_on_click
        x2 = max(min(self.app.image_bounds()[2], event.x), x1 + 40)
        y2 = max(min(self.app.image_bounds()[3], event.y), y1 + 40)
        self.redraw((x1, y1, x2, y2))

    @register_start
    def move(self, event=None):
        # We will use the small change approach. We detect the small change in cursor position then map this
        # difference to the crop box.
        # Update the position cache with the new position so that we can calculate the subsequent small change
        bounds = self.app.image_bounds()
        if self.pos_cache is not None:
            # noinspection DuplicatedCode
            delta_x, delta_y = event.x - self.pos_cache.x, event.y - self.pos_cache.y
            x1, y1, x2, y2 = self.bbox_on_click
            # We need to ensure the crop box does not go beyond the image on both the x and y axis
            delta_x = 0 if x1 + delta_x < bounds[0] or x2 + delta_x > bounds[2] else delta_x
            delta_y = 0 if y1 + delta_y < bounds[1] or y2 + delta_y > bounds[3] else delta_y
            self.redraw((x1 + delta_x, y1 + delta_y, x2 + delta_x, y2 + delta_y))
            self.pos_cache = event  # Update the cache
            self.canvas.update_idletasks()
            self.bbox_on_click = self.canvas.bbox("crop_rec")  # Update the bound box as well!

    def cancel_cropping(self):
        # Delete all cropping-elements from the canvas
        self.app.canvas.delete("crop")
        self.crop_box_active = False
        self.update_ui()

    def redraw(self, bbox):
        # Update the bounding box position and size
        bound = self.app.image_bounds()
        x1, y1, x2, y2 = bbox
        radius = self.RADIUS
        self.canvas.coords("crop_rec", x1, y1, x2, y2)
        self.canvas.coords(self.nw, x1 - radius, y1 - radius, x1 + radius, y1 + radius)
        self.canvas.coords(self.sw, x1 - radius, y2 - radius, x1 + radius, y2 + radius)
        self.canvas.coords(self.ne, x2 - radius, y1 - radius, x2 + radius, y1 + radius)
        self.canvas.coords(self.se, x2 - radius, y2 - radius, x2 + radius, y2 + radius)
        # Set restoration ratios just in case the image is re-sized by a window event and we need to scale the crop box
        width, height = self.image_size()
        self.position_ratios = ((x1 - bound[0]) / width,
                                (y1 - bound[1]) / height,
                                (bound[2] - x2) / width,
                                (bound[3] - y2) / height)

    def correct_outline(self, bbox):
        # This method removes the outline error in the crop box bounding box
        # I dont know why but the bbox method can't seem to return the right bounds when outline is included
        # Subtracting one stabilises bounding box calculations!
        pad = self.OUTLINE - 1
        return bbox[0] + pad, bbox[1] + pad, bbox[2] - pad, bbox[3] - pad

    def image_size_changed(self):
        # Scale the crop box if image size is changed
        self.lock_size()
        bound = self.app.image_bounds()
        if self.crop_box_active:
            ratios = self.position_ratios
            width, height = self.image_size()
            self.redraw((bound[0] + width * ratios[0],
                         bound[1] + height * ratios[1],
                         bound[2] - width * ratios[2],
                         bound[3] - height * ratios[3]))

    def image_size(self):
        bounds = self.app.image_bounds()
        return bounds[2] - bounds[0], bounds[3] - bounds[1]

    def lock_size(self):
        size = self.image_size()
        self._width.entry.set_validator(numeric_limit, 0, size[0])
        self._height.entry.set_validator(numeric_limit, 0, size[1])

    def update_ui(self):
        if self.crop_box_active:
            self.crop_details.grid(row=2, column=0, columnspan=2, pady=5, sticky='ew')
            self.lock_size()
        else:
            self.crop_details.grid_forget()


class Rotation(BaseComponent, widgets.Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.app = master.app
        self.config(self.style.dark, height=30)
        widgets.Label(self, **self.style.dark_text_accent_1, text="Rotation", anchor='w').pack(side="top", fill="x",
                                                                                               pady=5)
        frame_rotate = widgets.Frame(self, height=30, **self.style.dark)
        self._straighten = widgets.HorizontalScale(self, height=30)
        self._straighten.config_scale(from_=-50, to=50, command=self.on_straighten_change)
        self._straighten.config_all(**self.style.dark_text)
        self._straighten.config_label(text="Straighten")
        self._straighten.pack(side="top", fill="x", pady=10)
        self._straighten.scale.bind("<ButtonPress>", lambda *_: self.app.show_grid())
        self._straighten.scale.bind("<ButtonRelease>", lambda *_: self.app.remove_grid())
        frame_rotate.pack(side="top", fill="x", pady=10)
        self._clockwise = widgets.Button(frame_rotate, **self.style.dark_text, **self.style.dark_highlight_passive,
                                         text=get_icon("rotate_clockwise") + " rotate right")
        self._clockwise.on_click(self.rotate_clockwise)
        self._counter_clockwise = widgets.Button(frame_rotate, **self.style.dark_text,
                                                 **self.style.dark_highlight_passive,
                                                 text=get_icon("rotate_counterclockwise") + " rotate left")
        self._counter_clockwise.on_click(self.rotate_counter_clockwise)
        self._clockwise.place(relx=0.51, y=0, relwidth=0.49, relheight=1)
        self._counter_clockwise.place(relx=0.01, y=0, relwidth=0.49, relheight=1)
        flip_frame = widgets.Frame(self, height=30, **self.style.dark)
        flip_frame.pack(side="top", fill="x", pady=10)
        self._flip_horizontal = widgets.Button(flip_frame, **self.style.dark_text,
                                               **self.style.dark_highlight_passive,
                                               text=get_icon("flip_horizontal") + " Flip horizontal")
        self._flip_horizontal.on_click(self.flip_horizontal)
        self._flip_vertical = widgets.Button(flip_frame, **self.style.dark_text,
                                             **self.style.dark_highlight_passive,
                                             text=get_icon("flip_vertical") + " Flip Vertical")
        self._flip_vertical.on_click(self.flip_vertical)
        self._flip_horizontal.place(relx=0.51, y=0, relwidth=0.49, relheight=1)
        self._flip_vertical.place(relx=0.01, y=0, relwidth=0.49, relheight=1)
        self.pack(side="top", fill="x", padx=5)
        self.image = self.app.image

    def rotate_clockwise(self, *_):
        self.image = self.image.rotate(-90, 0, 1)
        self.apply_straightening(self._straighten.get())

    def flip_horizontal(self, *_):
        self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
        # We need to reverse the straightening
        # No need to apply_straightening as setting a value automatically does this
        self._straighten.set(-self._straighten.get())

    def flip_vertical(self, *_):
        self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
        self.apply_straightening(self._straighten.get())

    def rotate_counter_clockwise(self, *_):
        self.image = self.image.rotate(90, 0, 1)
        self.apply_straightening(self._straighten.get())

    def on_straighten_change(self, *_):
        self._straighten.config_value(text="{}°".format(int(self._straighten.get())))
        self.apply_straightening(self._straighten.get())

    def apply_straightening(self, degrees):
        degrees = int(degrees)
        # Perform straightening based on the tilt in degrees
        image = self.image
        # For straightening to work we have to be in a landscape setup_widget. If not we enforce so by rotating by 90
        width, height = image.size
        is_portrait = height > width
        if is_portrait:
            image = image.rotate(90, 0, 1)
        width, height = image.size
        ratio = width / height
        # Calculate the required scaling to ensure even on tilting the image fits the view port
        delta_w = math.ceil(height * math.sin(math.radians(abs(degrees))))
        delta_h = math.ceil(width * math.sin(math.radians(abs(degrees))))
        # Apply scaling then rotate image by degrees
        image = image.resize(self.match_aspect((width + delta_w, height + delta_h), ratio),
                             Image.ANTIALIAS).rotate(degrees, 0, 1)
        # Determine the cropping bbox values
        padding_w = round((image.width - width) / 2)
        padding_h = round((image.height - height) / 2)
        image = image.crop((padding_w, padding_h, padding_w + width, padding_h + height))
        # If we performed rotation by 90 we need to reverse it.
        if is_portrait:
            image = image.rotate(-90, 0, 1)
        self.app.update_render(image)

    def match_aspect(self, size: (int, int), ratio=None) -> (int, int):
        # It so happens that straightening returns a size that does not match the aspect ratio
        # So we pick the _height and generate the _width based on the aspect ratio
        if ratio is None:
            ratio = self.image.width / self.image.height
        return round(size[1] * ratio), size[1]


class SizingComponent(BaseComponent, widgets.Frame):
    ICON = get_icon("crop_resize")
    DESCRIPTION = "Size options"

    def __init__(self, app):
        super().__init__(app.control.body)
        self.config(self.style.dark)
        self.app = app
        self.selector = None

        #  ================== set up sub components ==================
        self.components = (
            Rotation(self),
            CropAndResize(self),
        )

    def image_size_changed(self):
        for component in self.components:
            component.image_size_changed()
