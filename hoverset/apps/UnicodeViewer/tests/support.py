from ..app import App
from itertools import chain


class MockEvent:

    def __init__(self):
        self.x_root = 10
        self.y_root = 10


class MockApp(App):
    """
    Subclass of App that is optimized for testing purposes.
    It prevents Thread functionality which tends to break tkinter tests
    by overriding methods that spawn threads and coercing them to run within
    the main thread.
    """

    def __init__(self):
        super().__init__()
        # Remove components
        list(map(lambda component: component.uninstall(), self.components))
        # Hide window
        # self.withdraw()

    def render(self, from_: int) -> None:
        # We need to prevent thread functionality during tests
        self._render(from_, None)

    @property
    def flattened_grids(self):
        # Return grids in a flattened form for easy direct looping during tests
        return list(chain.from_iterable(self.grids))

    def request_context_menu(self, event=None):
        # Calling the raw method during tests results in errors
        pass
