from functools import partial
from tkinter import BooleanVar, filedialog

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import ScrolledFrame, Frame, Label, Spinner, Button, ActionNotifier
from hoverset.ui.dialogs import MessageDialog
from hoverset.data.preferences import ListControl
from hoverset.util.execution import import_path
from studio.preferences import Preferences, templates
from studio.feature._base import BaseFeature
from studio.lib import legacy, native
from studio.lib.pseudo import PseudoWidget, Container, WidgetMeta
from studio.ui import geometry
from studio.i18n import _


class Component(Frame):

    def __init__(self, master, component: PseudoWidget.__class__, _=None):
        super().__init__(master)
        self.config(**self.style.surface)
        self._icon = Label(self, **self.style.text_accent, image=get_icon_image(component.icon, 15, 15))
        self._icon.pack(side="left")
        self._text = Label(self, **self.style.text, anchor="w", text=component.display_name)
        self._text.pack(side="left", fill="x")
        self.bind("<Enter>", self.select)
        self.bind("<Leave>", self.deselect)
        self.component = component
        self.allow_drag = True
        self.designer = None

    def select(self, *_):
        self.config_all(**self.style.hover)

    def deselect(self, *_):
        self.config_all(**self.style.surface)

    def render_drag(self, window):
        dim = getattr(self.component, "initial_dimensions", None)
        if dim:
            window.geometry(f"{dim[0]}x{dim[1]}")
        Label(window, **self.style.text_accent, image=get_icon_image(self.component.icon, 15, 15)).pack(side="left")
        Label(window, **self.style.text, anchor="w", text=self.component.display_name).pack(side="left", fill="x")

    def drag_start_pos(self, event):
        self.designer = ComponentPane.get_instance().studio.designer
        self.designer._refresh_container_sort()
        window = self.window.drag_window
        if window:
            window.update_idletasks()
            return (
                event.x_root - int(window.winfo_width() / 2),
                event.y_root - int(window.winfo_height() / 2)
            )
        return super(Component, self).drag_start_pos(event)

    def on_drag(self, event):
        if not self.designer:
            return
        if issubclass(self.component, PseudoWidget) and self.component.non_visual:
            widget = self.designer.widget_at_pos(*self.window.drag_window.get_center())
        else:
            widget = self.designer.layout_at_pos(*self.window.drag_window.get_center())

        if widget and self.window.drag_window:
            bounds = geometry.absolute_bounds(self.window.drag_window)
            widget.react(bounds)

    def on_drag_end(self, event):
        if not self.designer:
            return
        widget = self.designer.layout_at_pos(*self.window.drag_window.get_center())
        if issubclass(self.component, PseudoWidget) and self.component.non_visual:
            if widget:
                widget.clear_highlight()
            widget = self.designer.widget_at_pos(*self.window.drag_window.get_center())
            if widget:
                self.designer.add(self.component, 0, 0, layout=widget)
                widget.clear_highlight()
            self.designer.set_active_container(None)
        elif isinstance(widget, Container):
            bounds = geometry.absolute_bounds(self.window.drag_window)
            widget.add_new(self.component, *bounds[:2])
            widget.clear_highlight()


class SelectableComponent(Component):

    def __init__(self, master, component: PseudoWidget.__class__, controller):
        super(SelectableComponent, self).__init__(master, component)
        self.selected = False
        self.controller = controller
        self.on_click(self.select)
        self.allow_drag = False
        self.bind("<Leave>", self._on_leave)
        self.bind("<Enter>", self._on_enter)

    def _on_leave(self, _):
        if not self.selected:
            self.deselect()

    def _on_enter(self, _):
        super(SelectableComponent, self).select()

    def select(self, *_):
        if self.selected:
            self.deselect()
            return
        super(SelectableComponent, self).select()
        self.selected = True
        self.controller.select(self)

    def deselect(self, silently=False):
        super(SelectableComponent, self).deselect()
        self.selected = False
        self.controller.deselect(self, silently)


class ClickableComponent(Component):

    def __init__(self, master, component: PseudoWidget.__class__, controller):
        super(ClickableComponent, self).__init__(master, component)
        self.controller = controller
        self.allow_drag = False
        ActionNotifier.bind_event(
            "<Button-1>", self, self.add,
            text=f"{component.display_name} added"
        )

    def add(self, *_):
        self.controller.select(self)


