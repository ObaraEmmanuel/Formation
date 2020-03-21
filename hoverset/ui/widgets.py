"""
Widget factory classes. This is the foundation of all GUI components used in hoverset.
You may ask, why rewrite say tkinter classes?
The answer is simple, we need a way to easily switch GUI frameworks in the future without
breaking functionality in the soon to grow hoverset app ecosystem
All gui manifestation should strictly use hoverset widget set for easy maintenance in the future
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import dataclasses
import functools
import logging
import tkinter as tk
import tkinter.tix as tix
import tkinter.ttk as ttk
from tkinter import font

from hoverset.ui.animation import Animate, Easing
from hoverset.ui.icons import get_icon
from hoverset.ui.styles import StyleDelegator
from hoverset.ui.windows import DragWindow


class FontStyle(font.Font):

    @staticmethod
    def families(root=None, displayof=None):
        return font.families(root, displayof)

    @staticmethod
    def nametofont(name):
        try:
            return font.nametofont(name)
        except tk.TclError:
            return None

    @staticmethod
    def names(root=None):
        return font.names(root)


class EventMask:
    """
    Event mask values to be used to test events occurring with these states set.
    To check whether control button was down just check whether:

    event.state & EventMask.CONTROL != 0

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


@dataclasses.dataclass
class EventWrap:
    x_root: int = 0
    y_root: int = 0
    x: int = 0
    y: int = 0


class WidgetError(tk.TclError):
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
    class_name = 'hover.{}'.format(widget.winfo_class())
    ttk_style.configure(class_name, **styles)
    widget.configure(style=class_name)


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
    allowed_styles = widget.config()
    cleaned_styles = {}
    for style in styles:
        if style in allowed_styles:
            cleaned_styles[style] = styles[style]
    return cleaned_styles


def system_fonts():
    fonts = sorted(list(font.families()))
    fonts = list(filter(lambda x: not x.startswith("@"), fonts))
    return fonts


class EditableMixin:
    """
    This mixin implements all methods applicable to all widgets that allow entry of data
    using the keyboard. All widgets that have such functionality should ensure they extend
    this mixin.
    """

    def set_validator(self, validator, *args, **kwargs) -> None:
        """
        Allows addition of realtime validation of data entered by the user to input widgets. This validation
        is carried out at the lowest level before the user interface even displays the value in the widget allowing
        invalid data to be blocked before it is ever displayed.
        :param validator: The validation method that accepts one argument which is the string to be validated. Such
        functions can be found or added at hoverset.util.validators
        :return: None
        """
        self.configure(validate='all',
                       validatecommand=(self.register(lambda val: validator(val, *args, **kwargs)), "%P")
                       )

    def on_change(self, callback, *args, **kwargs):
        """
        Set the callback when data in the input widget is changed either explicitly or implicitly.
        :param callback:
        :return:
        """
        self._var.trace("w", lambda *_: callback(*args, **kwargs))

    def on_entry(self, callback, *args, **kwargs):
        """
        Set the callback when data in the input widget is changed explicitly i.e when the user actually types values
        into the input widget.
        :param callback:
        :return:
        """
        # Capture typing event
        self.bind("<KeyRelease>", lambda *_: callback(*args, **kwargs))

    def disabled(self, flag):
        if flag:
            self.config(state='disabled')
        else:
            self.config(state='normal')


