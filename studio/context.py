from hoverset.util.execution import Action
from hoverset.ui.widgets import Frame
from hoverset.ui.icons import get_icon_image


class BaseContext(Frame):

    def __init__(self, master, studio, *args, **kwargs):
        super(BaseContext, self).__init__(master)
        self.tab_view = master
        self.studio = studio
        self.pref = studio.pref
        self._undo_stack = []
        self._redo_stack = []
        self.tab_handle = None
        self.name = "tab"
        self.icon = get_icon_image("data", 15, 15)
        self.bind("<<TabDeleted>>", self._close_context)
        self.bind("<<TabToClose>>", self._close_check)

    def _close_context(self, _):
        self.studio.on_context_close(self)
        self.destroy()

    def _close_check(self, _):
        if not self.on_context_close():
            self.tab_view.block_close(True)

    def on_context_set(self):
        pass

    def on_context_unset(self):
        pass

    def on_context_mount(self):
        self.tab_handle.config_tab(text=self.name)

    def new_action(self, action: Action):
        """
        Register a undo redo point
        :param action: An action object implementing undo and redo methods
        :return:
        """
        self._redo_stack.clear()
        if len(self._undo_stack) >= self.pref.get("studio::undo_depth") and self.studio.get("studio::use_undo_depth"):
            self._undo_stack.pop(0)
        self._undo_stack.append(action)

    def undo(self):
        # Let's avoid popping an empty list to prevent raising IndexError
        if self._undo_stack:
            action = self._undo_stack.pop()
            action.undo()
            self._redo_stack.append(action)

    def redo(self):
        if self._redo_stack:
            action = self._redo_stack.pop()
            action.redo()
            self._undo_stack.append(action)

    def has_redo(self) -> bool:
        return bool(self._redo_stack)

    def has_undo(self) -> bool:
        return bool(self._undo_stack)

    def last_action(self):
        if self._undo_stack:
            return self._undo_stack[-1]
        return None

    def pop_last_action(self, key=None):
        last = self.last_action()
        if last is not None:
            # verify action key first
            if key is not None and last.key != key:
                return
            self._undo_stack.remove(last)

    def select(self):
        if self.tab_handle:
            self.tab_view.select(self.tab_handle)

    def serialize(self):
        return {"class": self.__class__, "args": (), "kwargs": {}, "data": {}}

    def deserialize(self, data):
        pass

    def can_persist(self):
        return False

    def on_app_close(self):
        return True

    def on_context_close(self):
        return True
