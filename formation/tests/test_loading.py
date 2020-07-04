import unittest
from lxml import etree

from formation import AppBuilder
from formation.tests.support import tk_supported, ttk_supported, tk, ttk, get_resource


class XMLLoadingTextCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.xml_string = """
        <tkinter.Frame 
            xmlns:attr="http://www.hoversetformationstudio.com/styles/"
            xmlns:layout="http://www.hoversetformationstudio.com/layouts/" 
            name="Frame_1" 
            attr:layout="FrameLayout"
            layout:width="616" 
            layout:height="571" 
            layout:x="31" 
            layout:y="31">
            <tkinter.Frame 
                name="Frame_2" 
                attr:background="#e3e3e3" 
                attr:layout="FrameLayout" 
                layout:width="262"
                layout:height="145" 
                layout:x="125" 
                layout:y="23"/>
        </tkinter.Frame>"""

    def test_load_path_implicit(self):
        builder = AppBuilder(path=get_resource("all_legacy.xml"))
        self.assertIsInstance(builder.Frame_2, tk.Frame)
        self.assertEqual(builder.Frame_2["background"], "#e3e3e3")

    def test_load_path_explicit(self):
        builder = AppBuilder()
        builder.load_path(path=get_resource("all_legacy.xml"))
        self.assertIsInstance(builder.Frame_2, tk.Frame)
        self.assertEqual(builder.Frame_2["background"], "#e3e3e3")

    def test_load_string_implicit(self):
        builder = AppBuilder(string=self.xml_string)
        self.assertIsInstance(builder.Frame_1, tk.Frame)
        self.assertEqual(builder.Frame_2["background"], "#e3e3e3")

    def test_load_string_explicit(self):
        builder = AppBuilder()
        builder.load_string(self.xml_string)
        self.assertIsInstance(builder.Frame_1, tk.Frame)
        self.assertEqual(builder.Frame_2["background"], "#e3e3e3")

    def test_load_node_implicit(self):
        with open(get_resource("all_legacy.xml"), 'rb') as stream:
            node = etree.parse(stream).getroot()
        builder = AppBuilder(node=node)
        self.assertIsInstance(builder.Frame_1, tk.Frame)
        self.assertEqual(builder.Frame_2["background"], "#e3e3e3")

    def test_load_node_explicit(self):
        with open(get_resource("all_legacy.xml"), 'rb') as stream:
            node = etree.parse(stream).getroot()
        builder = AppBuilder()
        builder.load_node(node)
        self.assertIsInstance(builder.Frame_1, tk.Frame)
        self.assertEqual(builder.Frame_2["background"], "#e3e3e3")


class CompatibilityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder(path=get_resource("compat.xml"))

    def test_tk_compatibility(self):
        # Both tests should pass in python 2 and 3
        self.assertIsInstance(self.builder.button_tk_2, tk.Button)
        self.assertIsInstance(self.builder.button_tk_3, tk.Button)

    def test_ttk_compatibility(self):
        # Both tests should pass in python 2 and 3
        self.assertIsInstance(self.builder.button_ttk_2, ttk.Button)
        self.assertIsInstance(self.builder.button_ttk_3, ttk.Button)


class LegacyWidgetCreationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder(path=get_resource("all_legacy.xml"))

    def test_creation(self):
        for widget_class in tk_supported:
            with self.subTest(widget_class=widget_class):
                widget = getattr(self.builder, widget_class.__name__ + "_1", None)
                self.assertIsNotNone(widget, "missing test case for " + str(widget_class))
                self.assertIsInstance(widget, widget_class, "creation failed: " + widget_class.__name__)


class WidgetCreationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = AppBuilder(path=get_resource("all_native.xml"))

    def test_panedwindow_creation(self):
        self.assertEqual(str(self.builder.Panedwindow_1["orient"]), tk.HORIZONTAL)
        self.assertEqual(str(self.builder.Panedwindow_2["orient"]), tk.VERTICAL)

    def test_creation(self):
        for widget_class in ttk_supported:
            with self.subTest(widget_class=widget_class):
                widget = getattr(self.builder, widget_class.__name__ + "_1", None)
                self.assertIsNotNone(widget, "missing test case for " + str(widget_class))
                self.assertIsInstance(widget, widget_class, "creation failed: " + widget_class.__name__)


if __name__ == '__main__':
    unittest.main()
