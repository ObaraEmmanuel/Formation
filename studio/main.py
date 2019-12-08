# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

import sys

# Add Studio and Hoverset to path so imports from hoverset can work.
sys.path.append("..\\..\\Hoverset")

from studio.design import Designer
from studio.component_tree import ComponentTree
from studio.ui.stylepane import StylePane
from studio.components import ComponentPane
from hoverset.ui.widgets import Application, Label, Spinner, SpinBox, Frame, PanedWindow


class FrozenLabel(Label):
    style = None

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.config(**self.style.dark_text)
        self.config(text="label1")


class FrozenSpinner(Spinner):
    style = None

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.set("spinner1")
        self.disabled(True)


class FrozenSpinBox(SpinBox):
    style = None

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.set("spinbox1")
        self.disabled(True)


class StudioApplication(Application):
    widget_tree = None
    designer: Designer = None
    style_pane: StylePane = None
    widget_set: ComponentPane = None

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self.load_styles("../hoverset/ui/themes/default.css")
        self.geometry("1100x650")
        self.state('zoomed')
        self.title('Tkinter Studio')
        self._toolbar = Frame(self, **self.style.dark, height=30)
        self._toolbar.pack(side="top", fill="x")
        self._toolbar.pack_propagate(0)
        self._pane = PanedWindow(self, **self.style.dark_pane_horizontal)
        self._pane.pack(fill="both", expand=True)
        self._left = PanedWindow(self._pane, **self.style.dark_pane_vertical)
        self._center = PanedWindow(self._pane, **self.style.dark_pane_vertical)
        self._right = PanedWindow(self._pane, **self.style.dark_pane_vertical)

        self._pane.add(self._left, minsize=300, sticky='nswe', width=300)
        self._pane.add(self._center, minsize=400, width=16000, sticky='nswe')
        self._pane.add(self._right, minsize=300, sticky='nswe', width=300)

        StudioApplication.widget_set = self.install(ComponentPane, self._left)
        StudioApplication.widget_tree = self.install(ComponentTree, self._left)
        StudioApplication.designer = self.install(Designer, self._center)
        StudioApplication.style_pane = self.install(StylePane, self._right)

        # self.design.add(GenericLinearLayout, 400, 350)

    def install(self, component, pane):
        obj = component(pane, self)
        pane.add(obj, minsize=100, height=300, sticky='nswe')
        return obj

    def select(self, widget):
        StudioApplication.style_pane.styles_for(widget)
        StudioApplication.widget_tree.select(widget)

    def add(self, widget, parent=None):
        StudioApplication.widget_tree.add(widget, parent)

    def widget_modified(self, widget1, widget2=None):
        StudioApplication.widget_tree.widget_modified(widget1, widget2)


if __name__ == "__main__":
    # apps.unicode_viewer.App().mainloop()
    StudioApplication().mainloop()