class Selector(Label):

    def __init__(self, master, **cnf):
        name = cnf.pop("name", None)
        super().__init__(master, **cnf)
        self.name = name
        self.group = None
        self.config(**self.style.text, anchor="w")

    def select(self):
        self.config(**self.style.hover)

    def deselect(self):
        self.config(**self.style.surface)

    def __eq__(self, other):
        if isinstance(other, Selector):
            return self.name == other.name
        super().__eq__(other)


class ComponentGroup:
    name = None

    def __init__(self, master, name, items, evaluator=None, component_class=None):
        self.name = name
        self.items = items
        self.master = master
        self.selector = None
        self._evaluator = evaluator
        self.component_class = component_class or Component
        self.components = []
        self.update_components(items)

    def supports(self, widget):
        if self._evaluator:
            return self._evaluator(widget)
        return True

    def update_components(self, items):
        self.components = [self.component_class(self.master, i, self) for i in items]


class SelectToDrawGroup(ComponentGroup):

    def __init__(self, master, name, items, evaluator=None, component_class=None):
        component_class = component_class or SelectableComponent
        super(SelectToDrawGroup, self).__init__(master, name, items, evaluator, component_class)
        self._selected = None
        # actual selected component to be drawn
        self.selected = None
        self._on_selection_change = None

    def on_select(self, func, *args, **kwargs):
        self._on_selection_change = lambda component: func(component, *args, **kwargs)

    def select(self, component):
        if self._selected == component:
            return
        if self._selected is not None:
            # deselect silently without triggering selection change
            self._selected.deselect(True)
        self._selected = component
        self.selected = component.component
        if self._on_selection_change:
            self._on_selection_change(self.selected)

    def deselect(self, component, silently=False):
        if self._selected == component:
            self._selected = None
            self.selected = None
            if self._on_selection_change and not silently:
                self._on_selection_change(self.selected)


class ClickToAddGroup(ComponentGroup):

    def __init__(self, master, name, items, evaluator=None, component_class=None):
        component_class = component_class or ClickableComponent
        super(ClickToAddGroup, self).__init__(master, name, items, evaluator, component_class)
        self._on_selection_change = None

    def on_select(self, func, *args, **kwargs):
        self._on_selection_change = lambda component: func(component, *args, **kwargs)

    def select(self, component):
        if self._on_selection_change:
            self._on_selection_change(component.component)


class CustomPathControl(ListControl):

    def __init__(self, master, pref_, path, desc, **extra):
        super(CustomPathControl, self).__init__(master, pref_, path, desc, **extra)
        clear_btn = self.create_action(
            get_icon_image("close", 17, 17), self._clear_all, _("Clear all")
        )
        clear_btn.pack(side="right", fill="y", padx=5)
        clear_btn.configure(**self.style.highlight_active)
        self._list.set_mode(self._list.MULTI_MODE)

    def on_add(self, __=None):
        paths = filedialog.askopenfilenames(
            parent=self.window, title=_("Pick custom widget search paths"),
            filetypes=[("python", ".py .pyw .pyi")],
        )
        cur_paths = [i.value for i in self._list.items]
        # remove duplicates if any
        cur_paths.extend(list(filter(lambda e: e not in cur_paths, paths)))
        self._list.set_values(cur_paths)
        super(CustomPathControl, self).on_add(_)

    def _clear_all(self, _=None):
        self._list.set_values([])
        self._change()

    def has_changes(self):
        return super(CustomPathControl, self).has_changes()


