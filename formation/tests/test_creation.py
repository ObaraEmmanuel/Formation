import unittest

from formation import AppBuilder
from formation.tests.support import tk_supported, ttk_supported, tk, ttk, get_resource


class CompatibilityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder(get_resource("compat.xml"))

    def test_tk_compatibility(self):
        # Both tests should pass in python 2 and 3
        self.assertIsInstance(self.builder.button_tk_2, tk.Button, "Could not load python 2 tkinter variant")
        self.assertIsInstance(self.builder.button_tk_3, tk.Button, "Could not load python 3 tkinter variant")

    def test_ttk_compatibility(self):
        # Both tests should pass in python 2 and 3
        self.assertIsInstance(self.builder.button_ttk_2, ttk.Button, "Could not load python 2 ttk variant")
        self.assertIsInstance(self.builder.button_ttk_3, ttk.Button, "Could not load python 3 ttk variant")


class LegacyWidgetCreationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder(get_resource("all_legacy.xml"))

    def test_creation(self):
        for widget_class in tk_supported:
            with self.subTest(widget_class=widget_class):
                widget = getattr(self.builder, widget_class.__name__ + "_1", None)
                self.assertIsNotNone(widget, "missing test case for " + str(widget_class))
                self.assertIsInstance(widget, widget_class, "creation failed: " + widget_class.__name__)


class WidgetCreationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder(get_resource("all_native.xml"))

    def test_panedwindow_creation(self):
        self.assertEqual(str(self.builder.Panedwindow_1["orient"]), tk.HORIZONTAL, "Orientation not set correctly")
        self.assertEqual(str(self.builder.Panedwindow_2["orient"]), tk.VERTICAL, "Orientation not set correctly")

    def test_creation(self):
        for widget_class in ttk_supported:
            with self.subTest(widget_class=widget_class):
                widget = getattr(self.builder, widget_class.__name__ + "_1", None)
                self.assertIsNotNone(widget, "missing test case for " + str(widget_class))
                self.assertIsInstance(widget, widget_class, "creation failed: " + widget_class.__name__)


if __name__ == '__main__':
    unittest.main()
