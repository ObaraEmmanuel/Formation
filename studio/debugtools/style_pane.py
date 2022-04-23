from hoverset.ui.widgets import Label

from studio.ui.widgets import Pane
from studio.feature.stylepane import StylePaneFramework, StyleGroup
from studio.debugtools.common import get_resolved_properties, get_base_class
from studio.debugtools import layouts


class AttributeGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = "Attributes"

    def get_definition(self):
        if not hasattr(self.widget, '_dbg_properties'):
            setattr(self.widget, '_dbg_properties', get_resolved_properties(self.widget))

        properties = self.widget._dbg_properties
        for key in properties:
            properties[key]["value"] = self.widget[key]
        return properties

    def _get_prop(self, prop, widget):
        return widget[prop]

    def _set_prop(self, prop, value, widget):
        widget.configure(**{prop: value})

    def on_widget_change(self, widget):
        super().on_widget_change(widget)
        base = get_base_class(widget)
        if base:
            self.label = f"Attributes ({base.__name__})"
        else:
            self.label = "Attributes"


class LayoutGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        super().__init__(master, pane, **cnf)
        self.label = "Layout"

    def get_definition(self):
        layout = layouts.get_layout(self.widget)
        if layout:
            return layout.get_def(self.widget)
        return {}

    def _get_prop(self, prop, widget):
        layout = layouts.get_layout(self.widget)
        if layout:
            return layout.configure(self.widget)[prop]

    def _set_prop(self, prop, value, widget):
        layout = layouts.get_layout(self.widget)
        if layout:
            layout.configure(**{prop: value})

    def on_widget_change(self, widget):
        super().on_widget_change(widget)
        if not widget:
            return
        layout = layouts.get_layout(self.widget)
        if layout:
            self.label = f"Layout ({layout.name})"
        elif not self.widget.winfo_ismapped():
            self._show_empty("Widget is unmapped")
            self.label = "Layout"
        else:
            self._show_empty("Unknown layout manager")
            self.label = "Layout"


class StylePane(StylePaneFramework, Pane):
    name = "Widget config"

    def __init__(self, master, debugger):
        super(StylePane, self).__init__(master)
        Label(self._header, **self.style.text_accent, text=self.name).pack(side="left")
        self.debugger = debugger
        self.setup_style_pane()
        self.add_group(LayoutGroup)
        self.add_group(AttributeGroup)
        self.debugger.bind("<<WidgetSelectionChanged>>", self.on_selection_changed)

    def on_selection_changed(self, _):
        if self.debugger.selected:
            self.on_select(self.debugger.selected[0].widget)
        else:
            self.on_select(None)

    def get_header(self):
        return self._header

    def last_action(self):
        pass

    def new_action(self, action):
        pass

    def widget_modified(self, widget):
        pass
