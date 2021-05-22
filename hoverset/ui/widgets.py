"""

This is the foundation of all GUI components used in hoverset based project.
These widget classes are used in the Formation studio and have special features
such as tkinter styles loaded from css files and available for use anywhere inside them.
All gui manifestation should strictly use hoverset widget set for easy maintenance in the future.
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import functools
import logging
import os
import re
import webbrowser
import tkinter as tk
import tkinter.ttk as ttk
from collections import namedtuple
from tkinter import font

from hoverset.data.images import load_image_to_widget
from hoverset.data.utils import get_resource_path, get_theme_path
from hoverset.platform import platform_is, WINDOWS, LINUX, MAC
from hoverset.ui.animation import Animate, Easing
from hoverset.ui.icons import get_icon_image
from hoverset.ui.styles import StyleDelegator
from hoverset.ui.windows import DragWindow
from hoverset.ui.menu import MenuUtils
import hoverset.ui

__all__ = (
    "Application",
    "Button",
    "Canvas",
    "CenterWindowMixin",
    "Checkbutton",
    "ComboBox",
    "CompoundList",
    "ContextMenuMixin",
    "DragWindow",
    "DrawOver",
    "EditableMixin",
    "Entry",
    "EventMask",
    "EventWrap",
    "FontStyle",
    "Frame",
    "Scale",
    "ImageCacheMixin",
    "Label",
    "LabelFrame",
    "MenuButton",
    "Message",
    "PanedWindow",
    "Popup",
    "PositionMixin",
    "ProgressBar",
    "RadioButton",
    "RadioButtonGroup",
    "Screen",
    "ScrollableInterface",
    "ScrolledFrame",
    "SpinBox",
    "Spinner",
    "TabView",
    "ToggleButton",
    "ToolWindow",
    "TreeView",
    "Text",
    "Widget",
    "WidgetError",
    "Window",
    "WindowMixin",
    "chain",
    "clean_styles",
    "set_ttk_style",
    "system_fonts",
    "suppress_change",
)


class FontStyle(font.Font):
    """
    Hoverset equivalent of :py:class:`tkinter.font.Font` with additional
    functionality

    """

    @staticmethod
    def families(root=None, displayof=None):
        """
        Get font families as tuple
        """
        return font.families(root, displayof)

    @staticmethod
    def nametofont(name):
        """
        Given the name of a tk named font, returns a Font representation.
        """
        try:
            return font.nametofont(name)
        except tk.TclError:
            return None

    @staticmethod
    def names(root=None):
        """
        Get names of defined fonts (as a tuple)
        """
        return font.names(root)


class EventMask:
    """
    Event mask values to be used to test events occurring with these
    states set. For instance, to check whether control button was
    down the following check can be performed

    .. code:: python

        def on_event(event):
            if event.state & EventMask.CONTROL:
                print("Control button pressed")

    .. table::

        ============================  ========================
        Event Mask                    Event status
        ============================  ========================
        EventMask.SHIFT               Shift key down
        EventMask.CAPS_LOCK           Caps lock key down
        EventMask.CONTROL             Control key down
        EventMask.L_ALT               Left Alt key down
        EventMask.NUM_LOCK            Num lock key down
        EventMask.MOUSE_BUTTON_1      Right mouse button down
        EventMask.MOUSE_BUTTON_2      Mouse wheel down
        EventMask.MOUSE_BUTTON_3      Left mouse button down
        ============================  ========================

    """
    SHIFT = 0x0001
    CAPS_LOCK = 0x0002
    CONTROL = 0x0004
    L_ALT = 0x0008
    NUM_LOCK = 0x0010
    R_ALT = 0x0080
    MOUSE_BUTTON_1 = 0x0100
    MOUSE_BUTTON_2 = 0x0200
    MOUSE_BUTTON_3 = 0x0400


# Imitate a tkinter event object for use when handling synthetic events
EventWrap = namedtuple('EventWrap', ['x_root', 'y_root', 'x', 'y'])
EventWrap.__doc__ = """
Imitate a tkinter event object for use when handling synthetic events"""


class WidgetError(tk.TclError):
    """
    Extra errors thrown by hoverset widgets
    """
    pass


def chain(func):
    """
    Decorator function that allows class methods to be chained by implicitly returning the object. Any method
    decorated with this function returns its object.

    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        func(self, *args, **kwargs)
        return self

    return wrap


def set_ttk_style(widget, cnf=None, **styles) -> None:
    """
    Allows you set styles for ttk widgets just like conventional tkinter widgets.
    It bypasses the need to work with ttk styles.
    It is important however to note that unsupported styles will be silently ignored!

    :param widget: A ttk widget
    :param styles: keyword arguments representing conventional tkinter style
    :param cnf: Dictionary of styles to applied
    :return: None
    """
    if cnf is None:
        cnf = {}
    styles.update(cnf)
    ttk_style = ttk.Style()
    # Use hoverset class extension to avoid collision with actual native widgets in use
    orient = "." + str(widget['orient']).title() if 'orient' in widget.keys() else ''
    class_name = 'hover{}.{}'.format(orient, widget.winfo_class())
    ttk_style.configure(class_name, **styles)
    widget.configure(style=class_name)


def config_ttk(widget, cnf=None, **styles) -> None:
    """

    :param widget:
    :param cnf:
    :param styles:
    :return:
    """
    if cnf is None:
        cnf = {}
    styles.update(cnf)
    direct = {i: styles[i] for i in styles.keys() & set(widget.keys())}
    widget.configure(**direct)
    set_ttk_style(
        widget,
        None,
        **{i: styles[i] for i in styles.keys() - direct.keys()})


def clean_styles(widget, styles) -> dict:
    """
    Ensures safety while passing styles to tkinter objects. Normally tkinter objects raise errors for declaring
    styles that are not allowed for a given widget. This function takes in the styles dictionary and removes
    invalid styles for the particular widget returning the cleaned styles dictionary. As a bonus, duplicate definitions
    are overwritten.

    :param widget:
    :param styles:
    :return: dict cleaned_styles
    """
    allowed_styles = widget.config() or {}
    cleaned_styles = {}
    for style in styles:
        if style in allowed_styles:
            cleaned_styles[style] = styles[style]
    return cleaned_styles


def system_fonts():
    """
    A list of all font on the current system

    :return: list of font names
    """
    fonts = sorted(list(font.families()))
    fonts = list(filter(lambda x: not x.startswith("@"), fonts))
    return fonts


def suppress_change(func):
    """
    Wraps a method to prevent it from emitting an on change event. Works with
    the hoverset architecture where objects contain a _on_change attribute
    for the callback fired on change
    """

    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        temp = self._on_change
        self._on_change = None
        func(self, *args, **kwargs)
        self._on_change = temp

    return inner


class EditableMixin:
    """
    This mixin implements all methods applicable to all widgets that allow
    entry of data using the keyboard. All widgets that have such functionality
    should ensure they extend this mixin.
    """

    def set_validator(self, validator, *args, **kwargs) -> None:
        """
        Allows addition of realtime validation of data entered by the
        user to input widgets. This validation is carried out at the
        lowest level before the user interface even displays the value in
        the widget allowing invalid data to be blocked before it is ever
        displayed.

        :param validator: The validation method that accepts one argument
          which is the string to be validated. Such functions can be found
          or added at hoverset.util.validators
        :return: None
        """
        self.configure(
            validate='all',
            validatecommand=(
                self.register(lambda val: validator(val, *args, **kwargs)),
                "%P"
            )
        )

    def on_change(self, callback, *args, **kwargs):
        """
        Set the callback when data in the input widget is changed either
        explicitly or implicitly.

        :param callback:
        :return:
        """
        self._var.trace("w", lambda *_: callback(*args, **kwargs))

    def on_entry(self, callback, *args, **kwargs):
        """
        Set the callback when data in the input widget is changed explicitly
        i.e when the user actually types values into the input widget.

        :param callback:
        :return:
        """
        # Capture typing event
        self.bind("<KeyRelease>", lambda *_: callback(*args, **kwargs))

    def disabled(self, flag):
        """
        Change the state of an editable widget, whether disable or enabled

        :param flag: set to ``True`` to disable and ``False`` to enable
        """
        if flag:
            self.config(state='disabled')
        else:
            self.config(state='normal')

    def get(self):
        """
        Overrides default get method which often gives an outdated value
        and instead returns latest value straight from the control variable

        :return: current value of editable widget, type depends on the
          control variable type
        """
        return self._var.get()


class ContextMenuMixin:
    """
    Adds context menu functionality to a widget
    """
    _on_context_menu = None

    @functools.wraps(MenuUtils.make_dynamic, assigned=('__doc__',))
    def make_menu(self, templates, parent=None, dynamic=True, **cnf):
        return MenuUtils.make_dynamic(templates, parent or self, self.style, dynamic, **cnf)

    def set_up_context(self, templates, **cnf):
        """
        Set up a context menu using the template which is a tuple
        containing items in the format
        ``(type, label, icon, command, additional_configuration={})``

        :param templates: menu template
        :param cnf: config for menu
        """
        self.context_menu = self.make_menu(templates, **cnf)
        self.bind_all("<Button-3>", lambda event: ContextMenuMixin.popup(event, self.context_menu), add='+')

    @staticmethod
    def popup(event, menu):
        """
        Show context menu at event location

        :param event: event whose location is to be used
        :param menu: menu to be displayed
        """
        MenuUtils.popup(event, menu)

    @staticmethod
    def add_context_menu(menu, widget):
        """
        Setup context menu for other widgets not extending this mixin

        :param menu: menu to be set up as context
        :param widget: widget to context menu on
        """
        widget.bind("<Button-3>", lambda event: ContextMenuMixin.popup(event, menu), add="+")


