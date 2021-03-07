from hoverset.ui.menu import ShowIf, EnableIf
from hoverset.ui.icons import get_icon_image
from studio.tools.menus import MenuTool
from studio.tools._base import BaseTool


class ToolManager:
    """
    This class manages all tools dynamically exposing tool functions through toplevel and
    context menus. Add in built tools here
    """
    _tools = {
        MenuTool,
    }

    @classmethod
    def get_tool_menu(cls, studio=None, hide_unsupported=True):
        """
        Get all tools functionality as a dynamic menu template that
        adjusts to expose only tool functionality available based current
        studio state such as selected widget.
        :param studio:
        :param hide_unsupported: Set to false to to disable and not hide unavailable
        tool functionality
        :return: tuple of menu templates
        """
        templates = ()
        manipulator = ShowIf if hide_unsupported else EnableIf
        for tool in cls._tools:
            template = tool.get_menu(studio)
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
                manipulator(lambda: tool.supports(studio.selected), template),
            )
        # prepend a separator for context menus
        if len(templates) and hide_unsupported:
            templates = (('separator',),) + templates
        return tuple(templates)

    @classmethod
    def get_tools_as_menu(cls, studio=None):
        """
        Return menu template for tools. Based on currently selected widget and other
        parameters, tools that cannot be invoked are disabled
        :param studio: A StudioApplication object
        :return: tuple of menu templates
        """
        return cls.get_tool_menu(studio, False)

    @classmethod
    def install(cls, tool):
        if not isinstance(tool, BaseTool):
            raise ValueError('Tool does not extend class BaseTool')
        cls._tools.add(tool)
