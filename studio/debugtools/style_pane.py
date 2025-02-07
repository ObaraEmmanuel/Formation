from hoverset.ui.widgets import Label
from studio.debugtools.defs import RemoteWidget

from studio.ui.widgets import Pane
from studio.feature.stylepane import StylePaneFramework, StyleGroup
from studio.debugtools.common import get_resolved_properties
from studio.debugtools import layouts
from studio.lib.properties import combine_properties
from studio.i18n import _


def get_combined_properties(widgets):
    """
    Return a dict of properties that are common to all widgets in the list.
    """
    if not widgets:
        return {}

    # get all the properties for each widget
    properties = [widget._dbg_properties for widget in widgets]

    return combine_properties(properties)


class AttributeGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Attributes")
        self.bases = []

    def get_definition(self):
        for widget in self.widgets:
            if not hasattr(widget, '_dbg_properties'):
                setattr(widget, '_dbg_properties', get_resolved_properties(widget))
            else:
                widget._dbg_properties = get_resolved_properties(widget)

        return get_combined_properties(self.widgets)

    def _get_prop(self, prop, widget):
        return widget[prop]

    def _set_prop(self, prop, value, widget):
        widget.configure(**{prop: value})

    def can_optimize(self):
        return self.bases == list(set([widget.equiv_class for widget in self.widgets]))

    def on_widgets_change(self):
        super().on_widgets_change()
        self.bases = bases = list(set([widget.equiv_class for widget in self.widgets]))
        if len(bases) == 1:
            self.label = _("Attributes") + f" ({bases[0].__name__})"
        elif len(bases) > 1:
            self.label = _("Attributes") + " (*)"
        else:
            self.label = _("Attributes")


class LayoutGroup(StyleGroup):

    handles_layout = True

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = _("Layout")
        self._layouts = []

    def _layout_def(self, widget):
        layout = layouts.get_layout(widget)
        if layout:
            return layout.get_def(widget)
        return {}

    def get_definition(self):
        return combine_properties([self._layout_def(widget) for widget in self.widgets])

    def _get_prop(self, prop, widget):
        layout = layouts.get_layout(widget)
        if layout:
            prop = layout.configure(widget)[prop]
            return prop

    def _set_prop(self, prop, value, widget):
        layout = layouts.get_layout(widget)
        if layout:
            layout.configure(widget, **{prop: value})

    def can_optimize(self):
        return self._layouts == list(set(filter(lambda x: x, [layouts.get_layout(widget) for widget in self.widgets])))

    def supports_widgets(self):
        return all(isinstance(widget, RemoteWidget) for widget in self.widgets)

    def on_widgets_change(self):
        super().on_widgets_change()

        self._layouts = list(set(filter(lambda x: x, [layouts.get_layout(widget) for widget in self.widgets])))

        if len(self._layouts) == 1:
            self.label = _("Layout") + f" ({self._layouts[0].name})"
        elif len(self._layouts) > 1:
            self.label = _("Layout") + " (*)"
        elif all(not widget.winfo_ismapped() for widget in self.widgets):
            self._show_empty(_("Widget(s) not mapped"))
            self.label = _("Layout")
        else:
            self._show_empty(_("Unknown layout manager"))
            self.label = _("Layout")


class StylePane(StylePaneFramework, Pane):
    name = _("Widget config")
    display_name = _("Widget config")

    def __init__(self, master, debugger):
        super(StylePane, self).__init__(master)
        Label(self._header, **self.style.text_accent, text=self.display_name).pack(side="left")
        self.debugger = debugger
        self.setup_style_pane()
        self.add_group(LayoutGroup)
        self.add_group(AttributeGroup)
        self.debugger.bind("<<SelectionChanged>>", self.on_selection_changed, True)
        self.debugger.bind("<<WidgetModified>>", self._on_config_change)
        self.debugger.bind("<<MenuItemModified>>", self._on_menu_item_config, True)
        self.debugger.bind("<<WidgetLayoutChanged>>", self._on_layout_change)
        self.debugger.bind("<<WidgetMapped>>", self._on_layout_change, True)
        self.debugger.bind("<<WidgetUnmapped>>", self._on_layout_change, True)

    def _on_config_change(self, _):
        if self.debugger.active_widget in self.widgets:
            self.render_styles()

    def _on_menu_item_config(self, event):
        widget, root, index = event.user_data.split(" ")
        widget = self.debugger.widget_from_id(widget, int(root))
        if not widget._menu_items:
            return
        item = widget._menu_items[int(index)]
        if item in self.widgets:
            self.render_styles()

    def _on_layout_change(self, _):
        if self.debugger.active_widget in self.widgets:
            self.render_layouts()

    def on_selection_changed(self, _):
        if self.debugger.selection:
            self._select(None, self.debugger.selection)
        else:
            self._select(None, [])

    def get_header(self):
        return self._header

    def last_action(self):
        pass

    def new_action(self, action):
        pass

    def widgets_modified(self, widgets):
        pass