class ScrollableInterface:
    """
    Interface that allows widgets to be managed by the _MouseWheelDispatcherMixin which handles mousewheel
    events which may be tricky to handle at the widget level.
    """

    def on_mousewheel(self, event):
        raise NotImplementedError("on_mousewheel method is required")
    
    def handle_wheel(self, widget, event):
        # perform cross platform mousewheel handling
        delta = 0
        if platform_is(LINUX):
            delta = 1 if event.num == 5 else -1
        elif platform_is(MAC):
            # For mac delta remains unmodified
            delta = event.delta
        elif platform_is(WINDOWS):
            delta = -1 * (event.delta // 120)
            
        if event.state & EventMask.CONTROL:
            # scroll horizontally when control is held down
            widget.xview_scroll(delta, "units")
        else:
            widget.yview_scroll(delta, "units")

    def scroll_position(self):
        # Return the scroll position to determine if we have reach the end of scroll so we can
        # pass the scrolling to the next widget under the cursor that can scroll
        raise NotImplementedError("Scroll position required for scroll transfer")

    def scroll_transfer(self) -> bool:
        # Override this method and return true to allow scroll transfers
        return False


class CenterWindowMixin:
    # match > digit x digit + signed digit + signed digit
    #       > width x height + (-)x + (-)y
    GEOMETRY_RGX = re.compile(
        r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)"
    )

    def enable_centering(self):
        self.centered = False
        self._vis_bind = self.bind('<Visibility>', self.center, '+')
        if platform_is(WINDOWS):
            self._conf_bind = self.bind('<Configure>', self.center, '+')
            self.event_generate('<Configure>')

    def center(self, *_):
        if not self.centered:
            self.update_idletasks()
            ref_geometry = self.position_ref.get_geometry()
            geometry = self.get_geometry()
            if ref_geometry is None or geometry is None:
                # log it since we don't expect it to happen
                logging.error("Failed to fetch geometry")
                return
            r_width, r_height, r_x, r_y = ref_geometry
            width, height, *_ = geometry
            x = int((r_width - width) / 2) + r_x
            y = int((r_height - height) / 2) + r_y
            self.geometry("+{}+{}".format(x, y))
            self.centered = True if self.winfo_width() != 1 else False
        else:
            # we no longer need the bindings
            if hasattr(self, '_conf_bind'):
                self.unbind(self._conf_bind)
            if hasattr(self, '_vis_bind'):
                self.unbind(self._vis_bind)

    def get_geometry(self):
        """
        Get window geometry parsed into a tuple

        :return: tuple containing (width, height, x, y) in that order
        """
        search = self.GEOMETRY_RGX.search(self.geometry())
        if search is None:
            # not a valid geometry
            return None
        return tuple(map(int, search.groups()))


class PositionMixin:
    """
    Automatic positioning of popup windows, it positions windows such that
    the are visible from any point of the screen by providing a post method
    """

    def get_pos(self, widget, **kwargs):
        """
        Get the position of a popup window anchored around a widget

        :param widget: A tk widget to be used as an anchor point
        :param kwargs:
            -side: a string value "nw", "ne", "sw", "se", "auto" representing where the
              dialog is to be position relative the anchor widget
            -padding: an integer indicating how much space to allow between the popup and the
              anchor widget
            -width: prospected width of the popup which can be used even before the
              popup is initialized by tkinter. If not provided its obtained
              from the popup hence the popup must have been initialized by tkinter
            -height: prospected height of the popup. Same rules on ``width``
              apply here

        :return: None
        """
        side = kwargs.get("side", "auto")
        padding = kwargs.get("padding", 2)
        if "width" in kwargs and "height" in kwargs:
            w_width = kwargs.get("width")
            w_height = kwargs.get("height")
        else:
            self.re_calibrate()
            self.update_idletasks()
            w_width = self.width
            w_height = self.height
        widget.update_idletasks()
        x, y, width, height = widget.winfo_rootx(), widget.winfo_rooty(), widget.width, widget.height
        right = x
        left = x - w_width + width
        top = y - w_height - padding
        bottom = y + height + padding
        if side == "nw":
            return left, top
        elif side == "ne":
            return right, top
        elif side == "sw":
            return left, bottom
        elif side == "se":
            return right, bottom
        else:
            # i.e. side == "auto"
            # set the screen size as the boundary
            win_bounds = 0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()
            offset_b = win_bounds[3] - bottom
            offset_t = y - win_bounds[1]
            offset_l = x - win_bounds[0]
            offset_r = win_bounds[2] - right
            x_pos = left if offset_l >= offset_r or offset_l > w_width else right
            y_pos = bottom if offset_b >= offset_t or offset_b > w_height else top
            return x_pos, y_pos

    def post(self, widget, **kwargs):
        """
        Display a popup window anchored around a widget

        :param widget: A tk widget to be used as an anchor point
        :param kwargs:
            -side: a string value "nw", "ne", "sw", "se", "auto" representing where the
              dialog is to be position relative the anchor widget
            -padding: an integer indicating how much space to allow between the popup and the
              anchor widget
            -width: prospected width of the popup which can be used even before the
              popup is initialized by tkinter. If not provided its obtained
              from the popup hence the popup must have been initialized by tkinter
            -height: prospected height of the popup. Same rules on ``width``
              apply here

        :return: None
        """
        self.set_geometry(self.get_pos(widget, **kwargs))


class _Tooltip(tk.Toplevel):
    """
    Tooltip window class. It is not meant to be used directly; use the tooltip methods instead
    to create tooltips
    """
    Y_CLEARANCE = 10

    def __init__(self, style: StyleDelegator, xy: tuple, render, master=None):
        """
        Create a tooltip window

        :param style: A style delegator object to allow use of hoverset widgets inside the window
        :param xy: a tuple representing the current cursor position
        :param render: A function taking accepting one argument (the tooltip window)
        which draws content into the tooltip window
        :param master: The parent window for the tooltip
        """
        super().__init__(master)
        self.geometry(f"+{self.winfo_screenwidth() + 1000}+{self.winfo_screenheight() + 1000}")
        self.style = style
        self.overrideredirect(True)
        self.lift(master)
        render(self)
        self.config(**style.bright_highlight)
        self._position(xy)  # Determine the best position for the window given cursor coordinates xy

    def _position(self, xy):
        self.update_idletasks()  # refresh to get the updated position values
        # un-box position values
        w, h = self.winfo_width(), self.winfo_height()
        x, y = xy
        # center the window horizontally about the x, y position
        x -= w // 2
        # display the tooltip above or below the x, y position depending on which side has enough space
        y = y - self.Y_CLEARANCE - h if y - self.Y_CLEARANCE - h > 0 else y + self.Y_CLEARANCE
        # adjust the horizontal window position to fit within screen width
        x -= max(0, (x + w) - self.winfo_screenwidth())
        x = max(0, x)
        self.geometry('+{}+{}'.format(x, y))


