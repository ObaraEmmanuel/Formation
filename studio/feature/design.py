"""
Drag drop designer for the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from tkinter import filedialog

from hoverset.data import actions
from hoverset.data.keymap import KeyMap
from hoverset.data.images import get_tk_image
from hoverset.ui.widgets import Label
from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.menu import MenuUtils, LoadLater
from hoverset.util.execution import Action, as_thread
from studio.lib.layouts import FrameLayoutStrategy
from studio.lib.pseudo import PseudoWidget, Container, Groups
from studio.parsers.xml import XMLForm
from studio.ui import geometry
from studio.ui.highlight import HighLight
from studio.ui.widgets import DesignPad, CoordinateIndicator
from studio.tools import ToolManager
from formation.xml import BaseConverter


class DesignLayoutStrategy(FrameLayoutStrategy):

    def add_new(self, widget, x, y):
        self.container.add(widget, x, y, layout=self.container)

    def _move(self, widget, bounds):
        self.container.position(widget, self.container.canvas_bounds(bounds))

    def add_widget(self, widget, bounds=None, **kwargs):
        super(FrameLayoutStrategy, self).add_widget(widget, bounds=None, **kwargs)
        super(FrameLayoutStrategy, self).remove_widget(widget)
        if bounds is None:
            x = kwargs.get("x", 10)
            y = kwargs.get("y", 10)
            width = kwargs.get("width", 20)
            height = kwargs.get("height", 20)
            self.container.place_child(widget, x=x, y=y, width=width, height=height)
        else:
            x1, y1, x2, y2 = self.container.canvas_bounds(bounds)
            self.container.place_child(widget, x=x1, y=y1, width=x2 - x1, height=y2 - y1)
        self.children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        self.container.forget_child(widget)

    def apply(self, prop, value, widget):
        if value == '':
            return
        self.container.config_child(widget, **{prop: value})

    def restore_widget(self, widget, data=None):
        data = self._restoration_data[widget] if data is None else data
        self.children.append(widget)
        widget.layout = self.container
        widget.level = self.level + 1
        self.container.place_child(widget, **data)

    def get_restore(self, widget):
        return self.container.config_child(widget)

    def definition_for(self, widget):
        definition = super().definition_for(widget)
        bounds = self.container.bbox(widget)
        definition["x"]["value"] = bounds[0]
        definition["y"]["value"] = bounds[1]
        # bordermode is not supported in design pad so simply set value to the default 'inside'
        definition["bordermode"]["value"] = 'inside'
        return definition


class Designer(DesignPad, Container):
    MOVE = 0x2
    RESIZE = 0x3
    name = "Designer"
    pane = None

    def __init__(self, master, studio):
        super().__init__(master)
        self.id = None
        self.setup_widget()
        self.parent = self
        self.studio = studio
        self.config(**self.style.bright, takefocus=True)
        self.objects = []
        self.root_obj = None
        self.layout_strategy = DesignLayoutStrategy(self)
        self.highlight = HighLight(self)
        self.highlight.on_resize(self._on_size_changed)
        self.highlight.on_move(self._on_move)
        self.highlight.on_release(self._on_release)
        self._update_throttling()
        self.studio.pref.add_listener(
            "designer::frame_skip",
            self._update_throttling
        )
        self.current_obj = None
        self.current_container = None
        self.current_action = None
        self._frame.bind("<Button-1>", lambda *_: self.focus_set())
        self._frame.bind('<Motion>', self.on_motion, '+')
        self._padding = 30
        self.design_path = None
        self.xml = XMLForm(self)
        self._load_progress = None
        self._shortcut_mgr = KeyMap(self._frame)
        self._set_shortcuts()
        self._last_click_pos = None
        # create the dynamic menu
        self._context_menu = MenuUtils.make_dynamic(
            self.studio.menu_template +
            ToolManager.get_tool_menu(self.studio) +
            (LoadLater(lambda: self.current_obj.create_menu() if self.current_obj else ()),),
            self.studio,
            self.style
        )
        self._coord_indicator = self.studio.install_status_widget(CoordinateIndicator)
        self._empty = Label(
            self,
            image=get_tk_image("paint", 30, 30), compound="top",
            text="Drag a container here to start",
            **self.style.dark_text_passive,
        )
        self._empty.config(**self.style.bright)
        self._show_empty(True)

    def focus_set(self):
        self._frame.focus_force()

    def _update_throttling(self, *_):
        self.highlight.set_skip_max(self.studio.pref.get("designer::frame_skip"))

    def _show_empty(self, flag):
        if flag:
            self._empty.place(relwidth=1, relheight=1)
        else:
            self._empty.place_forget()

    def _set_shortcuts(self):
        shortcut_mgr = self._shortcut_mgr
        shortcut_mgr.bind()
        shortcut_mgr.add_routines(
            actions.get('STUDIO_COPY'),
            actions.get('STUDIO_CUT'),
            actions.get('STUDIO_DELETE'),
            actions.get('STUDIO_PASTE'),
        )
        # allow control of widget position using arrow keys
        shortcut_mgr.add_shortcut(
            (lambda: self.displace('right'), KeyMap.RIGHT),
            (lambda: self.displace('left'), KeyMap.LEFT),
            (lambda: self.displace('up'), KeyMap.UP),
            (lambda: self.displace('down'), KeyMap.DOWN),
        )

    def _open_default(self):
        self.update_idletasks()
        from studio.lib import legacy
        self.add(legacy.Frame, self._padding, self._padding, width=self.width - self._padding * 2,
                 height=self.height - self._padding * 2)
        self.xml.generate()
        self.design_path = None

    @property
    def _ids(self):
        return [i.id for i in self.objects]

    def has_changed(self):
        # check if design has changed since last save or loading so we can prompt user to save changes
        xml = self.xml
        if self.root_obj:
            xml = XMLForm(self)
            xml.generate()
        return xml != self.xml

    def open_new(self):
        # open a blank design
        self.open_xml(None)

    def to_xml(self):
        """ Generate xml form of current design state without needing to save"""
        xml = XMLForm(self)
        xml.generate()
        return xml.root

    def save_prompt(self):
        return MessageDialog.builder(
            {"text": "Save", "value": True, "focus": True},
            {"text": "Don't save", "value": False},
            {"text": "Cancel", "value": None},
            wait=True,
            title="Save design",
            message="This design has unsaved changes. Do you want to save them?",
            parent=self.studio,
            icon=MessageDialog.ICON_INFO
        )

    def open_xml(self, path=None):
        if self.has_changed():
            save = self.save_prompt()
            if save:
                # user opted to save
                saved_to = self.save()
                if saved_to is None:
                    # User did not complete saving and opted to cancel
                    return
            elif save is None:
                # user made no choice or basically selected cancel
                return
        self.clear()
        # inform the studio about the session clearing
        self.studio.on_session_clear(self)
        if path:
            self.xml = XMLForm(self)
            self._load_design(path)
        else:
            # if no path is supplied the default behaviour is to open a blank design
            self._open_default()

    def clear(self):
        # Warning: this method deletes elements irreversibly
        # remove the current root objects and their descendants
        self.studio.select(None)
        # create a copy since self.objects will mostly change during iteration
        # remove root and dangling objects
        for widget in self.objects:
            widget.destroy()
        self.objects.clear()
        self.root_obj = None

    @as_thread
    def _load_design(self, path):
        # Loading designs is elaborate so better do it on its own thread
        self._load_progress = MessageDialog.show_progress(
            mode=MessageDialog.INDETERMINATE,
            message='Loading design file to studio...',
            parent=self.studio
        )
        # Capture any errors that occur while loading
        # This helps the user single out syntax errors and other value errors
        try:
            with open(path, 'rb') as dump:
                self.root_obj = self.xml.load_xml(dump, self)
                # store the file hash so we can check for changes later
                self.design_path = path
        except Exception as e:
            MessageDialog.show_error(parent=self.studio, title='Error loading design', message=str(e))
        finally:
            if self._load_progress:
                self._load_progress.destroy()
                self._load_progress = None

    def save(self, new_path=False):
        self.xml.generate()
        if not self.design_path or new_path:
            path = filedialog.asksaveasfilename(parent=self, filetypes=[("XML", "*.xml")],
                                                defaultextension='.xml')
            if not path:
                return None
            self.design_path = path
        with open(self.design_path, 'w') as dump:
            dump.write(self.xml.to_xml(
                self.studio.pref.get("designer::xml::pretty_print")
            ))
        return self.design_path

    def as_xml_node(self, widget):
        xml = self.xml
        if xml is None:
            xml = XMLForm(self)
        return xml.to_xml_tree(widget)

    def paste(self, node, silently=False):
        if not self.current_obj:
            return
        layout = self.current_obj if isinstance(self.current_obj, Container) else self.current_obj.layout
        width = int(BaseConverter.get_attr(node, "width", "layout") or 0)
        height = int(BaseConverter.get_attr(node, "height", "layout") or 0)
        x, y = self._last_click_pos or (self.winfo_rootx() + 50, self.winfo_rooty() + 50)
        self._last_click_pos = x + 5, y + 5  # slightly displace click position so multiple pastes are still visible
        bounds = geometry.resolve_bounds((x, y, x + width, y + height), self)
        obj = self.xml.load_section(node, layout, bounds)
        restore_point = layout.get_restore(obj)
        # Create an undo redo point if add is not silent
        if not silently:
            self.studio.new_action(Action(
                # Delete silently to prevent adding the event to the undo/redo stack
                lambda: self.delete(obj, True),
                lambda: self.restore(obj, restore_point, obj.layout)
            ))
        return obj

    def _get_unique(self, obj_class):
        """
        Generate a unique id for widget belonging to a given class
        """
        # start from 1 and check if name exists, if it exists keep incrementing
        count = 1
        name = f"{obj_class.display_name}_{count}"
        while name in self._ids:
            name = f"{obj_class.display_name}_{count}"
            count += 1
        return name

    def on_motion(self, event):
        self.highlight.resize(event)
        geometry.make_event_relative(event, self)
        self._coord_indicator.set_coord(
            self._frame.canvasx(event.x),
            self._frame.canvasy(event.y)
        )

    def _attach(self, obj):
        # bind events for context menu and object selection
        # all widget additions call this method so clear empty message
        self._show_empty(False)
        obj.bind("<Button-3>", lambda e: self.show_menu(e, obj), add='+')
        obj.bind('<Shift-ButtonPress-1>', lambda e: self.highlight.set_function(self.highlight.move, e), add='+')
        obj.bind('<Motion>', self.on_motion, '+')
        obj.bind('<ButtonRelease>', self.highlight.clear_resize, '+')
        self.objects.append(obj)
        if self.root_obj is None:
            self.root_obj = obj
        obj.bind("<Button-1>", lambda e: self._handle_select(obj, e), add='+')
        # bind shortcuts
        self._shortcut_mgr.bind_widget(obj)

    def show_menu(self, event, obj=None):
        # select object generating the context menu event first
        if obj is not None:
            self.select(obj)
        MenuUtils.popup(event, self._context_menu)

    def _handle_select(self, obj, event):
        # store the click position for effective widget pasting
        self._last_click_pos = event.x_root, event.y_root
        self.select(obj)

    def load(self, obj_class, name, container, attributes, layout, bounds=None):
        obj = obj_class(self, name)
        obj.configure(**attributes)
        self._attach(obj)
        if bounds is not None:
            container.add_widget(obj, bounds)
        else:
            container.add_widget(obj, **layout)
        if container == self:
            container = None
        self.studio.add(obj, container)
        return obj

    def _show_root_widget_warning(self):
        MessageDialog.show_warning(title='Invalid root widget', parent=self.studio,
                                   message='Only containers are allowed as root widgets')

    def add(self, obj_class: PseudoWidget.__class__, x, y, **kwargs):
        if obj_class.group != Groups.container and self.root_obj is None:
            # We only need a container as the root widget
            self._show_root_widget_warning()
            return
        width = kwargs.get("width", 55)
        height = kwargs.get("height", 30)
        silent = kwargs.get("silently", False)
        name = self._get_unique(obj_class)
        obj = obj_class(self, name)
        obj.layout = kwargs.get("intended_layout", None)
        self._attach(obj)  # apply extra bindings required
        layout = kwargs.get("layout")
        # If the object has a layout which actually the layout at the point of creation prepare and pass it
        # to the layout
        if isinstance(layout, Container):
            bounds = (x, y, x + width, y + height)
            bounds = geometry.resolve_bounds(bounds, self)
            layout.add_widget(obj, bounds)
            self.studio.add(obj, layout)
            restore_point = layout.get_restore(obj)
            # Create an undo redo point if add is not silent
            if not silent:
                self.studio.new_action(Action(
                    # Delete silently to prevent adding the event to the undo/redo stack
                    lambda: self.delete(obj, True),
                    lambda: self.restore(obj, restore_point, obj.layout)
                ))
        elif obj.layout is None:
            # This only happens when adding the main layout. We dont need to add this action to the undo/redo stack
            # This main layout is attached directly to the designer
            obj.layout = self
            self.layout_strategy.add_widget(obj, x=x, y=y, width=width, height=height)
            self.studio.add(obj, None)

        return obj

    def select_layout(self, layout: Container):
        pass

    def restore(self, widget, restore_point, container):
        container.restore_widget(widget, restore_point)
        self.studio.on_restore(widget)
        self._replace_all(widget)

    def _replace_all(self, widget):
        # Recursively add widget and all its children to objects
        self.objects.append(widget)
        if self.root_obj is None:
            self.root_obj = widget
        if isinstance(widget, Container):
            for child in widget._children:
                self._replace_all(child)

    def delete(self, widget, silently=False):
        if not widget:
            return
        if not silently:
            restore_point = widget.layout.get_restore(widget)
            self.studio.new_action(Action(
                lambda: self.restore(widget, restore_point, widget.layout),
                lambda: self.studio.delete(widget)
            ))
        else:
            self.studio.delete(widget, self)
        widget.layout.remove_widget(widget)
        if widget == self.root_obj:
            # try finding another toplevel widget that can be a root obj otherwise leave it as none
            self.root_obj = None
            for w in self.layout_strategy.children:
                if isinstance(w, Container):
                    self.root_obj = w
                    break
        self._uproot_widget(widget)

    def _uproot_widget(self, widget):
        # Recursively remove widgets and all its children
        if widget in self.objects:
            self.objects.remove(widget)
        if isinstance(widget, Container):
            for child in widget._children:
                self._uproot_widget(child)

    def react(self, event):
        layout = self.event_first(event, self, Container, ignore=self)
        if self.current_container is not None:
            self.current_container.clear_highlight()
            self.current_container = None
        if isinstance(layout, Container):
            self.current_container = layout
            layout.react_to_pos(event.x_root, event.y_root)
            layout.show_highlight()

    def compute_overlap(self, bound1, bound2):
        return geometry.compute_overlap(bound1, bound2)

    def layout_at(self, bounds):
        for container in sorted(filter(lambda x: isinstance(x, Container) and x != self.current_obj, self.objects),
                                key=lambda x: len(self.objects) - x.level):
            if isinstance(self.current_obj, Container) and self.current_obj.level < container.level:
                continue
            if self.compute_overlap(geometry.bounds(container), bounds):
                return container
        return None

    def parse_bounds(self, bounds):
        return {
            "x": bounds[0],
            "y": bounds[1],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }

    def position(self, widget, bounds):
        self.place_child(widget, **self.parse_bounds(bounds))

    def select(self, obj, explicit=False):
        if obj is None:
            self.clear_obj_highlight()
            self.studio.select(None, self)
            self.highlight.clear()
            return
        self.focus_set()
        if self.current_obj == obj:
            return
        self.clear_obj_highlight()
        self.current_obj = obj
        self.draw_highlight(obj)
        if not explicit:
            # The event is originating from the designer
            self.studio.select(obj, self)

    def draw_highlight(self, obj):
        self.highlight.surround(obj)

    def displace(self, side):
        if not self.current_obj:
            return
        bounds = geometry.bounds(self.current_obj)
        x1, y1, x2, y2 = bounds
        if side == 'right':
            bounds = x1 + 1, y1, x2 + 1, y2
        elif side == 'left':
            bounds = x1 - 1, y1, x2 - 1, y2
        elif side == 'up':
            bounds = x1, y1 - 1, x2, y2 - 1
        elif side == 'down':
            bounds = x1, y1 + 1, x2, y2 + 1
        self._on_move(bounds)
        self._on_release(bounds)

    def clear_obj_highlight(self):
        if self.highlight is not None:
            self.highlight.clear()
            self.current_obj = None
            if self.current_container is not None:
                self.current_container.clear_highlight()
                self.current_container = None

    def _on_release(self, bound):
        obj = self.current_obj
        container = self.current_container
        if obj is None:
            return
        if container is not None and container != obj:
            container.clear_highlight()
            if self.current_action == self.MOVE:
                container.add_widget(obj, bound)
                # If the enclosed widget was initially the root object, make the container the new root object
                if obj == self.root_obj and obj != self:
                    self.root_obj = self.current_container
            else:
                obj.layout.widget_released(obj)
            self.studio.widget_layout_changed(obj)
            self.current_action = None
        elif self.current_action == self.RESIZE:
            obj.layout.widget_released(obj)
            self.current_action = None

    def create_restore(self, widget):
        restore_point = widget.layout.get_restore()
        self.studio.new_action(Action(
            lambda: self.restore(widget, restore_point, widget.layout),
            lambda: self.studio.delete(widget)
        ))

    def _on_move(self, new_bound):
        obj = self.current_obj
        current_container = self.current_container
        if obj is None:
            return
        self.current_action = self.MOVE
        container: Container = self.layout_at(new_bound)
        if container is not None and obj != container:
            if container != current_container:
                if current_container is not None:
                    current_container.clear_highlight()
                container.show_highlight()
                self.current_container = container
            container.move_widget(obj, new_bound)
        else:
            if current_container is not None:
                current_container.clear_highlight()
                self.current_container = self
            obj.level = 0
            obj.layout = self
            self.move_widget(obj, new_bound)
        if obj.layout.layout_strategy.realtime_support:
            self.studio.widget_layout_changed(obj)

    def _on_size_changed(self, new_bound):
        obj = self.current_obj
        if obj is None:
            return
        self.current_action = self.RESIZE
        if isinstance(obj.layout, Container):
            obj.layout.resize_widget(obj, new_bound)

        if obj.layout.layout_strategy.realtime_support:
            self.studio.widget_layout_changed(obj)

    def on_select(self, widget):
        self.select(widget)

    def on_widget_change(self, old_widget, new_widget=None):
        pass

    def on_widget_add(self, widget, parent):
        pass

    def show_highlight(self, *_):
        pass

    def on_app_close(self):
        if self.has_changed():
            save = self.save_prompt()
            if save:
                self.save()
            elif save is None:
                return False
        return True
