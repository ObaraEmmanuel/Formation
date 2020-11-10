import unittest

from formation import AppBuilder
from formation.tests.support import get_resource, tk


class PlaceLayoutTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("common_layout.xml"))

    def test_loading(self):
        children = self.builder.place_frame.winfo_children()
        self.assertEqual(len(children), 6, "Loading incomplete")
        self.assertIsNotNone(getattr(self.builder, "grid_frame", None))
        self.assertIsNotNone(getattr(self.builder, "radio", None))
        self.assertIsNotNone(getattr(self.builder, "scale", None))
        self.assertIsNotNone(getattr(self.builder, "entry", None))
        self.assertIsNotNone(getattr(self.builder, "button_10", None))
        self.assertIsNotNone(getattr(self.builder, "label", None))

    def test_properties(self):
        prop = self.builder.button_10.place_info()
        # strangely place_info returns values as strings
        # so we convert to int first
        self.assertEqual(int(prop.get("x")), 20)
        self.assertEqual(int(prop.get("y")), 280)
        self.assertEqual(int(prop.get("width")), 400)
        self.assertEqual(int(prop.get("height")), 60)
        self.assertEqual(prop.get("bordermode"), tk.OUTSIDE)


class GridLayoutTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("common_layout.xml"))

    def test_loading(self):
        children = self.builder.grid_frame.winfo_children()
        self.assertEqual(len(children), 7)
        self.assertIsNotNone(getattr(self.builder, "button_1", None))
        self.assertIsNotNone(getattr(self.builder, "button_2", None))
        self.assertIsNotNone(getattr(self.builder, "button_3", None))
        self.assertIsNotNone(getattr(self.builder, "button_4", None))
        self.assertIsNotNone(getattr(self.builder, "button_5", None))
        self.assertIsNotNone(getattr(self.builder, "button_6", None))
        self.assertIsNotNone(getattr(self.builder, "pack_frame", None))

    def test_properties(self):
        btn2_info = self.builder.button_2.grid_info()
        self.assertEqual(btn2_info.get("padx"), 5)
        self.assertEqual(btn2_info.get("pady"), 5)
        self.assertEqual(btn2_info.get("ipadx"), 20)
        self.assertEqual(btn2_info.get("ipady"), 20)
        self.assertEqual(sorted(btn2_info.get("sticky", "")), sorted('nswe'))
        self.assertEqual(btn2_info.get("row"), 1)
        self.assertEqual(btn2_info.get("column"), 0)
        self.assertEqual(btn2_info.get("rowspan"), 1)
        self.assertEqual(btn2_info.get("columnspan"), 2)

        btn6 = self.builder.button_6
        self.assertEqual(btn6.cget("width"), 4)
        self.assertEqual(btn6.cget("height"), 1)


class PackLayoutTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("common_layout.xml"))

    def test_loading(self):
        children = self.builder.pack_frame.winfo_children()
        self.assertEqual(len(children), 4)
        self.assertIsNotNone(getattr(self.builder, "button_7", None))
        self.assertIsNotNone(getattr(self.builder, "button_8", None))
        self.assertIsNotNone(getattr(self.builder, "button_9", None))
        self.assertIsNotNone(getattr(self.builder, "button_n8", None))

    def test_properties(self):
        info = self.builder.button_9.pack_info()
        self.assertEqual(info.get("padx"), 5)
        self.assertEqual(info.get("pady"), 5)
        self.assertEqual(info.get("ipadx"), 5)
        self.assertEqual(info.get("ipady"), 5)
        self.assertEqual(info.get("anchor"), tk.W)
        self.assertEqual(info.get("expand"), True)
        self.assertEqual(info.get("fill"), tk.BOTH)
        self.assertEqual(info.get("side"), tk.BOTTOM)

        btn8 = self.builder.button_8
        self.assertEqual(btn8.cget("width"), 9)
        self.assertEqual(btn8.cget("height"), 2)

        btn8native = self.builder.button_n8
        self.assertEqual(btn8native.cget("width"), 9)