# noinspection PyTypeChecker
class Widget:
    """
    Base class for all hoverset widgets implementing all common methods.
    """
    s_style = None  # Static style holder
    s_window = None  # Static window holder
    __readonly_options = {"class", "container"}

    def setup(self, _=None):
        """
        It performs the necessary dependency injection and event bindings and
        set up.
        """
        self._allow_drag = False
        self._drag_setup = False
        self._tooltip_text = None
        self._tooltip_ev = None
        self._tooltip_win = None
        self._tooltip_bound = False
        self._tooltip_delay = 1500

    @property
    def allow_drag(self):
        """
        Determines whether widgets can be dragged in-case of a drag drop event
        """
        return self._allow_drag

    @allow_drag.setter
    def allow_drag(self, flag: bool):
        """
        Call this method to make the widget allow or disallow drag and drop

        :param flag: set to True to allow drag drop and False to disallow
        """
        self._allow_drag = flag
        if self._allow_drag and not self._drag_setup:
            self.bind_all('<Motion>', self._drag_handler)
            self.bind_all('<ButtonRelease-1>', self._drag_handler)
            self._drag_setup = True

    def _drag_handler(self, event):
        """
        Handle drag drop events
        :param event: tk event
        """
        if not self.allow_drag:
            return
        if event.type.value == "6":
            # Event is of Motion type
            if event.state & EventMask.MOUSE_BUTTON_1 and self.window.drag_window is None:
                self.window.drag_context = self
                self.window.drag_window = DragWindow(self.window)
                self.render_drag(self.window.drag_window)
                self.window.drag_window.set_position(event.x_root, event.y_root)
                self.on_drag_start(event)
            elif self.window.drag_window is not None:
                self.window.drag_window.set_position(event.x_root, event.y_root)
        elif event.type.value == "5":
            # Event is of Button release type so end drag
            if self.window.drag_window:
                self.window.drag_window.destroy()
                self.window.drag_window = None
                # Get the first widget at release position that supports drag manager and pass the context to it
                event_position = self.event_first(event, self, Widget)
                if isinstance(event_position, Widget):
                    event_position.accept_context(self.window.drag_context)
                self.window.drag_context = None

    def accept_context(self, context):
        """
        This method is called when a drag drop operation is completed to allow the dropped object to be handled

        :param context: Object being dropped at the widget
        """
        logging.info(f"Accepted context {context}")

    def render_drag(self, window):
        """
        Override this method to create and position widgets on the drag shadow window (The object displayed
        as the widget is dragged around). Create your custom widget hierarchy and position
        it in window.

        :param window: The drag window provided by the drag manager that should be used as the widget master
        :return: None
        """
        tk.Label(window, text="Item", bg="#f7f7f7").pack()  # Default render

    def on_drag_start(self, *args):
        pass

    def config_all(self, cnf=None, **kwargs):
        """
        A way to config all the children of a widget. Especially useful for compound widgets where styles need to be
        applied uniformly or following a custom approach to all contained child widgets. Override this method to
        customize its behaviour to suit your widget. It defaults to the normal config

        :param cnf: :class:`dict` containing configuration
        :param kwargs: configurations as keyword arguments
        :return: None
        """
        self.config(cnf, **kwargs)

    def bind_all(self, sequence=None, func=None, add=None):
        """
        Total override of the tkinter bind_all method allowing events to be bounds to all the children of a widget
        and not the entire application. This is useful for compound widgets which need to behave as a single entity

        :param sequence: Event sequence to be bound
        :param func: Callback function
        :param add: specifies whether func will be called additionally to the other bound function or whether
          it will replace the previous function entirely.
        :return: identifier of the bound function allowing it to be unbound later
        """
        return self.bind(sequence, func, add)

    @property
    def width(self) -> int:
        """
        Wrapper property of the tk Misc class w.winfo_width() method for quick access to widget width property in pixels

        :return: width of widget
        """
        return self.winfo_width()

    @property
    def height(self) -> int:
        """
        Wrapper property of the tk Misc class w.winfo_height() method for quick access to widget height property in
        pixels
        :return: int
        """
        return self.winfo_height()

    def disabled(self, flag: bool) -> None:
        """
        Set the state of a widget to disabled .Override this method for compound widgets to obtain the
        expected behaviour as the state is by default only applied to the containing/parent widget.

        :param flag: True or False
        :return:
        """
        # clean the styles so we don't end up setting state to a widget that does not support it
        if flag:
            self.config(**clean_styles(self, {"state": tk.DISABLED}))
        else:
            self.config(**clean_styles(self, {"state": tk.NORMAL}))

    @staticmethod
    def event_in(event, widget):
        """
        Check whether event has occurred within a widget

        :param event: event object containing position data
        :param widget: the widget to be checked
        :return: True if event occurred in within widget else False
        """
        x, y = event.x_root, event.y_root
        x1, y1, x2, y2 = (
            widget.winfo_rootx(),
            widget.winfo_rooty(),
            widget.winfo_rootx() + widget.winfo_width(),
            widget.winfo_rooty() + widget.winfo_height(),
        )
        return x1 < x < x2 and y1 < y < y2

    @staticmethod
    def event_first(event, widget, class_: type, ignore=None):
        """
        Gets the first widget belonging to `class\_` at the event position. This widget
        may be the top widget or it's parents and grandparents deep down the hierarchy.
        Useful when you want to ignore widgets and cascade the event to a specific lower
        level widget.

        :param event: a tk event object containing the position data
        :param widget: any widget preferably the toplevel widget
        :param class_: the class of the widget we are interested in
        :param ignore: widget to be ignored if any
        :return: the first widget belonging to `class\_`, if no widget is found None is returned
        """
        check = widget.winfo_containing(event.x_root, event.y_root)
        while not isinstance(check, Application) and check is not None:
            if isinstance(check, class_) and not check == ignore:
                return check
            check = check.nametowidget(check.winfo_parent())
        return None

    def absolute_bounds(self):
        """
        Get the position of the widget on the screen

        :return: a tuple containing the bounding box of the widget (x1, y2, x2, y2)
        """
        self.update_idletasks()
        return (self.winfo_rootx(), self.winfo_rooty(),
                self.winfo_rootx() + self.width, self.winfo_rooty() + self.height)

    @staticmethod
    def clone_to(parent, widget):
        """
        Clone a tkinter widget to a different parent. Tkinter widget parents cannot be changed directly. This method
        performs recursive cloning of widget hierarchies. For cloning of custom tkinter widgets it is advisable to
        use clone method instead to specify your clone procedure

        :param parent: The new parent for cloned widget
        :param widget: The widget to be cloned
        :return: cloned widget
        """
        try:
            if isinstance(widget, Widget):
                clone = widget.clone(parent)
            else:
                clone = widget.__class__(parent)
                Widget.copy_config(widget, clone)
                [Widget.clone_to(clone, i) for i in widget.winfo_children()]
            return clone
        except TypeError:
            logging.debug(f"{widget.__class__} requires special clone handling")

    def clone(self, parent):
        """
        Generates a clone of the current widget for the given parent. Override this method in a custom widget to
        provide a custom implementation for cloning

        :param parent: A tk widget which will be clones parent
        :return: A clone of the current widget
        """
        # noinspection PyArgumentList
        return self.__class__(parent)

    @staticmethod
    def copy_config(from_, to):
        """
        Copy styles and configuration from one widget to another

        :param from_: Widget whose configuration is to be copied
        :param to: Widget receiving the copied configurations
        :return: None
        """
        if not from_.configure():
            return
        for key in from_.configure():
            if key in Widget.__readonly_options:
                continue
            try:
                to.configure(**{key: from_[key]})
            except tk.TclError:
                logging.debug("Attempted to set readonly option {opt}".format(opt=key))

    def tooltip(self, text, delay=1500):
        """
        Set the tooltip text for a widget

        :param text: Tooltip text to be displayed
        :param delay: Amount of time in milliseconds it takes for the tooltip to appear
        :return: None
        """
        if not self._tooltip_bound:
            # if tooltip events for this window have not been bound, setup the events
            self._setup_tooltip()
        self._tooltip_delay = delay
        self._tooltip_text = text

    def _setup_tooltip(self):
        # bind enter and exit events to trigger tooltip schedules
        # set add='+' to avoid possible overwriting of existing similar sequences
        self.bind('<Enter>', self._schedule_tooltip, add='+')
        self.bind('<Leave>', self._cancel_tooltip, add='+')
        self._tooltip_bound = True

    def _schedule_tooltip(self, *_):
        # cancel any previous scheduling
        self._cancel_tooltip()
        self._tooltip_ev = self.after(1500, self._show_tooltip)

    def _cancel_tooltip(self, *_):
        if self._tooltip_ev is not None:
            # there is a tooltip schedule active so cancel it
            self.after_cancel(self._tooltip_ev)
            self._tooltip_ev = None
        if self._tooltip_win:
            # if the cursor exits the widget of interest we need not display the tooltip anymore
            # if there exist a tooltip window on display close it
            self._tooltip_win.destroy()
            self._tooltip_win = None

    def _show_tooltip(self):
        # display tooltip window and maintain a reference for the purposes of termination
        self._tooltip_win = _Tooltip(self.style, self.winfo_pointerxy(), self.render_tooltip, self.window)

    def render_tooltip(self, window):
        """
        Create a custom tooltip body by overriding this method. The default rendering displays
        a simple Label with the tooltip text

        :param window: The tooltip window instance to be used as parent for the custom elements
        :return: None
        """
        tk.Label(window, **self.style.tooltip, text=self._tooltip_text).pack()

    @property
    def window(self):
        return self.winfo_toplevel()

    @property
    def style(self):
        return self.window.style


class ImageCacheMixin:
    """
    Performs automatic handling of images in tkinter widgets that use
    images by overriding configure methods and adding references to
    the images to shield them from garbage collection. It also handles
    animated widgets
    """
    _image_properties = ("image", "tristateimage", "selectimage")

    def configure(self, cnf=None, **kw):
        cnf = {} if cnf is None else cnf
        cnf.update(kw)
        for prop in ImageCacheMixin._image_properties:
            if cnf.get(prop):
                load_image_to_widget(self, cnf.get(prop), prop)
        return super().configure(cnf, **kw)

    def __setitem__(self, key, value):
        if key in ImageCacheMixin._image_properties:
            setattr(self, key, value)
        super().__setitem__(key, value)


class ContainerMixin:
    """
    Provides extra functionality to container types
    """

    def clear_children(self):
        for child in self.winfo_children():
            child.pack_forget()
            child.grid_forget()
            child.place_forget()

    def bind_all(self, sequence=None, func=None, add=None):
        self.bind(sequence, func, add)
        for child in self.winfo_children():
            if not (hasattr(child, "bind_all") and isinstance(child, Widget)):
                child.bind(sequence, func, add)
            else:
                child.bind_all(sequence, func, add)

    def on_click(self, callback, *args, **kwargs):
        self.bind_all('<Button-1>', self._click)
        self.bind_all("<Return>", self._click)
        self._on_click = lambda event: callback(event, *args, **kwargs)

    def _click(self, event):
        self.focus_set()
        if self._on_click is not None:
            self._on_click(event)

    def config_all(self, **cnf):
        self.config(**cnf)
        for child in self.winfo_children():
            child.config(**clean_styles(child, cnf))


class _MouseWheelDispatcherMixin:
    """
    Dispatches mousewheel events to the right scrolledFrame. The mousewheel event is bound to the main window
    then the event is processed by this mixin though widget resolution techniques to determine if there is any
    scrolled frame at the scroll position
    """

    def _on_mousewheel(self, event):
        # Resolve the widget under the cursor to determine if there is any scrollable widget (ScrollableInterface)
        # If any pass the event to it
        check = self.winfo_containing(event.x_root, event.y_root)
        while not isinstance(check, Application) and check is not None:
            if isinstance(check, ScrollableInterface):
                if check.scroll_transfer() and check.scroll_position()[0] < 1:
                    # Perform scroll transfer by ignoring this widget and checking the next
                    continue
                check.on_mousewheel(event)
                break
            check = check.nametowidget(check.winfo_parent())


class WindowMixin(_MouseWheelDispatcherMixin):

    def setup_window(self):
        self._on_close = None
        self._on_focus = None
        self._on_focus_lost = None
        self.drag_context = None
        self.drag_window = None
        # This normally fails for non-toplevel like frame and labelframe so lets wrap
        # This can however be re-enacted by the bind_close method when the frame is ready
        try:
            self.wm_protocol("WM_DELETE_WINDOW", self._close)
        except tk.TclError:
            pass

        self.bind("<FocusIn>", self._focus_)
        self.bind("<FocusOut>", self._focus_out_)

    def bind_close(self):
        self.wm_protocol("WM_DELETE_WINDOW", self._close)

    def set_up_mousewheel(self):
        self.bind_all("<MouseWheel>", self._on_mousewheel, '+')

    def on_close(self, callback, *args, **kwargs):
        self._on_close = lambda: callback(*args, **kwargs)

    def on_focus(self, callback, *args, **kwargs):
        self._on_focus = lambda: callback(*args, **kwargs)

    def on_focus_lost(self, callback, *args, **kwargs):
        self._on_focus_lost = lambda: callback(*args, **kwargs)

    def _close(self):
        if self._on_close:
            self._on_close()
        else:
            self.destroy()

    def _focus_(self, *_):
        if self._on_focus:
            self._on_focus()

    def _focus_out_(self, *_):
        if self._on_focus_lost:
            self._on_focus_lost()


class SpinBox(Widget, EditableMixin, tk.Spinbox):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, **cnf)
        self._var = tk.IntVar()
        self.config(textvariable=self._var)

    def get(self):
        self.update_idletasks()
        try:
            return self._var.get()
        except tk.TclError:
            return ''

    def set(self, value):
        self._var.set(value)
        self.update_idletasks()


class ComboBox(Widget, EditableMixin, ttk.Combobox):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master)
        self.config(**cnf)
        self._var = tk.StringVar()
        self.configure(textvariable=self._var)

    def config(self, **cnf):
        set_ttk_style(self, **cnf)
        return super().config(cnf)

    def config_style(self, **cnf):
        set_ttk_style(self, **cnf)

    def set_readonly(self) -> None:
        self.state(['readonly'])


class Entry(Widget, EditableMixin, tk.Entry):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, **cnf)
        self._var = tk.StringVar()
        self.config(textvariable=self._var)

    def set(self, value):
        self._var.set(value)
        self.update_idletasks()


class Label(Widget, ContextMenuMixin, ImageCacheMixin, tk.Label):

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master)
        self.configure(**kwargs)

    def set_alignment(self, alignment):
        self.config(anchor=alignment)


class Message(Widget, ContextMenuMixin, ImageCacheMixin, tk.Message):

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)

    def set_alignment(self, alignment):
        self.config(anchor=alignment)


