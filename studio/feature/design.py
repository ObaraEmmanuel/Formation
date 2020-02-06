"""
Drag drop designer for the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.ui.widgets import Frame
from hoverset.util.execution import Action
from studio.layouts import FrameLayoutStrategy
from studio.lib import legacy
from studio.lib.pseudo import PseudoWidget, Container
from studio.ui import geometry
from studio.ui.highlight import HighLight


class Designer(Frame, Container):
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
        self.layout_strategy = FrameLayoutStrategy(self)
        self.highlight = HighLight(self)
        self.highlight.on_resize(self._on_size_changed)
        self.highlight.on_move(self._on_move)
        self.highlight.on_release(self._on_release)
        self.current_obj = None
        self.current_container = None
        self.current_action = None
        self.bind("<Button-1>", lambda *_: self.select(None))
        self._padding = 30
        # Initialize the first layout some time after the designer has been initialized
        self.after(300, self._set_layout)

    def _set_layout(self):
        self.update_idletasks()
        self.add(legacy.Frame, self._padding, self._padding, width=self.width - self._padding * 2,
                 height=self.height - self._padding * 2)

    @property
    def _ids(self):
        return [i.id for i in self.objects]

    def paste(self, widget):
        # Set a window attribute to widget so that geometry.absolute_bounds can work
        # The widget is not necessarily a hoverset based widget hence might lack this attribute
        widget.window = self.window
        bounds = geometry.absolute_bounds(widget)
        width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
        obj = self.add(widget.__class__, bounds[0] + 8, bounds[1] + 8, width=width, height=height, template=widget,
                       layout=widget.layout)
        Frame.copy_config(widget, obj)

    def add(self, obj_class: PseudoWidget.__class__, x, y, **kwargs):
        width = kwargs.get("width", 55)
        height = kwargs.get("height", 30)
        count = 1
        name = f"{obj_class.display_name}_{count}"
        while name in self._ids:
            name = f"{obj_class.display_name}_{count}"
            count += 1
        obj = obj_class(self, name)
        # Create the context menu associated with the object including the widgets own custom menu
        menu = self.make_menu(self.studio.menu_template + obj.create_menu(), obj)
        # Select the widget before drawing the menu
        obj.bind("<Button-3>", lambda _: self.select(obj), add='+')
        Frame.add_context_menu(menu, obj)
        # Set the layout with respect to the designer. This may change when the object is finally
        # passed to its layout if any
        obj.layout = self
        self.objects.append(obj)
        obj.bind("<Button-1>", lambda _: self.select(obj))

        layout = kwargs.get("layout")
        # If the object has a layout which actually the layout at the point of creation prepare and pass it
        # to the layout
        if isinstance(layout, Container):
            bounds = (x, y, x + width, y + height)
            bounds = geometry.resolve_bounds(bounds, self)
            layout.add_widget(obj, bounds)
            self.studio.add(obj, layout)
            restore_point = layout.get_restore(obj)
            # Create an undo redo point
            self.studio.new_action(Action(
                lambda: self.delete(obj, True),  # Delete silently to prevent adding the event to the undo/redo stack
                lambda: self.restore(obj, restore_point, obj.layout)
            ))
        else:
            # This only happens when adding the main layout. We dont need to add this action to the undo/redo stack
            # This main layout is attached directly to the designer
            obj.place(in_=self, x=x, y=y, width=width, height=height, bordermode="outside")
            self.studio.add(obj, None)

        return obj

    def get_restore(self, widget):
        # Just in case the designer is required to provide a restore point. The designer is almost similar to
        # a frame-layout
        return widget.place_info()

    def select_layout(self, layout: Container):
        pass

    def restore(self, widget, restore_point, container):
        container.restore_widget(widget, restore_point)
        self.studio.on_restore(widget)

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

    def remove_widget(self, widget):
        self.objects.remove(widget)
        widget.place_forget()

    def react(self, event):
        layout = self.event_first(event, self, Container)
        if self.current_container is not None:
            self.current_container.clear_highlight()
            self.current_container = None
        if isinstance(layout, Container):
            self.current_container = layout
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
                self.current_container.add_widget(self.current_obj, bound)
            else:
                self.current_obj.layout.widget_released(self.current_obj)
            self.adjust_highlight(self.current_obj)
            self.studio.widget_layout_changed(self.current_obj)
            self.current_action = None
        elif self.current_action == self.RESIZE:
            self.current_obj.layout.widget_released(self.current_obj)
            self.current_action = None
            self.adjust_highlight(self.current_obj)
            # self.studio.widget_layout_changed(self.current_obj)

    def create_restore(self, widget):
        restore_point = widget.layout.get_restore()
        self.studio.new_action(Action(
            lambda: self.restore(widget, restore_point, widget.layout),
            lambda: self.studio.delete(widget)
        ))

    def adjust_highlight(self, widget):
        self.highlight.adjust_to(self.highlight.bounds_from_object(widget))

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
                    self.current_container = None
                self.current_obj.level = 0
                self.current_obj.layout = self
                self.current_obj.place(in_=self, **self.parse_bounds(new_bound), bordermode="outside")
            self.current_obj.update_idletasks()
            self.update_idletasks()

    def _on_size_changed(self, new_bound):
        if self.current_obj is None:
            return
        self.current_action = self.RESIZE
        if isinstance(self.current_obj.layout, Container):
            self.current_obj.layout.resize_widget(self.current_obj, new_bound)
            # self.adjust_highlight(self.current_obj)
        else:
            self.current_obj.level = 0
            self.current_obj.place(in_=self, **self.parse_bounds(new_bound), bordermode="outside")
        self.current_obj.update_idletasks()
        self.update_idletasks()

    def on_select(self, widget):
        self.select(widget)

    def on_widget_change(self, old_widget, new_widget=None):
        pass

    def on_widget_add(self, widget, parent):
        pass
