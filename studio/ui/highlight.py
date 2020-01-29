import tkinter as tk
from hoverset.ui.widgets import Frame
from hoverset.platform import platform_is, WINDOWS
import studio.ui.geometry as geometry


def resize_cursor() -> tuple:
    r"""
    Returns a tuple of the cursors to be used based on platform
    :return: tuple ("nw_se", "ne_sw") cursors roughly equal to \ and / respectively
    """
    if platform_is(WINDOWS):
        # Windows provides corner resize cursors so use those
        return "size_nw_se", "size_ne_sw"
    else:
        # Use circles for other platforms
        return ("circle",)*2


class HighLight:
    """
    This class is responsible for the Highlight on selected objects on the designer. It allows resizing, moving and
    access to the currently selected widget. It also provides a way to attach listeners for any changes to the
    widgets size and position
    """
    OUTLINE = 2
    SIZER_LENGTH = 6

    def __init__(self, parent):
        self.parent = parent
        self._resize_func = None
        self.bounds = (0, 0, parent.width, parent.height)
        self.pos_on_click = None
        self.pos_cache = None
        self._bbox_on_click = None
        self._on_resize = None
        self._on_release = None
        self._on_move = None
        self.current_obj = None
        self.bind_ids = []

        # These are the handle widgets that acts as guides for resizing and moving objects

        self.l = tk.Frame(parent, bg="#3d8aff", width=self.OUTLINE, cursor="fleur")
        self.r = tk.Frame(parent, bg="#3d8aff", width=self.OUTLINE, cursor="fleur")
        self.t = tk.Frame(parent, bg="#3d8aff", height=self.OUTLINE, cursor="fleur")
        self.b = tk.Frame(parent, bg="#3d8aff", height=self.OUTLINE, cursor="fleur")

        _cursors = resize_cursor()
        self.nw = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH, cursor=_cursors[0])
        self.ne = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH, cursor=_cursors[1])
        self.sw = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH, cursor=_cursors[1])
        self.se = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH, cursor=_cursors[0])
        self.n = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH,
                          cursor="sb_v_double_arrow")
        self.s = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH,
                          cursor="sb_v_double_arrow")
        self.e = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH,
                          cursor="sb_h_double_arrow")
        self.w = tk.Frame(parent, bg="#3d8aff", width=self.SIZER_LENGTH, height=self.SIZER_LENGTH,
                          cursor="sb_h_double_arrow")

        # bind all resizing corners to register their respective resize methods when pressed
        # Any movement events will then call this registered method to ensure the right resize approach
        # is being used.

        self.nw.bind("<ButtonPress>", lambda e: self.set_function(self.nw_resize, e))
        self.ne.bind("<ButtonPress>", lambda e: self.set_function(self.ne_resize, e))
        self.sw.bind("<ButtonPress>", lambda e: self.set_function(self.sw_resize, e))
        self.se.bind("<ButtonPress>", lambda e: self.set_function(self.se_resize, e))
        self.n.bind("<ButtonPress>", lambda e: self.set_function(self.n_resize, e))
        self.s.bind("<ButtonPress>", lambda e: self.set_function(self.s_resize, e))
        self.e.bind("<ButtonPress>", lambda e: self.set_function(self.e_resize, e))
        self.w.bind("<ButtonPress>", lambda e: self.set_function(self.w_resize, e))

        self._elements = [
            self.l, self.r, self.t, self.b, self.nw, self.ne, self.sw, self.se, self.n, self.s, self.e, self.w
        ]

        # ============================================== bindings =====================================================

        # These variables help in skipping of several rendering frames to reduce lag when dragging items
        self._skip_var = 0
        self._skip_max = 2  # The maximum rendering to skip for every one successful render. Ensure its
        # not too big otherwise we won't be moving and resizing items at all
        self.parent.bind("<Motion>", self.resize)
        for elem in self._elements[4:]:
            elem.bind("<Motion>", self.resize)
            elem.bind("<ButtonRelease>", self.clear_resize)
        for elem in self._elements[:4]:
            elem.bind("<ButtonPress>", lambda e: self.set_function(self.move, e))
            elem.bind("<Motion>", self.resize)
            elem.bind("<ButtonRelease>", self.clear_resize)
        self.parent.bind_all("<ButtonRelease>", self.clear_resize)

    @staticmethod
    def bounds_from_object(obj: tk.Misc):
        """
        Generate a bounding box for a widget relative to its parent which can then be used to position the highlight
        or by any other position dependent action.
        :param obj: a tk object
        :return:
        """
        obj.update_idletasks()
        x1 = obj.winfo_x()
        y1 = obj.winfo_y()
        x2 = obj.winfo_width() + x1
        y2 = obj.winfo_height() + y1
        return x1, y1, x2, y2

    def _lift_all(self):
        for elem in self._elements:
            elem.lift()

    def on_resize(self, listener, *args, **kwargs):
        self._on_resize = lambda bounds: listener(bounds, *args, **kwargs)

    def on_release(self, listener, *args, **kwargs):
        self._on_release = lambda bounds: listener(bounds, *args, **kwargs)

    def on_move(self, listener, *args, **kwargs):
        self._on_move = lambda bounds: listener(bounds, *args, **kwargs)

    def resize(self, event):
        # This method is called when the motion event is fired and dispatches the event to the registered resize method
        if self._resize_func:
            if self._skip_var >= self._skip_max:
                # Render frames and begin skip cycle
                self._skip_var = 0
                self._resize_func(self._stabilised_event(event))
            else:
                # Skip rendering frames
                self._skip_var += 1

    def clear_resize(self, *_):
        # Clear all global resize functions and reset the resize function so that the motion event can't update
        # The highlight box anymore
        self._resize_func = None
        self.pos_on_click = None
        self.pos_cache = None
        self._update_bbox()
        if self._on_release is not None:
            self._on_release(self._bbox_on_click)
        self._bbox_on_click = None

    @property
    def bbox_on_click(self):
        # Return the bounding box of the highlight
        return self._bbox_on_click

    def set_function(self, func, event):
        # Registers the method to be called for any drag actions which may include moving and resizing
        self._resize_func = func
        self.pos_on_click = self.pos_cache = self._stabilised_event(event)
        self._update_bbox()
        self.bounds = (0, 0, self.parent.width, self.parent.height)

    def _update_bbox(self):
        # Update the bounding box based on the current position of the highlight
        for elem in self._elements:
            elem.update_idletasks()
        x1 = self.l.winfo_x()
        y1 = self.t.winfo_y()
        x2 = self.r.winfo_x()
        y2 = self.b.winfo_y()
        self._bbox_on_click = geometry.relative_bounds((x1, y1, x2, y2), self.parent)

    def _shrink(self, bounds):
        # return bounds[0] + self.OUTLINE, bounds[1] + self.OUTLINE, bounds[2], bounds[3]
        return bounds

    def _expand(self, bounds):
        # return (bounds[0] - self.OUTLINE, bounds[1] - self.OUTLINE, bounds[2] - self.OUTLINE,
        #         bounds[3] - self.OUTLINE)
        return bounds

    def clear(self):
        """
        Remove the highlight from view. This is temporary and can be reversed by calling the surround method on an
        a widget
        :return:
        """
        for elem in self._elements:
            elem.place_forget()

    def redraw(self, bound, radius=None):
        # Redraw the highlight in the new bounding box
        radius = self.SIZER_LENGTH // 2 if radius is None else radius
        x1, y1, x2, y2 = bound
        width, height = x2 - x1, y2 - y1
        self.l.place(in_=self.parent, x=x1, y=y1, height=y2 - y1)
        self.r.place(in_=self.parent, x=x2, y=y1, height=y2 - y1)
        self.t.place(in_=self.parent, x=x1, y=y1, width=x2 - x1)
        self.b.place(in_=self.parent, x=x1, y=y2, width=x2 - x1)

        self.nw.place(in_=self.parent, x=x1 - radius, y=y1 - radius)
        self.ne.place(in_=self.parent, x=x2 - radius, y=y1 - radius)
        self.sw.place(in_=self.parent, x=x1 - radius, y=y2 - radius)
        self.se.place(in_=self.parent, x=x2 - radius, y=y2 - radius)
        self.n.place(in_=self.parent, x=x1 + width // 2 - radius, y=y1 - radius)
        self.s.place(in_=self.parent, x=x1 + width // 2 - radius, y=y2 - radius)
        self.e.place(in_=self.parent, x=x2 - radius, y=y1 + height // 2 - radius)
        self.w.place(in_=self.parent, x=x1 - radius, y=y1 + height // 2 - radius)

    # ========================================= resize approaches ==========================================

    def ne_resize(self, event=None):
        # perform resize in the north east direction
        x1, *_, y2 = self.bbox_on_click
        x2 = max(min(self.bounds[2], event.x), x1 + 20)
        y1 = min(max(self.bounds[1], event.y), y2 - 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def n_resize(self, event=None):
        # perform resize in the north direction
        x1, _, x2, y2 = self.bbox_on_click
        y1 = min(max(self.bounds[1], event.y), y2 - 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def e_resize(self, event=None):
        # perform resize in the east direction
        x1, y1, _, y2 = self.bbox_on_click
        x2 = max(min(self.bounds[2], event.x), x1 + 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def nw_resize(self, event=None):
        # perform resize in the north west direction
        *_, x2, y2 = self.bbox_on_click
        x1 = min(max(self.bounds[0], event.x), x2 - 20)
        y1 = min(max(self.bounds[1], event.y), y2 - 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def sw_resize(self, event=None):
        # perform resize in the south west direction
        _, y1, x2, _ = self.bbox_on_click
        x1 = min(max(self.bounds[0], event.x), x2 - 20)
        y2 = max(min(self.bounds[3], event.y), y1 + 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def s_resize(self, event=None):
        # perform resize in the south direction
        x1, y1, x2, _ = self.bbox_on_click
        y2 = max(min(self.bounds[3], event.y), y1 + 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def w_resize(self, event=None):
        # perform resize in the west direction
        _, y1, x2, y2 = self.bbox_on_click
        x1 = min(max(self.bounds[0], event.x), x2 - 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    def se_resize(self, event=None):
        # perform resize in the south east direction
        x1, y1, *_ = self.bbox_on_click
        x2 = max(min(self.bounds[2], event.x), x1 + 20)
        y2 = max(min(self.bounds[3], event.y), y1 + 20)
        self.redraw((x1, y1, x2, y2))
        self._on_resize(self._shrink((x1, y1, x2, y2)))

    # =========================================================================================================

    def surround(self, obj):
        """
        Draw the highlight around the object(widget) :param obj
        :param obj: A tk widget
        :return: None
        """
        self.current_obj = obj
        self.redraw(self.bounds_from_object(obj))
        self._update_bbox()
        self._lift_all()

    def adjust_to(self, bound):
        """
        Draw the highlight using the bound :param bound supplied.
        :param bound:
        :return:
        """
        self.redraw(bound)
        self._update_bbox()
        self._lift_all()

    def _stabilised_event(self, event):
        # Since events are bound to the dynamically adjusted handle widgets in the highlight,
        # coordinates for the event object may vary unpredictably.
        # This method attempts to fix that by adjusting the x and y attributes of the event to always
        # be in reference to a static parent widget in this case self.parent
        event.x = event.x_root - self.parent.winfo_rootx()
        event.y = event.y_root - self.parent.winfo_rooty()
        return event

    def move(self, event=None):
        # We will use the small change approach. We detect the small change in cursor position then map this
        # difference to the highlight box.
        # Update the position cache with the new position so that we can calculate the subsequent small change
        bounds = (0, 0, self.parent.width, self.parent.height)
        if self.pos_cache is not None:
            delta_x, delta_y = event.x - self.pos_cache.x, event.y - self.pos_cache.y
            x1, y1, x2, y2 = self.bbox_on_click
            # We need to ensure the crop box does not go beyond the image on both the x and y axis
            delta_x = 0 if x1 + delta_x < bounds[0] else delta_x
            delta_y = 0 if y1 + delta_y < bounds[1] else delta_y
            bound = (x1 + delta_x, y1 + delta_y, x2 + delta_x, y2 + delta_y)
            self.redraw(bound)
            self._on_move(bound)
            self.pos_cache = event  # Update the cache
            self._update_bbox()


class WidgetHighlighter:
    OUTLINE = 2

    def __init__(self, master):
        color = master.style.dark_on_hover.get("background", "#3d8aff")
        self.l = tk.Frame(master, bg=color, width=self.OUTLINE)
        self.r = tk.Frame(master, bg=color, width=self.OUTLINE)
        self.t = tk.Frame(master, bg=color, height=self.OUTLINE)
        self.b = tk.Frame(master, bg=color, height=self.OUTLINE)
        self.master = master
        self.elements = (self.l, self.r, self.t, self.b)

    def highlight(self, widget):
        x, y = widget.winfo_rootx() - self.master.winfo_rootx(), widget.winfo_rooty() - self.master.winfo_rooty()
        w, h = widget.winfo_width(), widget.winfo_height()
        self.l.place(x=x, y=y, height=h)
        self.r.place(x=x + w, y=y, height=h)
        self.t.place(x=x, y=y, width=w)
        self.b.place(x=x, y=y + h, width=w)
        for element in self.elements:
            element.lift()

    def clear(self):
        for element in self.elements:
            element.place_forget()


class EdgeIndicator(Frame):
    """
    Generates a conspicuous line at the edges of a widget for various indication purposes
    """

    def __init__(self, master):
        super().__init__(master.window)
        self.config(**self.style.bright_background, height=1)

    def bottom(self, widget):
        widget.update_idletasks()
        x, y = (widget.winfo_rootx() - self.window.winfo_rootx(),
                widget.winfo_rooty() - self.window.winfo_rooty() + widget.winfo_height())
        self.lift()
        self.place(in_=self.window, x=x, y=y, height=1.5, width=widget.winfo_width())

    def top(self, widget):
        widget.update_idletasks()
        x, y = widget.winfo_rootx() - self.window.winfo_rootx(), widget.winfo_rooty() - self.window.winfo_rooty()
        self.lift()
        self.place(in_=self.window, x=x, y=y, height=1.5, width=widget.winfo_width())

    def right(self, widget):
        widget.update_idletasks()
        x, y = (widget.winfo_rootx() - self.window.winfo_rootx() + widget.winfo_width(),
                widget.winfo_rooty() - self.window.winfo_rooty())
        self.lift()
        self.place(in_=self.window, x=x, y=y, height=widget.winfo_height(), width=1.5)

    def left(self, widget):
        widget.update_idletasks()
        x, y = (widget.winfo_rootx() - self.window.winfo_rootx(), widget.winfo_rooty() - self.window.winfo_rooty())
        self.lift()
        self.place(in_=self.window, x=x, y=y, height=widget.winfo_height(), width=1.5)

    def clear(self):
        self.place_forget()