class Frame(ContainerMixin, Widget, ContextMenuMixin, WindowMixin, tk.Frame, tk.Wm):

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)
        self.setup_window()
        # Since the frame may be a toplevel at some point we want the style
        # variable to be from the initial parent
        self._style = self.winfo_toplevel().style
        self._on_click = None
        self.body = self

    @property
    def style(self):
        return self._style


class LabelFrame(ContainerMixin, Widget, ContextMenuMixin, tk.LabelFrame):
    """
    Hoverset wrapper for :py:class:`tkinter.LabelFrame`
    """

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master)
        self.config(**{**self.style.text, **kwargs})
        self._on_click = None
        self.body = self


class ScrolledFrame(ContainerMixin, Widget, ScrollableInterface, ContextMenuMixin, WindowMixin, tk.Frame, tk.Wm):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, **cnf)
        self.setup_window()
        self._style = self.winfo_toplevel().style
        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._canvas.config(cnf)
        self._canvas.config(self.style.surface)
        self._scroll_y = ttk.Scrollbar(self, orient='vertical', command=self._limit_y)  # use frame limiters
        self._scroll_x = ttk.Scrollbar(self, orient='horizontal', command=self._limit_x)
        self._canvas.grid(row=0, column=0, sticky='nswe')
        self.columnconfigure(0, weight=1)  # Ensure the _canvas gets the rest of the left horizontal space
        self.rowconfigure(0, weight=1)  # Ensure the _canvas gets the rest of the left vertical space
        self._canvas.config(yscrollcommand=self._scroll_y.set, xscrollcommand=self._scroll_x.set)  # attach scrollbars
        self.body = Frame(self._canvas, **cnf)
        self.body.config(self.style.surface)
        self._window = self._canvas.create_window(0, 0, anchor='nw', window=self.body)
        # TODO Handle scrollbar flag behaviour
        self._scrollbar_flag = tk.Y  # Enable vertical scrollbar by default
        # self.after(200, self.on_configure)
        self._limit_var = [0, 0]  # limit var for x and y
        self._max_frame_skip = 3
        self.fill_x = True  # Set to True to disable the x scrollbar and fit content to width
        self.fill_y = False  # Set to True to disable the y scrollbar and fit content to height
        self._prev_region = (0, 0, 0, 0)
        self._prev_dimension = (0, 0)
        self._detect_change()

    @property
    def style(self):
        return self._style

    def _show_y_scroll(self, flag):
        if flag and not self._scroll_y.winfo_ismapped():
            self._scroll_y.grid(row=0, column=1, sticky='ns')
        elif not flag:
            self._scroll_y.grid_forget()
        self.update_idletasks()

    def _show_x_scroll(self, flag):
        if flag and not self._scroll_x.winfo_ismapped():
            self._scroll_x.grid(row=1, column=0, sticky='ew')
        elif not flag:
            self._scroll_x.grid_forget()
        self.update_idletasks()

    def config_all(self, **cnf):
        self.body.config_all(**clean_styles(self.body, cnf))
        super().config_all(**cnf)

    def _limiter(self, callback, axis, *args):
        # Frame limiting reduces lags while scrolling by skipping a number of scroll events to reduce the burden
        # of performing expensive redrawing by tkinter
        if self._limit_var[axis] == self._max_frame_skip:
            callback(*args)
            self._limit_var[axis] = 0
        else:
            self._limit_var[axis] += 1
        self._canvas.update_idletasks()
        self.body.update_idletasks()
        self.update_idletasks()

    def _limit_y(self, *scroll):
        self._limiter(self._canvas.yview, 1, *scroll)

    def _limit_x(self, *scroll):
        self._limiter(self._canvas.xview, 0, *scroll)

    def on_configure(self, *_):
        try:
            self._canvas.update_idletasks()
            self.body.update_idletasks()
            scroll_region = self._canvas.bbox("all")
        except tk.TclError:
            return

        dimension = (self._canvas.winfo_width(), self._canvas.winfo_height())
        if scroll_region == self._prev_region and dimension == self._prev_dimension:
            # Size has not necessarily changed so changes needed, break execution
            return
        self._prev_dimension = dimension
        self._prev_region = scroll_region

        if self.fill_y:
            # No vertical scrollbars needed
            self._canvas.itemconfigure(self._window, height=self._canvas.winfo_height())
        elif scroll_region[3] - scroll_region[1] > self._canvas.winfo_height():
            # Canvas content occupies more height than body's height so vertical scrollbars are needed
            self._show_y_scroll(True)
        else:
            # vertical scrollbars not needed, remove them
            self._show_y_scroll(False)

        if self.fill_x:
            # No horizontal scrollbars needed
            self._canvas.itemconfigure(self._window, width=self._canvas.winfo_width())
        elif scroll_region[2] - scroll_region[0] > self._canvas.winfo_width():
            # Canvas content occupies more width than body's height so horizontal scrollbars are needed
            self._show_x_scroll(True)
        else:
            # Horizontal scrollbars not needed, remove them
            self._show_x_scroll(False)

        # adjust scroll-region of the canvas to cover the contents
        self._canvas.config(scrollregion=scroll_region)

    def clear_children(self):
        # Unmap all children from the frame
        for child in self.body.winfo_children():
            child.pack_forget()

    def _detect_change(self, flag=True):
        # Lets set up the frame to listen to changes in size and update the scrollbars
        if flag:
            self.body.bind('<Configure>', self.on_configure)  # Changes in internal content
            self.bind('<Configure>', self.on_configure)  # Changes in the containing parent frame
        else:
            self.unbind('<Configure>')
            self.body.unbind('<Configure>')

    def on_mousewheel(self, event):
        # Enable the scrollbar to be scrolled using mouse wheel
        # Occasionally throws unpredictable errors so we better wrap it up in a try block
        try:
            if event.state & EventMask.CONTROL and self._scroll_x.winfo_ismapped():
                self.handle_wheel(self._canvas, event)
            elif self._scroll_y.winfo_ismapped():
                self.handle_wheel(self._canvas, event)
        except tk.TclError:
            pass

    def scroll_position(self):
        return self._scroll_y.get()

    def set_scrollbars(self, flag):
        """
        :param flag: set to tkinter.X to enable horizontal scrollbar, tkinter.Y to enable vertical scrollbar,
          tkinter.BOTH to enable both scrollbars and None to disable all scrollbars. The default is tkinter.Y for
          the vertical scrollbar.
        :return: None
        """
        self._scrollbar_flag = flag

    def content_height(self):
        self._canvas.update_idletasks()
        bbox = self._canvas.bbox('all')
        return bbox[3] - bbox[1] + 3

    def scroll_to_start(self):
        self._canvas.yview_moveto(0.0)
        self._canvas.xview_moveto(0.0)


class Screen:
    """
    What can comfortably be considered a tkinter fashion window for the root window (Tk)
    This allows calculations for centering the window possible with reference to the whole screen
    """

    def __init__(self, window: tk.Tk):
        self.window = window

    def winfo_x(self):
        return 0

    def winfo_y(self):
        return 0

    def winfo_width(self):
        return self.window.winfo_screenwidth()

    def winfo_height(self):
        return self.window.winfo_screenheight()

    def get_geometry(self):
        return self.winfo_width(), self.winfo_height(), 0, 0


class Application(Widget, CenterWindowMixin, _MouseWheelDispatcherMixin, ContextMenuMixin, tk.Tk):
    """
    The main toplevel widget for hoverset widgets. All hoverset widgets must
    be children or descendants of an :class:`hoverset.ui.widgets.Application` object.
    """
    # This class needs no dependency injection since its the source of the dependencies after all!

    def __init__(self, *args, **kwargs):
        Widget.s_window = self  # Window dependency set
        super().__init__(*args, **kwargs)
        self.position_ref = Screen(self)
        self.enable_centering()
        self.bind_all("<MouseWheel>", self._on_mousewheel, '+')
        # linux bindings
        self.bind_all("<Button-4>", self._on_mousewheel, '+')
        self.bind_all("<Button-5>", self._on_mousewheel, '+')
        self.drag_context = None
        self.drag_window = None
        # Load default styles
        self.load_styles(get_resource_path(
            hoverset.ui, "themes/default.css"
        ))

    def load_styles(self, theme):
        """
        Accepts a path to a cascading style sheet containing the styles used by the widgets. The style dependency is
        loaded here

        :param theme: name of the theme to be loaded with or without the .css extension
        :return: A :class:`hoverset.ui.styles.StyleDelegator` object
        """
        if os.path.exists(theme):
            path = theme
        else:
            path = get_theme_path(theme)
        self._style = StyleDelegator(path)

    @property
    def style(self):
        """
        Get the currently loaded css
        :return: a :class:`hoverset.ui.styles.StyleDelegator`
        """
        return self._style

    def bind_all(self, sequence=None, func=None, add="+"):
        return super(tk.Tk, self).bind_all(sequence, func, add)

    def unbind_all(self, sequence, func_id=None):
        """
        Unbind sequence from immediate children

        :param sequence: sequence to be unbound
        :param func_id: function id if any to unbind a specific callback
        :return:
        """
        for child in self.winfo_children():
            try:
                child.unbind(sequence, func_id)
            except tk.TclError:
                pass


class Window(Widget, CenterWindowMixin, WindowMixin, tk.Toplevel):

    def __init__(self, master=None, content=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.master = self.position_ref = master
        if master:
            self._style = master.window.style
        self.content = content
        self.setup_window()
        self.set_up_mousewheel()

    @property
    def style(self):
        return self._style


class ToolWindow(Window):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.wm_attributes('-alpha', 0.0)
        self.transient(master.window)

    def set_geometry(self, rec):
        logging.debug(f"placing window at {rec}")
        self.geometry("{}x{}+{}+{}".format(*rec))
        return self

    def show(self):
        """
        The window is initialized as invisible to allow you to set it up first. Call this method to make it visible
        """
        self.wm_attributes('-alpha', 1.0)


class ActionNotifier(Window):
    DELAY = 50

    def __init__(self, master, event, command=None, **cnf):
        super().__init__(master)
        self.config(self.style.surface)
        self.wm_overrideredirect(True)
        self.attributes("-alpha", 0)
        Label(self, **{**self.style.text, **cnf}).pack()
        self.current_opacity = 1
        self.initialized = False
        self.event = event
        if command:
            command(event)
        self.after(ActionNotifier.DELAY, self.__fade_up())

    @classmethod
    def bind_event(cls, sequence: str, widget, command, **cnf):
        widget.bind_all(sequence, lambda event: cls(widget.master, event, command, **cnf))
        return widget

    def __fade_up(self):
        if self.current_opacity == 0:
            self.destroy()
            return
        if not self.initialized:
            self.update_idletasks()
            width, height = self.winfo_width(), self.winfo_height()
            self._set_position(self.event.x_root - width / 2, self.event.y_root - height + 4)
            self.initialized = True
        self.current_opacity -= 0.05
        self.attributes("-alpha", self.current_opacity)
        self.update_idletasks()
        x, y = self.winfo_rootx(), self.winfo_rooty() - 1
        self._set_position(x, y)
        self.after(ActionNotifier.DELAY, self.__fade_up)

    def _set_position(self, x, y):
        self.geometry("+{}+{}".format(*list(map(int, [x, y]))))


class Canvas(Widget, ContextMenuMixin, tk.Canvas):
    """
    Hoverset wrapper for :class:`tkinter.Canvas`
    """

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)


