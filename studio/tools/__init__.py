from functools import partial

from hoverset.ui.menu import ShowIf, EnableIf
from hoverset.ui.icons import get_icon_image
from studio.tools.menus import MenuTool
from studio.tools.canvas import CanvasTool
from studio.tools._base import BaseTool


TOOLS = (
    MenuTool,
    CanvasTool,
)


class ToolManager:
    """
    This class manages all tools dynamically exposing tool functions through toplevel and
    context menus. Add in built tools here
    """
    _instance = None

    def __init__(self, studio):
        self._tools = []
        self.studio = studio
        ToolManager._instance = self

    def initialize(self):
        self._tools = [tool(self.studio, self) for tool in TOOLS]

    def get_tool_menu(self, hide_unsupported=True):
        """
        Get all tools functionality as a dynamic menu template that
        adjusts to expose only tool functionality available based current
        studio state such as selected widget.
        :param hide_unsupported: Set to false to to disable and not hide unavailable
        tool functionality
        :return: tuple of menu templates
        """
        templates = ()
        manipulator = ShowIf if hide_unsupported else EnableIf
        for tool in self._tools:
            template = tool.get_menu(self.studio)
            # If tool does not provide a menu ignore it
            if len(template) < 1:
                continue
            # if tool has more than one template entry use a cascade menu
            # otherwise use if only a single item is available, use as is
            if len(template) > 1:
                icon = get_icon_image(tool.icon, 14, 14) if isinstance(tool.icon, str) else tool.icon
                template = ('cascade', tool.name, icon, None, {'menu': template})
            else:
                template = template[0]
            templates += (
                manipulator(partial(tool.supports, self.studio.selection), template),
            )
        # prepend a separator for context menus
        if templates and hide_unsupported:
            templates = (('separator',),) + templates
        return tuple(templates)

    def get_tools_as_menu(self):
        """
        Return menu template for tools. Based on currently selected widget and other
        parameters, tools that cannot be invoked are disabled
        :return: tuple of menu templates
        """
        return self.get_tool_menu(False)

    def install(self, tool):
        if not issubclass(tool, BaseTool):
            raise ValueError(f'Tool {tool} does not extend class BaseTool')
        self._tools = tool(self.studio, self)
        # recompute templates
        self._templates = self.get_tool_menu()

    def acquire_tool(self, tool):
        if not issubclass(tool, BaseTool):
            raise ValueError(f'Tool {tool} does not extend class BaseTool')
        for t in self._tools:
            if isinstance(t, tool):
                return tool

    def dispatch(self, action, *args):
        # dispatch action to all tools connected
        for tool in self._tools:
            getattr(tool, action)(*args)

    def on_widgets_delete(self, widgets):
        self.dispatch("on_widgets_delete", widgets)

    def on_app_close(self):
        for tool in self._tools:
            # block app close if any tool returns false
            if not tool.on_app_close():
                return False
        return True

    def on_session_clear(self):
        self.dispatch("on_session_clear")

    def on_widget_add(self, widget, parent):
        self.dispatch("on_widget_add", widget, parent)

    def on_widgets_change(self, widgets):
        self.dispatch("on_widgets_change", widgets)

    def on_widgets_layout_change(self, widgets):
        self.dispatch("on_widgets_layout_change", widgets)

    def on_widgets_reorder(self, indices):
        self.dispatch("on_widgets_reorder", indices)

    def on_context_switch(self):
        self.dispatch("on_context_switch")

    def on_context_close(self, context):
        self.dispatch("on_context_close", context)

    @classmethod
    def acquire(cls):
        return cls._instance
