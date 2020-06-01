import unittest
from formation import AppBuilder
from formation.tests.support import tk_supported, ttk_supported, tk


class LegacyWidgetCreationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder("samples/all_legacy.xml")

    def test_creation(self):
        for widget_class in tk_supported:
            with self.subTest(widget_class=widget_class):
                widget = getattr(self.builder, widget_class.__name__ + "_1", None)
                self.assertIsNotNone(widget, "missing test case for " + str(widget_class))
                self.assertIsInstance(widget, widget_class, "creation failed: " + widget_class.__name__)


class WidgetCreationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder("samples/all_native.xml")

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