class MenuButton(Widget, ImageCacheMixin, tk.Menubutton):
    """
    Hoverset wrapper for :class:`tkinter.Menubutton`
    """

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)


class Button(Frame):
    """
    Completely custom Hoverset widget built on top of :class:`hoverset.ui.widgets.Frame`
    """

    # For purposes of easy customization we saw it wise to extend the Label instead of the button
    # The default tkinter button implements a sunken relief on click that is rather ancient.
    # So we'd rather reinvent the wheel (Painful yes) but we can stay modern.
    # TODO Implement Repeat-delay functionality

    def __init__(self, master=None, **cnf):
        super().__init__(master)
        cnf = cnf if len(cnf) else self.style.button
        # Use the hoverset Label which has additional automatic image caching capabilities
        self._label = Label(self)
        self._label.pack(fill="both", expand=True)
        self.config(**cnf)
        self.pack_propagate(False)

    def auto_width(self):
        self.pack_propagate(True)

    def measure_text(self, text):
        return FontStyle(family=self._label["font"]).measure(text)

    def on_click(self, callback, *args, **kwargs):
        """
        A more elaborate event binding that binds mouse clicks, return button and
        space button useful for mouse free operation. The callback should accept
        an event argument.

        :param callback: callback function to be bound
        :param args: arguments to be passed to callback
        :param kwargs: keyword arguments to be passed to callback
        """
        if callback is None:
            return
        self.bind_all("<Button-1>", lambda e: callback(e, *args, **kwargs))
        self.bind_all("<Return>", lambda e: callback(e, *args, **kwargs))
        self.bind_all("<space>", lambda e: callback(e, *args, **kwargs))

    def config(self, **cnf):
        if not cnf:
            return super().config()
        super().configure(clean_styles(self, cnf))
        self._label.configure(clean_styles(self._label, cnf))


class ToggleButton(Button):
    """
    Hoverset button allowing toggling
    """

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.bind_all("<Button-1>", self.toggle)
        self.config_all(**self.style.button)
        self.config_all(**cnf)
        self._selected = False
        self._on_change = lambda x: x  # Place holder

    def toggle(self, *_):
        if self._selected:
            self.deselect()
        else:
            self.select()
        self._on_change(self._selected)

    def get(self) -> bool:
        return self._selected

    def set(self, value: bool):
        if value:
            self.select()
        else:
            self.deselect()

    def select(self):
        self.config_all(**self.style.hover)
        self._selected = True

    def deselect(self):
        self.config_all(**self.style.surface)
        self._selected = False

    def on_click(self, callback, *args, **kwargs):
        super().on_click(callback, *args, **kwargs)
        self.bind_all("<Button-1>", self.toggle, '+')

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda value: func(value, *args, **kwargs)


class Checkbutton(Widget, ImageCacheMixin, tk.Checkbutton):
    """
    Hoverset wrapper for :py:class:`tkinter.ttk.Checkbutton`
    """

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master)
        cnf = {**self.style.checkbutton, **cnf}
        self.configure(**cnf)
        self._var = tk.BooleanVar()
        self.config(variable=self._var)

    def set(self, value):
        """
        Set the boolean value directly

        :param value: boolean value to be set
        """
        self._var.set(value)

    def get(self):
        """
        Get the selection state

        :return: ``True`` if selected else ``False``
        """
        return self._var.get()


class RadioButton(Widget, ImageCacheMixin, tk.Radiobutton):
    """
    Hoverset wrapper for :py:class:`tkinter.ttk.Radiobutton`
    """

    def __init__(self, master, **cnf):
        self.setup(master)
        super().__init__(master)
        cnf = {**self.style.radiobutton, **cnf}
        self.configure(**cnf)


class RadioButtonGroup(Frame):
    """
    Group of :py:class:`RadioButton` objects used to obtain a single value
    out of multiple options.

    .. code-block:: python

        button_group = RadioButtonGroup(
            parent,
            choices=(
                ("yellow", "This is the yellow option"),
                ("red", "This is the red option"),
            ),
            label="Select an option"
        )
        button_group.add_choice(("blue", "This is the blue option"))
        button_group.pack(side="top")
        button_group.set("red")  # selects the red option
        button_group.get()  # returns red
    """

    def __init__(self, master=None, choices=(), label='', **cnf):
        super().__init__(master)
        cnf = {**self.style.text, **cnf}
        self._pool = []
        self._radio_buttons = []
        self._var = tk.StringVar()
        self._var.trace("w", self._change)
        self._blocked = False
        self._on_change = None
        self._label = Label(self, text=label, anchor=tk.W)
        self._label.pack(side=tk.TOP, fill=tk.X, pady=3)
        self.set_choices(choices)
        self.config_all(**cnf)

    def _change(self, *_):
        if self._on_change and not self._blocked:
            self._on_change()

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda: callback(*args, **kwargs)

    def config_all(self, **cnf):
        """
        Use this method to correctly configure all radio buttons in the
        group

        :param cnf: config options
        :return: None
        """
        self.config(clean_styles(self, cnf))
        self._label.config(clean_styles(self._label, cnf))
        if len(self._radio_buttons):
            radio_conf = clean_styles(self._radio_buttons[0], cnf)
            for button in self._radio_buttons:
                button.config_all(**radio_conf)

    def set_label(self, label):
        """
        Set the group label

        :param label: string to be set as label
        """
        self._label.config(text=label)

    def add_choice(self, choice):
        """
        Add a choices to be appended at the end of the radio group as
        a ``(value, label)`` pair

        :param choice: a ``(value label)`` pair
        """
        value, desc = choice
        if len(self._pool):
            # pool is not empty so get buttons from there
            button = self._pool.pop(0)
        else:
            # create a new radio button since pool is empty
            button = RadioButton(self)
        button.config(value=value, text=desc, variable=self._var)
        button.pack(side=tk.TOP, fill=tk.X, padx=10)
        self._radio_buttons.append(button)

    def set_choices(self, choices):
        """
        Add the choices to be displayed in the radio group as
        ``(value, label)`` pairs

        :param choices: a tuple of ``(value label)`` pairs
        """
        # clear previous value silently without triggering change
        self.set("", True)
        for btn in self._radio_buttons:
            btn.pack_forget()
        # move all radio buttons to the pool
        self._pool.extend(self._radio_buttons)
        self._radio_buttons.clear()
        for choice in choices:
            self.add_choice(choice)

    def get(self):
        """
        Get the value of the currently selected option

        :return: value of the current option
        """
        return self._var.get()

    def disabled(self, flag: bool) -> None:
        super().disabled(flag)
        self._label.disabled(flag)
        for button in self._radio_buttons:
            button.disabled(flag)

    def set(self, value, silent=False):
        """
        Set the selected option

        :param value: value to be set
        :param silent: set to ``True`` to trigger change event
        """
        self._blocked = silent
        self._var.set(value)
        self._blocked = False


class Scale(Widget, ttk.Scale):
    """
    Hoverset wrapper for :py:class:`tkinter.ttk.Scale`
    """

    def __init__(self, master=None, variable=None, **cnf):
        self.setup(master)
        self._var = variable or tk.DoubleVar()
        super().__init__(master, variable=self._var)
        cnf = {**self.style.surface, **cnf}
        self.config_all(**cnf)
        self._on_change = None
        self._var.trace('w', self._change)

    def _change(self, *_):
        if self._on_change:
            self._on_change()

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda: callback(*args, **kwargs)

    def config_all(self, **kwargs):
        """
        Configure all options including ttk themed options automatically

        :param kwargs: config options
        :return: None
        """
        config_ttk(self, **kwargs)

    def set(self, value):
        """
        Set scale value. Overrides default behaviour and sets the value
        directly to the underlying variable

        :param value: Value to be set
        """
        self._var.set(value)

    def get(self, x=None, y=None):
        """
        Gets the current value directly from the underlying variable
        if either x or y is not provided.

        :param y: return value at x if provided
        :param x: return value at y if provided
        :return: current scale value
        """
        if x is None or y is None:
            return self._var.get()
        return super().get(x, y)


class Popup(PositionMixin, Window):

    def __init__(self, master, pos=None, **cnf):
        super().__init__(master, **cnf)
        if pos is not None:
            self.set_geometry(pos)
        self._close_func = None
        self.config(**self.style.highlight_active, **self.style.surface)
        self.overrideredirect(True)
        self.attributes("-topmost", 1)
        self._grabbed = self.grab_current()  # Store the widget that currently has the grab
        # Grab all events so we can tell whether someone is clicking outside the popup
        self.bind("<Visibility>", self._on_visibility)
        self.bind("<Button-1>", self._exit)
        self.body = self

    def _on_visibility(self, _):
        self.grab_set_global()

    def _exit(self, event):
        if not Widget.event_in(event, self):
            # Someone has clicked outside the popup so close it
            self.destroy()

    @chain
    def set_geometry(self, rec):
        x, y, width, height = rec if len(rec) == 4 else rec + (None, None)
        try:
            if width is None:
                self.geometry("+{}+{}".format(x, y))
            else:
                self.geometry("{}x{}+{}+{}".format(width, height, x, y))
        except tk.TclError:
            pass

    def hide(self):
        self.attributes("-alpha", 0)

    def show(self):
        self.attributes("-alpha", 1)

    def destroy(self):
        self.grab_release()
        if self._grabbed:
            try:
                self._grabbed.grab_set()  # Return the grab to whichever widget had it if any
            except tk.TclError:
                pass
        super().destroy()
        if self._close_func is not None:
            self._close_func()

    def re_calibrate(self):
        pass

    def on_close(self, func, *args, **kwargs):
        self._close_func = lambda: func(*args, **kwargs)


