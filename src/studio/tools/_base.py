from hoverset.ui.widgets import Window


class BaseTool:
    """
    Base tool for Tools. Subclass this class to implement a studio tool
    """
    name = ''
    icon = 'blank'

    @classmethod
    def get_menu(cls, studio):
        """
        Override this method to return menu template for your tool
        Set up templates as follows
        (type, label, icon, command/callback, additional_configuration={})
        icon should be a tk image preferably 14px x 14px
        :param studio:
        :return:
        """
        # default behaviour is to return an empty template
        return ()

    @classmethod
    def supports(cls, widget):
        """
        Checks whether the tool can work on a given widget. This information is
        useful for the studio to allow it render dropdown menus correctly
        :param widget: A tk Widget to be checked
        :return: True if tool can work on the widget otherwise false
        """


class BaseToolWindow(Window):
    _tool_map = {}

    def __init__(self, master, widget):
        super().__init__(master)
        self.widget = widget
        self.transient(master)
        self.config(**self.style.surface)

    @classmethod
    def close_all(cls):
        tools = tuple(cls._tool_map.values())
        for tool in tools:
            tool.destroy()

    def destroy(self):
        """
        Release an existing MenuEditor allowing a new one to
        be spawned next time.
        :return: None
        """
        if self.widget in self._tool_map:
            self._tool_map.pop(self.widget)
        super().destroy()

    @classmethod
    def acquire(cls, master, widget, *args, **kwargs):
        """
        To avoid opening multiple tools for the same widget use this
        constructor. It will either create an editor for the widget if none exists or bring
        an existing editor to focus.
        :param master: tk toplevel window
        :param widget: menu supporting widget
        :return: a MenuEditor instance
        """
        if widget in cls._tool_map:
            tool = cls._tool_map[widget]
            tool.lift()
            tool.focus_set()
        else:
            # noinspection PyArgumentList
            tool = cls(master, widget, *args, **kwargs)
            cls._tool_map[widget] = tool
        return tool
