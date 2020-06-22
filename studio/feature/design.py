"""
Drag drop designer for the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from hashlib import md5
from tkinter import filedialog

from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.widgets import Frame
from hoverset.util.execution import Action, as_thread
from studio.lib.layouts import FrameLayoutStrategy
from studio.lib.pseudo import PseudoWidget, Container, Groups
from studio.parsers.xml import XMLForm
from studio.ui import geometry
from studio.ui.highlight import HighLight
from studio.ui.widgets import DesignPad


class DesignLayoutStrategy(FrameLayoutStrategy):

    def add_new(self, widget, x, y):
        self.container.add(widget, x, y, layout=self.container)

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
            x1, y1, x2, y2 = bounds
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
        # bordermode is not supported in design pad so simply set value to the default 'inside'
        bounds = geometry.relative_bounds(geometry.bounds(widget), widget.layout)
        definition["x"]["value"] = bounds[0]
        definition["y"]["value"] = bounds[1]
        definition["bordermode"]["value"] = 'inside'
        return definition


class Designer(DesignPad, Container):
    MOVE = 0x2
    RESIZE = 0x3
    name = "Designer"
    side = "center"
    pane = None

    def __init__(self, master, studio):
        super().__init__(master)
        self.id = None
        self.setup_widget()
        self.parent = self
        self.studio = studio
        self.config(**self.style.bright)
        self.objects = []
        self.root_obj = None
        self.layout_strategy = DesignLayoutStrategy(self)
        self.highlight = HighLight(self)
        self.highlight.on_resize(self._on_size_changed)
        self.highlight.on_move(self._on_move)
        self.highlight.on_release(self._on_release)
        self.current_obj = None
        self.current_container = None
        self.current_action = None
        self.bind("<Button-1>", lambda *_: self.select(None))
        self._padding = 30
        self.design_path = None
        self.xml = None
        self.file_hash = None
        # Initialize the first layout some time after the designer has been initialized
        self.bind('<Configure>', lambda _: self.adjust_highlight(self.current_obj), add='+')

    def _open_default(self):
        self.update_idletasks()
        self.xml = XMLForm(self)
        from studio.lib import legacy
        self.add(legacy.Frame, self._padding, self._padding, width=self.width - self._padding * 2,
                 height=self.height - self._padding * 2)
        self.xml.generate()
        self.file_hash = md5(self.xml.to_xml_bytes()).hexdigest()
        self.design_path = None

    @property
    def _ids(self):
        return [i.id for i in self.objects]

    def has_changed(self):
        # check if design has changed since last save or loading so we can prompt user to save changes
        if self.root_obj:
            xml = XMLForm(self)
            xml.generate()
            _hash = md5(xml.to_xml_bytes()).hexdigest()
        else:
            _hash = None
        return _hash != self.file_hash

    def open_new(self):
        # open a blank design
        self.open_xml(None)

    def open_xml(self, path=None):
        if self.has_changed():
            save = MessageDialog.builder(
                {"text": "Save", "value": True, "focus": True},
                {"text": "Don't save", "value": False},
                {"text": "Cancel", "value": None},
                wait=True,
                title="Save design",
                message="This design has unsaved changes. Do you want to save them?",
                parent=self.studio,
                icon=MessageDialog.ICON_WARNING
            )
            if save:
                # user opted to save
                self.save()
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
        objects = list(self.objects)
        for widget in objects:
            self.delete(widget, silently=True)
            widget.destroy()
        self.objects.clear()
        self.root_obj = None

    @as_thread
    def _load_design(self, path):
        # Loading designs is elaborate so better do it on its own thread
        progress = MessageDialog.show_progress(
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
                self.file_hash = md5(self.xml.to_xml_bytes()).hexdigest()
                self.design_path = path
        except Exception as e:
            progress.destroy()
            MessageDialog.show_error(parent=self.studio, title='Error loading design', message=str(e))
        else:
            progress.destroy()

    def save(self, new_path=False):
        self.xml = XMLForm(self)
        self.xml.generate()
        if not self.design_path or new_path:
            path = filedialog.asksaveasfilename(parent=self, filetypes=[("XML", "*.xml")],
                                                defaultextension='.xml')
            if not path:
                return
            self.design_path = path
        with open(self.design_path, 'w') as dump:
            dump.write(self.xml.to_xml())
        self.file_hash = md5(self.xml.to_xml_bytes()).hexdigest()
        return self.design_path

    def to_xml(self):
        # TODO remove this method; was meant for testing
        xml = XMLForm(self)
        xml.generate()
        return xml.root

    def paste(self, widget: PseudoWidget):
        if not self.current_obj:
            return
        layout = self.current_obj if isinstance(self.current_obj, Container) else self.current_obj.layout
        width, height = widget.winfo_width(), widget.winfo_height()
        x, y = self.current_obj.last_menu_position
        obj = self.add(widget.__class__, x, y, width=width, height=height, template=widget,
                       layout=layout)
        Frame.copy_config(widget, obj)
        if isinstance(widget, Container):
            obj._switch_layout(widget.layout_strategy.__class__)
            for child in widget._children:
                # Prevent an endless paste loop if we are pasting the object into itself
                if child != obj:
                    self._deep_paste(child, obj)
        return obj

    def _deep_paste(self, widget: PseudoWidget, layout: Container):
        widget_copy = self.add(widget.__class__, 0, 0, width=0, height=0, silently=True, intended_layout=layout)
        Frame.copy_config(widget, widget_copy)
        self.studio.add(widget_copy, layout)
        layout.copy_layout(widget_copy, widget)
        if isinstance(widget, Container):
            widget_copy._switch_layout(widget.layout_strategy.__class__)
            for child in widget._children:
                self._deep_paste(child, widget_copy)
        return widget_copy

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

    def _attach(self, obj):
        # Create the context menu associated with the object including the widgets own custom menu
        menu = self.make_menu(self.studio.menu_template + obj.create_menu(), obj)
        # Select the widget before drawing the menu
        obj.bind("<Button-3>", lambda _: self.select(obj), add='+')
        obj.bind('<ButtonPress-1>', lambda e: self.highlight.set_function(self.highlight.move, e), add='+')
        obj.bind('<Motion>', self.highlight.resize, '+')
        obj.bind('<ButtonRelease>', self.highlight.clear_resize, '+')
        Frame.add_context_menu(menu, obj)
        self.objects.append(obj)
        if self.root_obj is None:
            self.root_obj = obj
        obj.bind("<Button-1>", lambda _: self.select(obj), add='+')

    def load(self, obj_class, name, container, attributes, layout):
        obj = obj_class(self, name)
        obj.configure(**attributes)
        self._attach(obj)
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
            return
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

    def clear_obj_highlight(self):
        if self.highlight is not None:
            self.highlight.clear()
            self.current_obj = None
            if self.current_container is not None:
                self.current_container.clear_highlight()
                self.current_container = None

    def _on_release(self, bound):
        if self.current_obj is None:
            return
        if self.current_container is not None and self.current_container != self.current_obj:
            self.current_container.clear_highlight()
            if self.current_action == self.MOVE:
                self.current_container.add_widget(self.current_obj, bound, )
            else:
                self.current_obj.layout.widget_released(self.current_obj)
            self.adjust_highlight(self.current_obj)
            self.studio.widget_layout_changed(self.current_obj)
            self.current_action = None
        elif self.current_action == self.RESIZE:
            self.current_obj.layout.widget_released(self.current_obj)
            self.current_action = None
            self.adjust_highlight(self.current_obj)

    def create_restore(self, widget):
        restore_point = widget.layout.get_restore()
        self.studio.new_action(Action(
            lambda: self.restore(widget, restore_point, widget.layout),
            lambda: self.studio.delete(widget)
        ))

    def adjust_highlight(self, widget):
        if self.highlight.is_active or not widget:
            return
        self.highlight.adjust_to(self.highlight.bounds_from_object(widget))

    def _y_scroll(self, *args):
        super()._y_scroll(*args)
        self.adjust_highlight(self.current_obj)

    def _x_scroll(self, *args):
        super()._x_scroll(*args)
        self.adjust_highlight(self.current_obj)

    def on_mousewheel(self, event):
        super().on_mousewheel(event)
        self.adjust_highlight(self.current_obj)

    def _on_move(self, new_bound):
        if self.current_obj is not None:
            self.current_action = self.MOVE
            container: Container = self.layout_at(new_bound)
            if container is not None and self.current_obj != container:
                if container != self.current_container:
                    if self.current_container is not None:
                        self.current_container.clear_highlight()
                    container.show_highlight()
                    self.current_container = container
                container.move_widget(self.current_obj, new_bound)
            else:
                if self.current_container is not None:
                    self.current_container.clear_highlight()
                    self.current_container = self
                self.current_obj.level = 0
                self.current_obj.layout = self
                self.move_widget(self.current_obj, new_bound)
            if self.current_obj.layout.layout_strategy.realtime_support:
                self.studio.widget_layout_changed(self.current_obj)
            self.current_obj.update_idletasks()
            self.update_idletasks()

    def _on_size_changed(self, new_bound):
        if self.current_obj is None:
            return
        self.current_action = self.RESIZE
        if isinstance(self.current_obj.layout, Container) and self.current_obj.layout != self:
            self.current_obj.layout.resize_widget(self.current_obj, new_bound)
        else:
            self.current_obj.level = 0
            self.place_child(self.current_obj, **self.parse_bounds(new_bound))
        if self.current_obj.layout.layout_strategy.realtime_support:
            self.studio.widget_layout_changed(self.current_obj)
        self.current_obj.update_idletasks()
        self.update_idletasks()

    def on_select(self, widget):
        self.select(widget)

    def on_widget_change(self, old_widget, new_widget=None):
        pass

    def on_widget_add(self, widget, parent):
        pass

    def show_highlight(self, *_):
        pass