class DrawOver(PositionMixin, Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.highlight_active, **self.style.surface)
        self._close_func = None
        self._grabbed = self.grab_current()
        self.grab_set_global()
        self.focus_set()
        self._destroyed = False
        self.bind("<ButtonPress>", self._exit)
        self.re_calibrate()

    def _exit(self, event):
        if not Widget.event_in(event, self):
            self.destroy()

    def re_calibrate(self):
        # This is a necessary magic! We need to place the frame somewhere without specifying width or height
        # it cannot be seen for it to obtain its width and height using its contents so it can allow external uses to
        # have these values for positioning calculations
        self.place(x=10000, y=10000)  # It definitely wont be seen here
        self.update_idletasks()

    @chain
    def set_geometry(self, rec):
        try:
            x, y, width, height = rec if len(rec) == 4 else rec + (None, None)
            x -= self.window.winfo_rootx()
            y -= self.window.winfo_rooty()
            if width is None:
                self.place(x=x, y=y)
            else:
                self.place(x=x, y=y, width=width, height=height)
        except tk.TclError:
            pass

    def destroy(self):
        if self._destroyed:
            return
        self.grab_release()
        self.place_forget()
        if self._close_func:
            self._close_func()
        if self._grabbed:
            self._grabbed.grab_set()
        super().destroy()
        self._destroyed = True

    def on_close(self, func, *args, **kwargs):
        self._close_func = lambda: func(*args, **kwargs)


class CompoundList(ScrolledFrame):
    """
    ListBox widget allowing for more flexibility with custom items extending
    :py:class:`CompoundList.BaseItem`. Here is an example:

    .. code-block:: python

        from hoverset.ui.widgets import CompoundList, Application, Label

        app = Application()

        my_list = CompoundList(app)

        class CustomItem(CompoundList.BaseItem):
            # Custom class to display two fields in a single item

            def render(self):
                occupation, name = self.value
                Label(self, text=f"Occupation: {occupation}").pack(side="top")
                Label(self, text=f"Name: {name}").pack(side="top")

        my_list.set_item_class(CustomItem)
        my_list.set_values([["Engineer", "John"], ["Professor", "Sir Isaac"]])
        my_list.pack()

        app.mainloop()

    """
    MULTI_MODE = 0x001
    SINGLE_MODE = 0x002
    BROWSE_MODE = 0x003

    class BaseItem(Frame):
        """
        Base class for all custom list items
        """

        def __init__(self, master, value, index, isolated=False):
            super().__init__(master.body)
            self._value = value
            self._parent = master
            self._index = index
            self._selected = False
            self._isolated = isolated
            self.render()
            if not self._isolated:
                self.bind("<Enter>", self._on_hover)
                self.bind("<Leave>", self._on_hover_ended)
                self.bind_all("<Button-1>", self.select_self, add="+")
            self.config_all(**self.style.surface)

        def render(self):
            """
            Create the custom section of a custom item. Override this
            method and add new widgets to the item. The default rendering
            is a label containing the value of the item
            """
            self._text = Label(self, **self.style.text, text=self._value, anchor="w")
            self._text.pack(fill="both")

        @property
        def value(self):
            """
            The value the item is supposed to display. Can be any object
            depending on what is set through :py:attr:`CompoundList.set_values`

            :return: Value represented by item
            """
            return self._value

        def select_self(self, event=None, *_):
            """
            Set the item as selected in its parent list

            :param event: event causing the selection. Default is ``None``
            """
            self._parent.select(self._index, event)

        def select(self, *_):
            """
            Marks item as selected and applies the required styles and
            configuration to make it appear selected such as the color
            """
            self._selected = True
            self.on_hover()

        def deselect(self):
            """
            Marks item as deselected and applies the required styles and
            configuration to make it return to its normal state
            """
            self._selected = False
            self.on_hover_ended()

        # We need to add implementation details separate from library
        # user interference
        # Users are therefore free to override the non-private wrappers
        # without breaking core functionality
        def _on_hover(self, *_):
            if self._parent.get_mode() == CompoundList.BROWSE_MODE:
                self._parent.select(self._index)
            else:
                self.on_hover(*_)

        def _on_hover_ended(self, *_):
            if not self._selected:
                self.on_hover_ended(*_)

        def on_hover(self, *_):
            """
            Applies styles and config required when item is hovered
            """
            self.config_all(**self.style.hover)

        def on_hover_ended(self, *_):
            """
            Revert the item config when no longer under hover
            """
            self.config_all(**self.style.surface)

        def get(self):
            """
            Get the value represented by the item

            :return: Value represented by the item
            """
            return self._value

        def clone_to(self, parent):
            """
            Create a copy of the item for positioning in a new parent

            :param parent: New intended parent
            :return: the new item clone
            """
            return self.__class__(parent, self._value, self._index, True)

    # ----------------------------------------- CompoundList -----------------------------------------------

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self._cls = CompoundList.BaseItem  # Default
        self._values = []
        self._current_indices = []
        self._items = []
        self._mode = CompoundList.SINGLE_MODE  # Default
        self.config(self.style.surface)
        self._on_change = None

    @property
    def items(self):
        return self._items

    def set_mode(self, mode):
        """
        Set the mode of selection

        :param mode: mode value which can be one of the following

            * :py:attr:`CompoundList.SINGLE_MODE`: allows selection of one
              item at a time
            * :py:attr:`CompoundList.MULTI_MODE`: allows selection of multiple
              items by holding down the control key
            * :py:attr:`CompoundList.BROWSE_MODE`: allows selection of one item
              at a time. Selection will follow the currently hovered item

        """
        self._mode = mode

    def get_mode(self):
        """
        Get currently set mode
        """
        return self._mode

    def set_item_class(self, cls):
        """
        Set the class used to render the list items in the case of custom
        items.

        :param cls: A a subclass of :py:class:`CompoundList.BaseItem`
        """
        self._cls = cls

    def get_class(self):
        """
        Get the item class currently in use

        :return: current item class
        """
        return self._cls

    def set_values(self, values):
        """
        Set the values to be displayed by the list box

        :param values: an iterable containing the item values to be displayed
        """
        self._values = values
        self._render(values)

    def _render(self, values):
        for i in range(len(values)):
            item = self._cls(self, values[i], i)
            self._items.append(item)
            item.pack(side="top", fill="x", pady=1)
            item.update_idletasks()

    def add_values(self, values):
        """
        Append new values to the list

        :param values: an iterable containing items to be added
        :return:
        """
        self._values += values
        self._render(values)

    def select(self, index, event=None):
        """
        Select item at given index

        :param index: index to be selected
        :param event: event generating the selection if any
        """
        if event and event.state & EventMask.CONTROL and self._mode == CompoundList.MULTI_MODE:
            self._multi_selector(index)
        else:
            self._single_selector(index)
        if self._on_change:
            self._on_change(self.get())

    def _single_selector(self, index):
        for item in self._current_indices:
            self._items[item].deselect()
        self._current_indices = [index]
        self._items[index].select()

    def _multi_selector(self, index):
        if index in self._current_indices:
            self._current_indices.remove(index)
            self._items[index].deselect()
        else:
            self._current_indices.append(index)
            self._items[index].select()

    def get(self):
        """
        Get currently selected item(s)

        .. note::

            This does not return the underlying value but the rendered item
            currently selected which is a :class:`CompoundList.BaseItem`
            object. To obtain the value use its ``value`` property or ``get``
            method

        :return: selected item if mode is not set to MULTI_MODE otherwise
          a list of all selected items. If no item is selected ``None`` is
          returned
        """
        if self._mode == CompoundList.MULTI_MODE:
            return [self._items[index] for index in self._current_indices]
        elif len(self._current_indices):
            return self._items[self._current_indices[0]]
        else:
            return None

    def on_change(self, func, *args, **kwargs):
        """
        Set a callback function to be called on selection change

        :param func: callback function
        :param args: extra positional arguments to be passed to callback
          in addition to the selected item
        :param kwargs: keyword arguments to be passed to callback function
        """
        self._on_change = lambda value: func(value, *args, **kwargs)


class Spinner(Frame):
    """
    Combobox widget allowing easy customization of choice items
    """
    __icons_loaded = False
    EXPAND = None
    COLLAPSE = None

    def __init__(self, master=None, **_):
        super().__init__(master)
        self._load_images()
        self._button = Button(
            self, **self.style.button,
            image=self.EXPAND,
            width=20, anchor="center"
        )
        self._button.pack(side="right", fill="y")
        self._button.on_click(self._popup)
        self._entry = Frame(self, **self.style.surface)
        self._entry.body = self._entry
        self._entry.pack(side="left", fill="both", expand=True)
        # self._entry.pack_propagate(0)
        self.config(**self.style.highlight_active)
        self._popup_window = None
        self._on_create_func = None
        self._on_change = None
        self._values = []
        self._value_item = None
        self._item_cls = CompoundList.BaseItem
        self.dropdown_height = 150

    @classmethod
    def _load_images(cls):
        if cls.__icons_loaded:
            return
        cls.EXPAND = get_icon_image("triangle_down", 14, 14)
        cls.COLLAPSE = get_icon_image("triangle_up", 14, 14)
        cls.__icons_loaded = True

    def _popup(self, _=None):
        if self._popup_window is not None:
            self._popup_window.destroy()
            self._button.config(image=self.EXPAND)
            self._popup_window = None
            return
        self.update_idletasks()
        self.window.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        rec = x, y, self.winfo_width(), 0
        popup = self._popup_window = Popup(self.window, rec)

        options = CompoundList(popup.body)
        options.set_item_class(self._item_cls)
        options.set_values(self._values)
        options.on_change(self._make_selection)
        options.pack()
        options.update_idletasks()
        initial_height = min(options.content_height(), self.dropdown_height)
        # Sometimes there is no space for the drop-down so we need to check
        # If the initial_height + the distance at the bottom left corner of spinner from the top of the screen
        # is greater than the screen-height we animate upwards
        if y + initial_height + self.winfo_height() >= self.winfo_screenheight():
            direction = 'up'
            rec = x, y, self.winfo_width(), 0
        else:
            # Since we are animating downwards, the top of the dropdown begins at the bottom of the spinner
            y = y + self.winfo_height()
            rec = x, y, self.winfo_width(), 0
            direction = 'down'
        popup.set_geometry(rec)

        def update_popup(dx):
            if direction == 'up':
                # No space down so animate upwards
                popup.set_geometry((x, y - int(dx), rec[2], int(dx)))
            else:
                # Animate down by default
                popup.set_geometry((x, y, rec[2], int(dx)))

            options.update_idletasks()
            popup.update_idletasks()

        Animate(popup, 0, initial_height, update_popup,
                easing=Easing.SLING_SHOT, dur=0.2)
        self._button.config(image=self.COLLAPSE)
        popup.on_close(self._close_popup)

    def _close_popup(self):
        # self._popup_window = None
        # This fails at times during program close up
        try:
            self._button.config(image=self.EXPAND)
        except tk.TclError:
            pass

    def config_all(self, **cnf):
        self.config(**cnf)
        self._entry.config(**cnf)
        self._button.config(**cnf)

    @chain
    def on_create(self, func, *args, **kwargs):
        self._on_create_func = lambda: func(*args, **kwargs)

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda val: func(val, *args, **kwargs)

    def set_values(self, values):
        self._values = list(values)
        if len(values):
            self.set(values[0])

    def add_values(self, *values):
        self._values += values

    def remove_value(self, value):
        if value in self._values:
            self._values.remove(value)

    def set(self, value):
        if self.get() == value:
            return
        if value in self._values:
            if self._value_item:
                self._value_item.pack_forget()
            self._value_item = self._item_cls(self._entry, value, self._values.index(value), True)
            self._value_item.pack(fill="both")

    def set_item_class(self, class_):
        self._item_cls = class_

    def _make_selection(self, item):
        if self._value_item:
            self._value_item.pack_forget()
        self._value_item = item.clone_to(self._entry)
        self._value_item.pack(fill="both")
        if self._on_change is not None:
            self._on_change(item.get())
        self._popup()

    def disabled(self, flag):
        self._entry.disabled(flag)

    def get(self):
        if self._value_item is None:
            return None
        return self._value_item.get()