class ContextMenuMixin:
    _on_context_menu = None

    def make_menu(self, templates, parent=None, **cnf):
        """
        Create a menu object for the widget
        :param templates: a tuple of tuples of the format (type, label, icon, command, additional_configuration={})
        used to generate the menu. Repeat the same template format in the "menu" attribute in additional configurations
        for cascade menus
        :param parent: The parent of the menu. You will never need to set this attribute directly as it only exists
        for the purposes of recursion
        :param cnf:
        :return:
        """
        # If no style is provided use the default
        if not len(cnf):
            cnf = self.style.dark_context_menu
        parent = self if parent is None else parent
        menu = tk.Menu(parent, **cnf)
        # A holding array for for menu image items to hold out the garbage collector
        menu.images = []
        for template in templates:
            if template[0] == "separator":
                menu.add_separator()
            elif template[0] == "cascade":
                _type, label, icon, command, config = template
                # Create cascade menu recursively
                # create a new config copy to prevent messing with the template
                config = dict(**config)
                config["menu"] = self.make_menu(config.get("menu"), menu, **cnf)
                # Be careful we dont end up changing values in global style delegator. Don't assign directly
                conf = {**self.style.dark_context_menu_item}
                conf.update(config)
                menu.add_cascade(label=label, image=icon, command=command, compound='left', **conf)
                menu.images.append(icon)
            else:
                _type, label, icon, command, config = template
                conf = {**self.style.dark_context_menu_selectable} if _type in ("radiobutton", "checkbutton") else \
                    {**self.style.dark_context_menu_item}
                conf.update(config)
                menu.images.append(icon)
                menu.add(_type, label=label, image=icon, command=command, compound='left', **conf)

        return menu

    def set_up_context(self, templates, **cnf):
        """
        Set up a context menu using the template which is a tuple containing items in the format
        (type, label, icon, command, additional_configuration={})
        :param templates:
        :param cnf:
        :return:
        """
        self.context_menu = self.make_menu(templates, **cnf)
        self.bind_all("<Button-3>", lambda event: ContextMenuMixin.popup(event, self.context_menu), add='+')

    @staticmethod
    def popup(event, menu):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    @staticmethod
    def add_context_menu(menu, widget):
        widget.bind("<Button-3>", lambda event: ContextMenuMixin.popup(event, menu), add="+")


class ScrollableInterface:
    """
    Interface that allows widgets to be managed by the _MouseWheelDispatcherMixin which handles mousewheel
    events which may be tricky to handle at the widget level.
    """

    def on_mousewheel(self, event):
        raise NotImplementedError("on_mousewheel method is required")

    def scroll_position(self):
        # Return the scroll position to determine if we have reach the end of scroll so we can
        # pass the scrolling to the next widget under the cursor that can scroll
        raise NotImplementedError("Scroll position required for scroll transfer")

    def scroll_transfer(self) -> bool:
        # Override this method and return true to allow scroll transfers
        return False


class CenterWindowMixin:

    def enable_centering(self):
        self.centered = False
        self.bind('<Configure>', lambda _: self.center())
        self.event_generate('<Configure>')

    def center(self):
        if not self.centered:
            self.update_idletasks()
            x = int((self.position_ref.winfo_width() - self.winfo_width()) / 2) + self.position_ref.winfo_x()
            y = int((self.position_ref.winfo_height() - self.winfo_height()) / 2) + self.position_ref.winfo_y()
            self.geometry("+{}+{}".format(x, y))
            self.centered = True if self.winfo_width() != 1 else False

    def re_center(self):
        self.centered = False
        self.center()

    def force_center(self):
        self.centered = False
        self.center()


