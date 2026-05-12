import unittest

from formation import AppBuilder
from formation.tests.support import get_resource
from formation.utils import as_posix_path


class PosixPathTestCase(unittest.case.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("image.xml"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.builder._app.destroy()

    def test_native_widget_image_loading(self):
        # Both tests should pass in python 2 and 3
        widgets = [
            "button_2", "checkbutton_2", "radiobutton_1", "label_2"
        ]
        for widget in widgets:
            with self.subTest(widget=widget):
                widget = getattr(self.builder, widget)
                self.assertTrue(bool(widget["image"]))

    def test_legacy_widget_image_loading(self):
        property_map = {
            "button_1": ["image"],
            "checkbutton_1": ["image", "selectimage", "tristateimage"],
            "menubutton_1": ["image"],
            "radiobutton_2": ["image", "selectimage", "tristateimage"],
        }
        for widget_name, properties in property_map.items():
            widget = getattr(self.builder, widget_name)
            for property in properties:
                with self.subTest(widget=widget_name, property=property):
                    self.assertTrue(bool(widget[property]))

    def test_canvas_image_loading(self):
        canvas = self.builder.canvas_1
        image_objs = ["image_1", "image_2"]
        for image_obj in image_objs:
            for property in ["image", "disabledimage", "activeimage"]:
                with self.subTest(image_obj=image_obj, property=property):
                    self.assertTrue(bool(canvas.itemcget(
                        getattr(self.builder, image_obj),
                        property,
                    )))

    def test_menu_image_loading(self):
        menu = self.builder.menu_1
        sub_menu = menu.nametowidget(menu.entrycget(0, "menu"))
        property_map = {
            0: ["image"],
            1: ["image"],
            3: ["image", "selectimage"],
            4: ["image", "selectimage"],
        }
        for index, properties in property_map.items():
            for property in properties:
                with self.subTest(index=index, property=property):
                    self.assertTrue(bool(sub_menu.entrycget(index, property)))


# compatibility tests for older design files with paths in windows format
# newer design files always store paths in posix format
class WindowsPathTestCase(PosixPathTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("image_win.xml"))


class ImagePathUtilityTestCase(unittest.case.TestCase):

    def test_posix_path_to_posix_path(self):
        self.assertEqual(as_posix_path("resource/images"), "resource/images")

    def test_posix_path_to_windows_path(self):
        self.assertEqual(as_posix_path("resource\\images"), "resource/images")
        self.assertEqual(
            as_posix_path("c:\\resource\\images"), "c:/resource/images"
        )