class TreeView(ScrolledFrame):
    """
    Custom tree view implementation that is way more flexible for hoverset applications. Can be easily
    modified and works well with hoverset themes.
    """

    class Strip(Frame):
        """
        An interface for event binding to tree view items
        """

        def __init__(self, master=None, **config):
            super().__init__(master, **config)
            self.parent_node = master

        def select(self):
            self.parent_node.select()

        def deselect(self):
            self.parent_node.deselect()

    class Node(Frame):
        # will be loaded later
        EXPANDED_ICON = None
        COLLAPSED_ICON = None
        BLANK = None
        __icons_loaded = False
        PADDING = 1

        def __init__(self, master=None, **config):
            super().__init__(master.body)
            self._load_images()
            self.config(**self.style.surface)
            self.tree = master
            self._icon = config.get("icon", self.BLANK)
            self._name = config.get("name", "unknown")
            self.strip = f = TreeView.Strip(self, **self.style.surface, takefocus=True)
            f.pack(side="top", fill="x")
            self._spacer = Frame(f, **self.style.surface, width=0)
            self._spacer.pack(side="left")
            self.expander = Label(f, **self.style.text, text=" " * 4)
            self.expander.pack(side="left")
            self.expander.bind("<Button-1>", self.toggle)
            self.strip.bind("<FocusIn>", self.select)
            self.strip.bind("<Up>", self.select_prev)
            self.strip.bind("<Down>", self.select_next)
            self.icon_pad = Label(f, **self.style.text, image=self._icon)
            self.icon_pad.pack(side="left")
            self.name_pad = Label(f, **self.style.text, text=self._name)
            self.name_pad.pack(side="left", fill="x")
            self.name_pad.bind("<ButtonRelease-1>", self.select)
            self.strip.bind("<ButtonRelease-1>", self.select)
            self.body = Frame(self, **self.style.surface)
            self.body.pack(side="top", fill="x")
            self._expanded = False
            self._selected = False
            self._depth = 0  # Will be set on addition to a node or tree so this value is just placeholder
            self.parent_node = None
            self.nodes = []

        @classmethod
        def _load_images(cls):
            if cls.__icons_loaded:
                return
            cls.EXPANDED_ICON = get_icon_image("chevron_down", 14, 14)
            cls.COLLAPSED_ICON = get_icon_image("chevron_right", 14, 14)
            cls.BLANK = get_icon_image("blank", 14, 14)
            cls.__icons_loaded = True

        @property
        def depth(self):
            return self._depth

        @depth.setter
        def depth(self, value):
            self._depth = value
            self._spacer["width"] = 14 * (value - 1) + 1  # width cannot be set to completely 0 so add 1 just in case
            # Update depth even for the children
            for node in self.nodes:
                node.depth = self._depth + 1

        @property
        def name(self):
            return self.name_pad["text"]

        def bind_all(self, sequence=None, func=None, add=None):
            # The strip is pretty much the handle for the Node so better bind events here
            self.strip.bind(sequence, func, add)
            for child in self.strip.winfo_children():
                child.bind(sequence, func, add)

        def _set_expander(self, icon):
            if icon:
                self.expander.configure(image=icon)
            else:
                self.expander.configure(image=self.BLANK)

        def is_descendant(self, node):
            if node.depth >= self.depth:
                return False
            parent = self.parent_node
            while parent is not None:
                if parent == node:
                    return True
                parent = parent.parent_node
            return False

        def select_prev(self, event):
            self.tk_focusPrev().select(event)

        def select_next(self, event):
            self.tk_focusNext().select(event)

        def select(self, event=None, silently=False):
            if event and event.state == '??':
                # when the event is as a result of focus change using the tab key the event.state attribute
                # is a string equal to '??'. We therefore perform a basic selection
                self.tree.select(self)
                return
            elif event and event.state & EventMask.CONTROL:
                self.tree.toggle_from_selection(self)
                return
            elif event:
                self.tree.select(self)
            else:
                self.tree.add_to_selection(self, silently)

            self.strip.config_all(**self.style.hover)
            self._selected = True

        def deselect(self, *_):
            self.strip.config_all(**self.style.surface)
            self._selected = False

        def index(self):
            return self.parent_node.nodes.index(self)

        def toggle_select(self, event):
            if self._selected:
                self.deselect(event)
            else:
                self.select(event)

        @chain  # This just makes the method returns the object instance to allow method chaining
        def add(self, node):
            if self.is_descendant(node) or node == self:
                # You cannot add a node to its descendant/ child or itself
                return
            self.nodes.append(node)
            node.parent_node = self
            node.depth = self.depth + 1
            node.lift(self.body)
            if self._expanded:
                node.pack(in_=self.body, fill="x", side="top", pady=self.PADDING)
            else:
                self._set_expander(self.COLLAPSED_ICON)

        def insert_after(self, *nodes):
            """
            Insert the nodes immediately after this node in the same parent

            :param nodes: List of nodes to be inserted
            """
            self.parent_node.insert(self.parent_node.nodes.index(self) + 1, *nodes)

        def insert_before(self, *nodes):
            """
            Insert the nodes immediately before this node in the same parent

            :param nodes: List of nodes to be inserted
            """
            self.parent_node.insert(self.index(), *nodes)

        def insert(self, index=None, *nodes):
            """
            Insert all child nodes passed into parent node starting from the given index

            :param index: int representing the index from which to insert
            :param nodes: Child nodes to be inserted
            """
            # If no index is provided we assume we are appending
            index = len(self.nodes) if index is None else index
            for node in nodes:
                if self.is_descendant(node) or node == self:
                    # You cannot add a node to its descendant/ child or itself
                    continue
                node.remove()  # Remove node from whatever parent it belongs to
                self.nodes.insert(index, node)
                index += 1
                node.parent_node = self
                node.depth = self.depth + 1
                node.lift(self.body)
            if self._expanded:
                self.collapse()
                self.expand()
            if len(self.nodes) > 0:
                self._set_expander(self.COLLAPSED_ICON)
                self.expand()

        def add_as_node(self, **options):
            """
            Adds a node to the tree view.

            :param options: Options used in creating the node like name, icon e.t.c. depending on the Node
            :return: The created Node
            """
            # Create an object belonging to the same Node family as self
            # This allows sub-classes of TreeView to implement their own nodes.
            # By default self.__class__ will be equivalent to TreeView.Node but could change with subclasses
            node = self.__class__(self.tree, **options)
            node.parent_node = self
            node.depth = self.depth + 1
            self.add(node)
            return node

        def remove(self, node=None):
            """
            Remove the node from node's child nodes. If node is not provided the the node removes itself from
            its parent

            :param node: Node to be removed (optional)
            :return: None
            """
            if node is None:
                self.parent_node.remove(self)
            elif node in self.nodes:
                # We need a local copy of the expanded flag since calling collapse resets
                was_expanded = self._expanded
                # Collapse parent so that layout changes caused by removal of a node can be applied
                self.collapse()
                self.nodes.remove(node)
                node.pack_forget()
                if was_expanded:
                    # If the parent was expanded when we began removal we expand it again
                    self.expand()
                if len(self.nodes) == 0:
                    # remove the expansion icon
                    self._set_expander(self.BLANK)

        def expand(self):
            if len(self.nodes) == 0:
                # There is nothing to expand
                return
            self.pack_propagate(True)
            for node in self.nodes:
                node.pack(in_=self.body, fill="x", side="top", pady=self.PADDING)
            self._set_expander(self.EXPANDED_ICON)
            self._expanded = True

        def collapse(self):
            if len(self.nodes) == 0:
                # There is nothing to collapse
                return
            for node in self.nodes:
                node.pack_forget()
            self.pack_propagate(False)
            self.config(height=20)
            self._set_expander(self.COLLAPSED_ICON)
            self._expanded = False

        def expand_all(self):
            # Expand all nodes recursively
            self.expand()
            for node in self.nodes:
                node.expand_all()

        def collapse_all(self):
            # Collapse all nodes recursively
            self.collapse()
            for node in self.nodes:
                node.collapse_all()

        def toggle(self, *_):
            """
            Toggle between the expanded and collapsed state
            """
            if self._expanded:
                self.collapse()
            else:
                self.expand()

        def clear(self):
            nodes = list(self.nodes)
            for node in nodes:
                self.remove(node)

    # ============================================= TreeView ================================================

    def __init__(self, master=None, **config):
        super().__init__(master, **config)
        self.config(**self.style.surface)
        self._selected = []
        self.nodes = []
        self._multi_select = False
        self._on_select = None
        self.depth = 0
        self._parent_node = None  # This value should never be changed
        # self.fill_x = False

    @property
    def parent_node(self) -> None:
        # We prevent anyone from altering the parent_node value
        # The parent node for a tree is always None
        return self._parent_node

    def select(self, n, silently=False):
        """
        Select a node :param n and deselect all other selected nodes

        :param silently: Flag set to true to prevent firing on change event and vice versa. Default is false
        :param n: Node to be selected
        """
        for node in self._selected:
            node.deselect()
        self._selected = [n]
        if not silently:
            self.selection_changed()

    def clear_selection(self):
        """
        Deselect all currently selected nodes
        """
        for node in self._selected:
            node.deselect()
        self._selected = []
        self.selection_changed()

    def get(self):
        """
        Get the currently selected node if multi select is set to False and a list of all selected items if multi
        select is set to True. Returns None if no item is selected.

        :return: Selected widget or None if no widget is selected
        """
        if self._multi_select:
            return self._selected
        else:
            if len(self._selected):
                return self._selected[0]
            else:
                return None

    def add_to_selection(self, node, silently=False):
        if not self._multi_select:
            # We are not in multi select mode so select one node at a time
            self.select(node)
        else:
            # Append node without affecting the other selected nodes
            self._selected.append(node)
            if not silently:
                self.selection_changed()

    def toggle_from_selection(self, node):
        if not self._multi_select:
            return
        if node in self._selected:
            self.deselect(node)
            self.selection_changed()
        else:
            node.select()

    def deselect(self, node):
        if node in self._selected:
            self._selected.remove(node)
        node.deselect()

    def add(self, node):
        """
        Add an already created node to the tree view. Use add_as_node instead to avoid tkinter parent
        issues.

        :param node: The child Node to be added to the Node
        """
        self.nodes.append(node)
        node.parent_node = self
        node.depth = self.depth + 1
        node.pack(side="top", fill="x", in_=self.body, pady=self.__class__.Node.PADDING)

    def add_as_node(self, **options) -> Node:
        """
        Adds a base node to the Tree. The node will belong to a subclass' Node definition if any.

        :param options: Options used in creating the node like name, icon e.t.c.
        :return: The created Node
        """
        # Use the Node definition of the object
        node = self.__class__.Node(self, **options)
        self.add(node)
        node.parent_node = self
        node.depth = self.depth + 1
        return node

    def allow_multi_select(self, flag):
        """
        Allow or disallow multiple widgets to be selected

        :param flag: Set to True to allow multiple items to be selected by the tree view and false to disable
          selection of multiple items.
        """
        self._multi_select = flag

    def remove(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
            node.pack_forget()

    def clear(self):
        nodes = list(self.nodes)
        for node in nodes:
            self.remove(node)

    def redraw(self):
        for node in self.nodes:
            node.pack_forget()
        for node in self.nodes:
            node.pack(side="top", fill="x", in_=self.body, pady=self.__class__.Node.PADDING)

    def insert(self, index=None, *nodes):
        if index is None:
            index = len(self.nodes)
        for node in nodes:
            node.remove()  # Remove node from whatever parent it belongs to
            self.nodes.insert(index, node)
            index += 1
            node.parent_node = self
            node.depth = self.depth + 1
        self.redraw()

    def on_select(self, listener, *args, **kwargs):
        self._on_select = lambda: listener(*args, **kwargs)

    def selection_changed(self):
        if self._on_select:
            self._on_select()

    def collapse_all(self):
        """
        Collapse all nodes and sub-nodes so that their sub-node are not displayed
        """
        for node in self.nodes:
            node.collapse_all()

    def expand_all(self):
        """
        Expand all nodes and sub-nodes so that their sub-nodes are displayed
        """
        for node in self.nodes:
            node.expand_all()

    def selected_count(self) -> int:
        """
        Return the total number of items currently selected usually 1 if multi-select is disabled.

        :return: total number of items selected
        """
        return len(self._selected)


class PanedWindow(Widget, tk.PanedWindow):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, **cnf)
        self.config(**self.style.pane)