# noinspection PyTypeChecker
class Widget:
    """
    Base class for all hoverset widgets providing all methods common to all widgets
    """
    s_style = None  # Static style holder
    s_window = None  # Static window holder
    __readonly_options = {"class", "container"}

    def setup(self, _=None):
        """
        It performs the necessary dependency injection and event bindings and
        set up.
        :param _:
        :return:
        """
        self._allow_drag = False
        self._drag_setup = False

    @property
    def allow_drag(self):
        return self._allow_drag

    @allow_drag.setter
    def allow_drag(self, flag: bool):
        self._allow_drag = flag
        if self._allow_drag and not self._drag_setup:
            self.bind_all('<Motion>', self._drag_handler)
            self.bind_all('<ButtonRelease-1>', self._drag_handler)
            self._drag_setup = True

    def _drag_handler(self, event):
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
        :param context:
        :return:
        """
        logging.info(f"Accepted context {context}")

    def render_drag(self, window):
        """
        Override this method to create and position widgets on the drag shadow window
        :param window: The drag window provided by the drag manager that should be used as the widget master
        :return: None
        """
        tk.Label(window, text="Item", bg="#f7f7f7").pack()  # Default render

    def config_all(self, cnf=None, **kwargs):
        """
        A way to config all the children of a widget. Especially useful for compound widgets where styles need to be
        applied uniformly or following a custom approach to all contained child widgets. Override this method to
        customize its behaviour to suit your widget. It defaults to the normal config
        :param cnf:
        :param kwargs:
        :return:
        """
        self.config(cnf, **kwargs)

    def bind_all(self, sequence=None, func=None, add=None):
        """
        Total override of the tkinter bind_all method allowing events to be bounds to all the children of a widget.
        This is useful for compound widgets which need to behave as a single entity
        :param sequence: Event sequence
        :param func: Callback
        :param add:
        :return:
        """
        return self.bind(sequence, func, add)

    @property
    def width(self) -> int:
        """
        Wrapper property of the tk Misc class w.winfo_width() method for quick access to widget width property in pixels
        :return: int
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
            self.config(clean_styles(self, {"state": tk.DISABLED}))
        else:
            self.config(clean_styles(self, {"state": tk.NORMAL}))

    @staticmethod
    def event_in(event, widget):
        check = widget.winfo_containing(event.x_root, event.y_root)
        while not isinstance(check, Application) and check is not None:
            if check == widget:
                return True
            check = check.nametowidget(check.winfo_parent())
        return False

    @staticmethod
    def event_first(event, widget, class_: type, ignore=None):
        check = widget.winfo_containing(event.x_root, event.y_root)
        while not isinstance(check, Application) and check is not None:
            if isinstance(check, class_) and not check == ignore:
                return check
            check = check.nametowidget(check.winfo_parent())
        return None

    def absolute_bounds(self):
        self.update_idletasks()
        return (self.winfo_rootx(), self.winfo_rooty(),
                self.winfo_rootx() + self.width, self.winfo_rooty() + self.height)

    def on_drag_start(self, *args):
        pass

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
    the images to shield them from garbage collection.
    """

    def configure(self, cnf=None, **kw):
        cnf = {} if cnf is None else cnf
        cnf.update(kw)
        if cnf.get("image"):
            # If an image value is set, shield it from garbage collection by increasing its reference count
            self.image = cnf.get("image")
        return super().configure(cnf, **kw)

    def __setitem__(self, key, value):
        if key == "image":
            self.image = value
        super().__setitem__(key, value)


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
        self.setup(master)  # Dependency injection
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


class Frame(Widget, ContextMenuMixin, WindowMixin, tk.Frame, tk.Wm):

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)
        self.setup_window()
        self._style = self.winfo_toplevel().style
        self._on_click = None
        self.body = self
        # Since the frame may be a toplevel at some point we want the style variable to be from the initial parent

    @property
    def style(self):
        return self._style

    def clear_children(self):
        for child in self.winfo_children():
            child.pack_forget()
            child.grid_forget()
            child.place_forget()

    def bind_all(self, sequence=None, func=None, add=None):
        self.bind(sequence, func, add)
        for child in self.winfo_children():
            child.bind(sequence, func, add)

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
            child.config(**cnf)


class ScrolledFrame(Widget, ScrollableInterface, ContextMenuMixin, WindowMixin, tk.Frame, tk.Wm):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, **cnf)
        self.setup_window()
        self._style = self.winfo_toplevel().style
        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._canvas.config(cnf)
        self._canvas.config(self.style.dark)
        self._scroll_y = ttk.Scrollbar(self, orient='vertical', command=self._limit_y)  # use frame limiters
        self._scroll_x = ttk.Scrollbar(self, orient='horizontal', command=self._limit_x)
        self._canvas.grid(row=0, column=0, sticky='nswe')
        self.columnconfigure(0, weight=1)  # Ensure the _canvas gets the rest of the left horizontal space
        self.rowconfigure(0, weight=1)  # Ensure the _canvas gets the rest of the left vertical space
        self._canvas.config(yscrollcommand=self._scroll_y.set, xscrollcommand=self._scroll_x.set)  # attach scrollbars
        self.body = Frame(self._canvas, **cnf)
        self.body.config(self.style.dark)
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
            self._scroll_x.grid(row=1, column=0, columnspan=2, sticky='ew')
        elif not flag:
            self._scroll_x.grid_forget()
        self.update_idletasks()

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
        # TODO Add specialised mousewheel behaviour for the various platforms
        # Enable the scrollbar to be scrolled using mouse wheel
        # Occasionally throws unpredictable errors so we better wrap it up in a try block
        try:
            if self._scroll_y.winfo_ismapped():
                self._canvas.yview_scroll(-1 * int(event.delta / 50), "units")
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
        print("scrolling to start")
        self._canvas.yview_moveto(0.0)
        self._canvas.xview_moveto(0.0)


class Screen:
    """
    What can comfortably be considered a tkinter fashion window for the root window (Tk)
    This allows calculations for centering the window possible with reference to the whole screen
    """

    def __init__(self, window: tix.Tk):
        self.window = window

    def winfo_x(self):
        return 0

    def winfo_y(self):
        return 0

    def winfo_width(self):
        return self.window.winfo_screenwidth()

    def winfo_height(self):
        return self.window.winfo_screenheight()


class Application(Widget, CenterWindowMixin, _MouseWheelDispatcherMixin, ContextMenuMixin, tix.Tk):
    # We want to extend tix.Tk to broaden our widget scope because now we can use tix widgets!
    # This is inconsequential to other widgets as tix.Tk subclasses tkinter.tk which is the base class here
    # This class needs no dependency injection since its the source of the dependencies after all!

    def __init__(self, *args, **kwargs):
        Widget.s_window = self  # Window dependency set
        super().__init__(*args, **kwargs)
        self.position_ref = Screen(self)
        self.enable_centering()
        self.bind_all("<MouseWheel>", self._on_mousewheel, '+')
        self.drag_context = None
        self.drag_window = None

    def load_styles(self, path):
        """
        Accepts a path to a cascading style sheet containing the styles used by the widgets. The style dependency is
        loaded here
        :param path:
        :return:
        """
        self._style = StyleDelegator(path)

    @property
    def style(self):
        return self._style

    def bind_all(self, sequence=None, func=None, add="+"):
        return super(tix.Tk, self).bind_all(sequence, func, add)

    def unbind_all(self, sequence, func_id=None):
        for child in self.winfo_children():
            try:
                child.unbind(sequence, func_id)
            except tk.TclError:
                pass


class Window(Widget, CenterWindowMixin, WindowMixin, tix.Toplevel):

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
        self.wm_attributes('-toolwindow', True)

    def set_geometry(self, rec):
        logging.debug(f"placing window at {rec}")
        self.geometry("{}x{}+{}+{}".format(*rec))
        return self

    def show(self):
        """
        The window is initialized as invisible to allow you to set it up first. Call this method to make it visible
        :return:
        """
        self.wm_attributes('-alpha', 1.0)


class Canvas(Widget, ContextMenuMixin, tk.Canvas):

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)


class MenuButton(Widget, ImageCacheMixin, tk.Menubutton):

    def __init__(self, master=None, **kwargs):
        self.setup(master)
        super().__init__(master, **kwargs)


class Button(Frame):
    # For purposes of easy customization we saw it wise to extend the Label instead of the button
    # The default tkinter button implements a sunken relief on click that is rather ancient.
    # So we'd rather reinvent the wheel (Painful yes) but we can stay modern.
    # TODO Implement Repeat-delay functionality

    def __init__(self, master=None, **cnf):
        super().__init__(master)
        cnf = cnf if len(cnf) else self.style.dark_button
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

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.bind_all("<Button-1>", self.toggle)
        self.config_all(**self.style.dark_button)
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
        self.config_all(**self.style.dark_on_hover)
        self._selected = True

    def deselect(self):
        self.config_all(**self.style.dark_on_hover_ended)
        self._selected = False

    def on_click(self, callback, *args, **kwargs):
        super().on_click(callback, *args, **kwargs)
        self.bind_all("<Button-1>", self.toggle, '+')

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda value: func(value, *args, **kwargs)


class HorizontalScale(Widget, tk.Frame):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, cnf)
        self._frame = tk.Label(self)
        self._frame.pack(side="top", fill="x")
        self._label = tk.Label(self._frame)
        self._value = tk.Label(self._frame, width=5, anchor="e")
        self._value.pack(side="right")
        self._label.pack(side="left", fill="x")
        self.scale = ttk.Scale(self)
        self.scale.pack(fill="x", side="top")

    def get(self):
        return self.scale.get()

    def set(self, value):
        self.scale.set(value)

    def config_all(self, cnf=None, **kwargs):
        # We have to do this because it is not advisable to have mutable types(like {})  as default arguments!
        if cnf is None:
            cnf = {}
        cnf.update(kwargs)
        self.config(clean_styles(self, cnf))
        self._label.config(clean_styles(self._label, cnf))
        self._value.config(clean_styles(self._value, cnf))
        self._frame.config(clean_styles(self._frame, cnf))
        self.scale.config(clean_styles(self.scale, cnf))
        set_ttk_style(self.scale, cnf)

    def config_value(self, cnf=None, **kwargs):
        self._value.config(cnf, **kwargs)

    def config_label(self, cnf=None, **kwargs):
        self._label.config(cnf, **kwargs)

    def config_scale(self, cnf=None, **kwargs):
        self.scale.config(cnf, **kwargs)


class Popup(tix.Toplevel):

    def __init__(self, master, pos=None, **cnf):
        super().__init__(master, **cnf)
        if master:
            self.style = master.window.style
        if pos is not None:
            self.set_geometry(pos)
        self.window = self
        self._close_func = None
        self.config(**self.style.dark_highlight_active, **self.style.dark)
        self.overrideredirect(True)
        self.attributes("-topmost", 1)
        self._grabbed = self.grab_current()  # Store the widget that currently has the grab
        self.grab_set_global()  # Grab all events so we can tell whether someone is clicking outside the popup
        self.bind("<Button-1>", self._exit)
        self.body = self

    def _exit(self, event):
        if not Widget.event_in(event, self):
            # Someone has clicked outside the popup so close it
            self.destroy()

    @chain
    def set_geometry(self, rec):
        rec = rec[2], rec[3], rec[0], rec[1]
        try:
            self.geometry("{}x{}+{}+{}".format(*rec))
        except tk.TclError:
            pass

    def hide(self):
        self.attributes("-alpha", 0)

    def show(self):
        self.attributes("-alpha", 1)

    def destroy(self):
        self.grab_release()
        if self._grabbed:
            self._grabbed.grab_set()  # Return the grab to whichever widget had it if any
        super().destroy()
        if self._close_func is not None:
            self._close_func()

    def re_calibrate(self):
        pass

    def on_close(self, func, *args, **kwargs):
        self._close_func = lambda: func(*args, **kwargs)


class DrawOver(Frame):

    def __init__(self, master, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark_highlight_active, **self.style.dark)
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

    def post(self, widget, **kwargs):
        self.re_calibrate()
        side = kwargs.get("side", "auto")
        padding = kwargs.get("padding", 2)
        widget.update_idletasks()
        self.update_idletasks()
        x, y, width, height = widget.winfo_rootx(), widget.winfo_rooty(), widget.width, widget.height
        right = x
        left = x - self.width + width
        top = y - self.height - padding
        bottom = y + height + padding
        if side == "nw":
            self.set_geometry((left, top))
        elif side == "ne":
            self.set_geometry((right, top))
        elif side == "sw":
            self.set_geometry((left, bottom))
        elif side == "se":
            self.set_geometry((right, bottom))
        else:
            # i.e. side == "auto"
            win_bounds = self.window.absolute_bounds()
            offset_b = win_bounds[3] - bottom
            offset_t = y - win_bounds[1]
            offset_l = x + self.width - win_bounds[0]
            offset_r = win_bounds[2] - right
            x_pos = left if offset_l >= offset_r or offset_l > self.width else right
            y_pos = bottom if offset_b >= offset_t or offset_b > self.height else top
            self.set_geometry((x_pos, y_pos))


class CompoundList(ScrolledFrame):
    MULTI_MODE = 0x001
    SINGLE_MODE = 0x002
    BROWSE_MODE = 0x003

    class BaseItem(Frame):

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
                self.bind_all("<Button-1>", self.select_self)
            self.config_all(**self.style.dark)

        def render(self):
            self._text = Label(self, **self.style.dark_text, text=self._value, anchor="w")
            self._text.pack(fill="both")

        @property
        def value(self):
            return self._value

        def select_self(self, event=None, *_):
            self._parent.select(self._index, event)

        def select(self, *_):
            self._selected = True
            self.on_hover()

        def deselect(self):
            self._selected = False
            self.on_hover_ended()

        # We need to add implementation details separate from library user interference
        # Users are therefore free to override the non-private wrappers without breaking core functionality
        def _on_hover(self, *_):
            if self._parent.get_mode() == CompoundList.BROWSE_MODE:
                self._parent.select(self._index)
            else:
                self.on_hover(*_)

        def _on_hover_ended(self, *_):
            if not self._selected:
                self.on_hover_ended(*_)

        def on_hover(self, *_):
            self.config_all(**self.style.dark_on_hover)

        def on_hover_ended(self, *_):
            self.config_all(**self.style.dark_on_hover_ended)

        def get(self):
            return self._value

        def clone_to(self, parent):
            return self.__class__(parent, self._value, self._index, True)

    # ----------------------------------------- CompoundList -----------------------------------------------

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self._cls = CompoundList.BaseItem  # Default
        self._values = []
        self._current_indices = []
        self._items = []
        self._mode = CompoundList.SINGLE_MODE  # Default
        self.config(self.style.dark)
        self._on_change = None

    def set_mode(self, mode):
        self._mode = mode

    def get_mode(self):
        return self._mode

    def set_item_class(self, cls):
        self._cls = cls

    def class_in_use(self):
        return self._cls

    def set_values(self, values):
        self._values = values
        self._render(values)

    def _render(self, values):
        for i in range(len(values)):
            item = self._cls(self, values[i], i)
            self._items.append(item)
            item.pack(side="top", fill="x", pady=1)
            item.update_idletasks()

    def add_values(self, values):
        self._values += values
        self._render(values)

    def select(self, index, event=None):
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
        if self._mode == CompoundList.MULTI_MODE:
            return [self._items[index] for index in self._current_indices]
        elif len(self._current_indices):
            return self._items[self._current_indices[0]]
        else:
            return None

    def on_change(self, func, *args, **kwargs):
        self._on_change = lambda value: func(value, *args, **kwargs)


class Spinner(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master)
        self._button = Button(self, **self.style.dark_button, text=get_icon("triangle_down"), width=20, anchor="center")
        self._button.pack(side="right", fill="y")
        self._button.on_click(self._popup)
        self._entry = Frame(self, **self.style.dark)
        self._entry.body = self._entry
        self._entry.pack(side="left", fill="both", expand=True)
        # self._entry.pack_propagate(0)
        self.config(**self.style.dark_highlight_active)
        self._popup_window = None
        self._on_create_func = None
        self._on_change = None
        self._values = []
        self._value_item = None
        self._item_cls = CompoundList.BaseItem
        self.dropdown_height = 150

    def _popup(self, event=None):
        if self._popup_window is not None:
            self._popup_window.destroy()
            self._button.config(text=get_icon("triangle_down"))
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
        self._button.config(text=get_icon("triangle_up"))
        popup.on_close(self._close_popup)

    def _close_popup(self):
        # self._popup_window = None
        # This fails at times during program close up
        try:
            self._button.config(text=get_icon("triangle_down"))
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
        self._values = tuple(values)
        if len(values):
            self.set(values[0])

    def add_values(self, *values):
        self._values += values

    def remove_value(self, value):
        self._values.remove(value)

    def set(self, value):
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
        if self._value_item.get() is None:
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
        EXPANDED_ICON = get_icon("chevron_down")
        COLLAPSED_ICON = get_icon("chevron_right")
        PADDING = 1

        def __init__(self, master=None, **config):
            super().__init__(master.body)
            self.config(**self.style.dark)
            self.tree = master
            self._icon = config.get("icon", get_icon("data"))
            self._name = config.get("name", "unknown")
            self.strip = f = TreeView.Strip(self, **self.style.dark, takefocus=True)
            f.pack(side="top", fill="x")
            self.expander = Label(f, **self.style.dark_text, text=" " * 4)
            self.expander.pack(side="left")
            self.expander.bind("<Button-1>", self.toggle)
            self.strip.bind("<FocusIn>", self.select)
            self.strip.bind("<Up>", self.select_prev)
            self.strip.bind("<Down>", self.select_next)
            self.icon_pad = Label(f, **self.style.dark_text, text=self._icon)
            self.icon_pad.pack(side="left")
            self.name_pad = Label(f, **self.style.dark_text, text=self._name)
            self.name_pad.pack(side="left", fill="x")
            self.name_pad.bind("<Button-1>", self.select)
            self.strip.bind("<Button-1>", self.select)
            self.body = Frame(self, **self.style.dark)
            self.body.pack(side="top", fill="x")
            self._expanded = False
            self._selected = False
            self.depth = 0  # Will be set on addition to a node or tree so this value is just placeholder
            self.parent_node = None
            self.nodes = []

        @property
        def name(self):
            return self.name_pad["text"]

        def bind_all(self, sequence=None, func=None, add=None):
            # The strip is pretty much the handle for the Node so better bind events here
            self.strip.bind(sequence, func, add)
            for child in self.strip.winfo_children():
                child.bind(sequence, func, add)

        def _set_expander(self, text):
            if text:
                self.expander.config(text=text)
            else:
                self.expander.config(text=" " * 4)

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
            if event and event.state & EventMask.CONTROL:
                self.tree.toggle_from_selection(self)
                return
            elif event:
                self.tree.select(self)
            else:
                self.tree.add_to_selection(self, silently)

            self.strip.config_all(**self.style.dark_on_hover)
            self._selected = True

        def deselect(self, *_):
            self.strip.config_all(**self.style.dark)
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
                node.pack(in_=self.body, fill="x", side="top", padx=18, pady=self.PADDING)
            else:
                self._set_expander(self.COLLAPSED_ICON)

        def insert_after(self, *nodes):
            """
            Insert the nodes immediately after this node in the same parent
            :param nodes: List of nodes to be inserted
            :return:
            """
            self.parent_node.insert(self.parent_node.nodes.index(self) + 1, *nodes)

        def insert_before(self, *nodes):
            """
            Insert the nodes immediately before this node in the same parent
            :param nodes: List of nodes to be inserted
            :return:
            """
            self.parent_node.insert(self.index(), *nodes)

        def insert(self, index=None, *nodes):
            """
            Insert all child nodes passed into parent node starting from the given index
            :param index: int representing the index from which to insert
            :param nodes: Child nodes to be inserted
            :return: None
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
                    self._set_expander(False)

        def expand(self):
            if len(self.nodes) == 0:
                # There is nothing to expand
                return
            self.pack_propagate(True)
            for node in self.nodes:
                node.pack(in_=self.body, fill="x", side="top", padx=18, pady=self.PADDING)
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
            :param _:
            :return: None
            """
            if self._expanded:
                self.collapse()
            else:
                self.expand()

    # ============================================= TreeView ================================================

    def __init__(self, master=None, **config):
        super().__init__(master, **config)
        self.config(**self.style.dark)
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
        :param n: Node
        :return: None
        """
        for node in self._selected:
            node.deselect()
        self._selected = [n]
        if not silently:
            self.selection_changed()

    def clear_selection(self):
        """
        Deselect all currently selected nodes
        :return:
        """
        for node in self._selected:
            node.deselect()
        self._selected = []
        self.selection_changed()

    def get(self):
        """
        Get the currently selected node if multi select is set to False and a list of all selected items if multi
        select is set to True. Returns None if no item is selected.
        :return:
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
        :return:
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
        :param flag: Set to True to allow multiple items to be selected by the tree view and false to disable
        selection of multiple items.
        :return:
        """
        self._multi_select = flag

    def remove(self, node):
        self.nodes.remove(node)
        node.pack_forget()

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
        Collapse all nodes and sub-nodes
        :return:
        """
        for node in self.nodes:
            node.collapse_all()

    def expand_all(self):
        """
        Expand all nodes and sub-nodes
        :return:
        """
        for node in self.nodes:
            node.expand_all()

    def selected_count(self) -> int:
        """
        Return the total number of items currently selected usually 1 if multi-select is disabled.
        :return: an int representing item count
        """
        return len(self._selected)


class PanedWindow(Widget, tk.PanedWindow):

    def __init__(self, master=None, **cnf):
        self.setup(master)
        super().__init__(master, **cnf)
        self.config(**self.style.dark_pane)


if __name__ == "__main__":
    r = Application()
    r.load_styles("themes/default.css")
    frame = Frame(r, bg="#5a5a5a", width=300, height=400)
    frame.pack(fill="both", expand=True)


    class CompoundItem(CompoundList.BaseItem):

        def render(self):
            Label(self, **self.style.dark_text_accent_1, text=self.value).pack(side="top", anchor="w")
            Label(self, **self.style.dark_text, text=len(self.value)).pack(side="top", anchor="w")


    box = CompoundList(frame)
    box.pack(fill="both", expand=True)
    box.set_item_class(CompoundItem)
    box.set_values(["this", "are", "samples", "its", "the", "dawn", "of", "a", "new", "era"])
    box.set_mode(CompoundList.MULTI_MODE)
    r.mainloop()