class ComponentPane(BaseFeature):
    CLASSES = {
        "native (ttk)": {"widgets": native.widgets},
        "legacy (tk)": {"widgets": legacy.widgets},
    }
    name = "Components"
    display_name = _("Components")
    _var_init = False
    _defaults = {
        **BaseFeature._defaults,
        "widget_set": "legacy (tk)"
    }
    _custom_pref_path = "studio::custom_widget_paths"

    def __init__(self, master, studio=None, **cnf):
        if not self._var_init:
            self._init_var(studio)
        super().__init__(master, studio, **cnf)

        f = Frame(self, **self.style.surface)
        f.pack(side="top", fill="both", expand=True, pady=4)
        f.pack_propagate(0)

        self._widget_set = Spinner(self._header, width=150)
        self._widget_set.config(**self.style.no_highlight)
        self._widget_set.set_values(list(self.CLASSES.keys()))
        self._widget_set.pack(side="left")
        self._widget_set.on_change(self.collect_groups)
        self._select_pane = ScrolledFrame(f, width=150)
        self._select_pane.place(x=0, y=0, relwidth=0.4, relheight=1)

        self._search_btn = Button(self._header, image=get_icon_image("search", 15, 15), width=25, height=25,
                                  **self.style.button)
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)
        self._search_selector = Label(self._select_pane.body, **self.style.text, text="search", anchor="w")
        self._search_selector.configure(**self.style.hover)

        self._widget_pane = ScrolledFrame(f, width=150)
        self._select_pane.body.config(**self.style.surface)
        self._widget_pane.place(relx=0.4, y=0, relwidth=0.6, relheight=1)

        self._pool = {}
        self._selectors = []
        self._selected = None
        self._component_cache = None
        self._is_searching = False
        self._matching_components = []
        self._last_query = ""
        self._extern_groups = []
        widget_set = self.get_pref("widget_set")
        if widget_set not in self.CLASSES:
            widget_set = "legacy (tk)"
            self._widget_set.set(widget_set)
        self.collect_groups(widget_set)
        # add custom widgets config to settings
        templates.update(self._pref_template())
        self._custom_group = None
        self._custom_widgets = []
        self._external_widgets = []
        self.studio.bind("<<SelectionChanged>>", self.on_widget_select, add='+')
        Preferences.acquire().add_listener(self._custom_pref_path, self._init_custom)
        self._reload_custom()

    def _pref_template(self):
        return {
            _("Widgets"): {
                "_scroll": False,
                _("Custom Widgets"): {
                    "layout": {
                        "fill": "both",
                        "expand": True,
                    },
                    "children": (
                        {
                            "desc": _("Custom widgets search paths"),
                            "path": "studio::custom_widget_paths",
                            "element": CustomPathControl,
                            "layout": {
                                "fill": "both",
                                "expand": True,
                                "padx": 5,
                                "pady": 5
                            }
                        },
                    )
                }
            },
        }

    @property
    def custom_widgets(self):
        return self._custom_widgets

    @property
    def registered_widgets(self):
        return self._external_widgets + self.custom_widgets

    def auto_find_load_custom(self, *modules):
        # locate and load all custom widgets in modules
        # module can be a module or a path to module file
        self._custom_widgets = []
        errors = {}
        for module in modules:
            if isinstance(module, str):
                try:
                    module = import_path(module)
                except Exception as e:
                    errors[module] = e
                    continue
            for attr in dir(module):
                if type(getattr(module, attr)) == WidgetMeta:
                    self._custom_widgets.append(getattr(module, attr))
        if errors:
            error_msg = "\n\n".join(
                [f"{path}\n{error}" for path, error in errors.items()]
            )
            MessageDialog.show_error(
                parent=self.window,
                message=_("Error loading widgets \n\n{}").format(error_msg)
            )

        return self._custom_widgets

    def _init_custom(self, paths):
        # reload custom widget modules
        try:
            widgets = self.auto_find_load_custom(*paths)
        except Exception as e:

            return

        if not widgets:
            if self._custom_group is not None:
                self.unregister_group(self._custom_group)
                self._custom_group = None
            return

        if self._custom_group is None:
            self._custom_group = self.register_group(
                "Custom",
                widgets,
                ComponentGroup,
            )
        else:
            self._custom_group.update_components(widgets)
            # this will force group to be re-rendered
            self.select(self._custom_group.selector)

    def _reload_custom(self):
        self._init_custom(Preferences.acquire().get(self._custom_pref_path))

    def _init_var(self, master=None):
        self._var_init = True
        for widget_set in self.CLASSES:
            self.CLASSES[widget_set]["var"] = BooleanVar(master, False)

    def _widget_sets_as_menu(self):
        return [
            ("checkbutton",  # Type checkbutton
             i.capitalize(),  # Label as title case
             None,  # Image
             partial(self.collect_groups, i),  # The callback
             {"variable": self.CLASSES[i]["var"]}  # Additional config including the variable associated
             ) for i in self.CLASSES
        ]

    @property
    def selectors(self):
        return self._selectors

    def create_menu(self):
        return (
            (
                "command", _("Reload custom widgets"),
                get_icon_image("reload", 18, 18), self._reload_custom, {}
            ),
            (
                "command", _("Search"),
                get_icon_image("search", 18, 18), self.start_search, {}
            ),
            ("cascade", _("Widget set"), get_icon_image("blank", 18, 18), None, {"menu": (
                *self._widget_sets_as_menu(),
            )}),
        )

    def collect_groups(self, widget_set):
        for other_set in [i for i in self.CLASSES if i != widget_set]:
            self.CLASSES[other_set]["var"].set(False)
        self.CLASSES[widget_set]["var"].set(True)
        self._widget_set.set(widget_set)
        self._select_pane.clear_children()
        self._pool = {}
        components = self.CLASSES.get(widget_set)["widgets"]
        for component in components:
            group = component.group
            if group in self._pool:
                self._pool[group].append(Component(self._widget_pane.body, component))
            else:
                self._pool[group] = [Component(self._widget_pane.body, component)]
        self.render_groups()
        # component pool has changed so invalidate the cache
        self._component_cache = None
        self.set_pref("widget_set", widget_set)

    def get_components(self) -> set:
        if self._component_cache:
            return self._component_cache
        components = []
        for selector in self._selectors:
            if isinstance(selector.group, ComponentGroup):
                components.extend(selector.group.components)
            else:
                components.extend(self._pool[selector.name])
        self._component_cache = set(components)
        return self._component_cache

    def select(self, selector):
        if self._selected is not None:
            self._selected.deselect()
        selector.select()
        self._selected = selector
        self._widget_pane.clear_children()

        if isinstance(selector.group, ComponentGroup):
            components = selector.group.components
        else:
            components = self._pool[selector.name]

        for component in components:
            component.pack(side="top", pady=2, fill="x")

    def _auto_select(self):
        # automatically pick a selector when no groups have
        # been explicitly selected and the pane is in limbo
        if self._selectors:
            self.select(self._selectors[0])
        else:
            self._widget_pane.clear_children()
            self._selected = None

    def render_groups(self):
        self._selectors = []
        for group in self._pool:
            self.add_selector(Selector(self._select_pane.body, text=group.value, name=group))
        self._auto_select()
        self.render_extern_groups()

    def render_extern_groups(self):
        for group in self._extern_groups:
            if self.studio.selection and all(group.supports(w) for w in self.studio.selection):
                self.add_selector(group.selector)
            elif not self.studio.selection and group.supports(None):
                self.add_selector(group.selector)
            else:
                self.remove_selector(group.selector)
                if self._selected == group.selector:
                    self._auto_select()

    def add_selector(self, selector):
        if selector in self._selectors:
            return
        self._selectors.append(selector)
        selector.bind("<Button-1>", lambda *_: self.select(selector))
        selector.pack(side="top", pady=2, fill="x")

    def remove_selector(self, selector):
        if selector in self._selectors:
            self._selectors.remove(selector)
        selector.pack_forget()

    def hide_selectors(self):
        for selector in self._selectors:
            selector.pack_forget()

    def show_selectors(self):
        for selector in self._selectors:
            selector.pack(side="top", pady=2, fill="x")

    def register_group(self, name, items, group_class, evaluator=None, component_class=None, register=False):
        group = group_class(self._widget_pane.body, name, items, evaluator, component_class)
        self._extern_groups.append(group)
        # link up selector and group
        group.selector = Selector(self._select_pane.body, text=group.name, name=group.name)
        group.selector.group = group
        self.render_extern_groups()

        if register:
            self._external_widgets.extend(items)
        return group

    def unregister_group(self, group):
        if group in self._extern_groups:
            self.remove_selector(group.selector)
            self._extern_groups.remove(group)
            self._auto_select()

    def on_widget_select(self, _):
        self.render_extern_groups()
        # invalidate cache so it has to be regenerated
        self._component_cache = None
        if self._is_searching:
            self.hide_selectors()
            # Reapply search query to possibly new components
            self.on_search_query(self._last_query)
            return

    def start_search(self, *_):
        super().start_search()
        self._is_searching = True
        self._widget_pane.scroll_to_start()
        if self._selected is not None:
            self._selected.deselect()
        self.hide_selectors()
        self._search_selector.pack(side="top", pady=2, fill="x")
        self._widget_pane.clear_children()
        # Display all components by running an empty query
        self.on_search_query("")

    def on_search_clear(self):
        super().on_search_clear()
        if self._selectors:
            self.select(self._selectors[0])
        self._search_selector.pack_forget()
        self._is_searching = False
        self.show_selectors()

    def on_search_query(self, query):
        self._last_query = query
        components: set = self.get_components()
        # remove any components that are no longer available due to group changes
        for component in set(self._matching_components) - components:
            component.pack_forget()

        self._matching_components.clear()
        for component in self.get_components():
            if query.lower() in component.component.display_name.lower():
                self._matching_components.append(component)
                component.pack(side="top", pady=2, fill="x")
            else:
                component.pack_forget()