class ProgressBar(Widget, tk.Canvas):
    """
    Custom progress bar for use by hoverset applications
    """
    DETERMINATE = 'determinate'
    INDETERMINATE = 'indeterminate'
    DEFAULT_INTERVAL = 20

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.configure(**self.style.highlight_dim, height=3, **self.style.surface)
        self._bar_color = self.style.colors.get("accent")
        self._progress = 0
        self._bar = self.create_rectangle(0, 0, 0, 0)
        self._indeterminate = False
        self._step_var = 0
        self._direction = 1
        self._interval = self.DEFAULT_INTERVAL
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.update_idletasks()
        if self._indeterminate:
            try:
                # Sometimes the after event gets called after widget is deleted
                # If someone is able to fix this more elegantly code away
                width = (0.3 + self._step_var / self.winfo_width() * 0.8) * self.winfo_width()
            except tk.TclError:
                return
            self.coords(self._bar, self._step_var, 0, self._step_var + width, self.winfo_height())
            self._step_var += self._direction
            if self._step_var + width >= self.winfo_width():
                self._direction = -3
            elif self._step_var <= 0:
                self._direction = 3
            if event is None:
                self.master.after(self._interval, self._draw)
        else:
            self.coords(self._bar, 0, 0, self._progress * self.winfo_width(), self.winfo_height())
        self.itemconfigure(self._bar, fill=self._bar_color, width=0)

    def mode(self, value):
        """
        Set the mode of the progressbar to determinate or indeterminate

        :param value: constant value either ProgressBar.DETERMINATE or ProgressBar.INDETERMINATE
        """
        self._indeterminate = value == ProgressBar.INDETERMINATE
        self._draw()

    def interval(self, milliseconds):
        """
        Controls the speed of the indeterminate mode of the progressbar

        :param milliseconds: the update time in milliseconds, the smaller the faster
        """
        self._interval = milliseconds

    def set(self, value: float):
        """
        Sets the progress to a fraction value

        :param value: A floating point value between 0 and 1 inclusive which determines the progress
        """
        self._progress = value
        self._draw()

    def get(self):
        """
        Fetch the current progress of the bar.

        :return: a floating point from 0 to 1 representing current progress. If mode is set to
          indeterminate None is returned
        """
        if self._indeterminate:
            return None
        return self._progress

    def color(self, color):
        """
        Set the progress bar color

        :param color: A named color or hex defined color
        :raises: :class:`ValueError` if color is not a valid tk color
        """
        prev_color = self._bar_color
        self._bar_color = color
        try:
            self._draw()
        except tk.TclError:
            self._bar_color = prev_color
            self._draw()
            raise ValueError(f"{color} is not a valid tk color")


class Hyperlink(Label):
    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master)
        self.configure(**self.style.hyperlink, takefocus=True, **kwargs)
        self.font_ = font.Font(self, self.cget('font'))
        self.bind('<Enter>', lambda font_: self.font_.configure(underline=True))
        self.bind('<FocusIn>', lambda font_: self.font_.configure(underline=True))
        self.bind('<Leave>', lambda font_: self.font_.configure(underline=False))
        self.bind('<FocusOut>', lambda font_: self.font_.configure(underline=False))
        self.bind('<Return>', self._open_in_browser)
        self.bind('<Button-1>', self._open_in_browser)
        self.configure(font=self.font_)

    # TODO   Add the link to the hyperlink (override configure method)

    def _open_in_browser(self, event):
        if self['text']:
            webbrowser.open(self['text'])


class TabView(Frame):

    class Tab(Frame):
        def __init__(self, master, **cnf):
            super().__init__(master.tab_control)
            self._controller = master
            tab_style = dict(self.style.text)
            tab_style.update(cnf)
            self._label = Label(self, **tab_style, padx=10)
            self._label.pack(side="top", fill="x")
            self._highlight = Frame(self, height=2, **self.style.surface)
            self._highlight.pack(side="top", fill="x")
            self._label.bind("<Button-1>", lambda e: self._controller.select(self))

        def on_select(self):
            self._highlight.config(**self.style.accent)
            self._label.config(**self.style.hover)

        def on_deselect(self):
            self._highlight.config(**self.style.surface)
            self._label.config(**self.style.surface)

    def __init__(self, master):
        super().__init__(master)
        self.tab_control = Frame(self, **self.style.surface)
        self.tab_control.pack(side="top", fill="x")
        self.body = Frame(self, **self.style.surface)
        self.body.pack(fill="both")
        self._tabs = {}
        self._selected = None

    def _show(self, tab):
        tab.pack(side="left", fill="y")

    def add(self, widget, **cnf):
        tab = self.Tab(self, **cnf)
        self._show(tab)
        self._tabs[tab] = widget
        if len(self._tabs) == 1:
            self.select(tab)
        return tab

    def select(self, tab):
        if self._selected:
            self._tabs[self._selected].pack_forget()
            self._selected.on_deselect()
        self._tabs[tab].pack(fill="both", expand=True)
        tab.on_select()
        self._selected = tab


class Text(Widget, tk.Text):

    def __init__(self, master, **cnf):
        self.setup(master)
        super().__init__(master)
        default = self.style.textarea
        default.update(cnf)
        self.configure(**default)
        self._on_change = None
        self._last_edit_implicit = False
        self.bind("<<Modified>>", self._mod)

    def get_all(self):
        return str(self.get("1.0", tk.END)).strip()

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda: callback(*args, **kwargs)

    def _mod(self, *_):
        flag = self.edit_modified()
        # skip possible implicit modifications
        if flag and not self._last_edit_implicit:
            if self._on_change:
                self._on_change()
        self.edit_modified(False)
        self._last_edit_implicit = False

    def clear(self):
        self.delete("1.0", tk.END)

    def set(self, value):
        self.clear()
        super().insert("1.0", value)
        # this will suppress the next <<Modified>> event fired as a result
        self._last_edit_implicit = True


if __name__ == "__main__":
    r = Application()
    r.load_styles("themes/default.css")
    frame = Frame(r, bg="#5a5a5a", width=300, height=400)
    frame.pack(fill="both", expand=True)


    class CompoundItem(CompoundList.BaseItem):

        def render(self):
            Label(self, **self.style.text_accent_1, text=self.value).pack(side="top", anchor="w")
            Label(self, **self.style.text, text=len(self.value)).pack(side="top", anchor="w")


    box = CompoundList(frame)
    box.pack(fill="both", expand=True)
    box.set_item_class(CompoundItem)
    box.set_values(["this", "are", "samples", "its", "the", "dawn", "of", "a", "new", "era"])
    box.set_mode(CompoundList.MULTI_MODE)
    r.mainloop()
