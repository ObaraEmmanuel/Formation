import unittest
import tkinter

from formation.utils import CustomPropertyMixin


class SampleWidget(CustomPropertyMixin, tkinter.Frame):

    prop_info = {
        "custom1": {
            "name": "custom1",
            "default": 20,
            "setter": "custom_prop1",
            "getter": "_custom_prop1"
        },
        "custom2": {
            "name": "custom2",
            "default": "#ffffff",
            "setter": "custom_prop2",
            "getter": "_custom_prop2"
        },
    }

    def __init__(self, master=None):
        super(SampleWidget, self).__init__(master)
        self._custom_prop1 = 20
        self._custom_prop2 = "#ffffff"

    def custom_prop1(self, value):
        self._custom_prop1 = value

    def custom_prop2(self, value):
        self._custom_prop2 = value


class CustomPropertyMixinTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.widget = SampleWidget()

    def test_configure(self):
        cnf = self.widget.configure()
        self.assertEqual(cnf["custom1"][:-1], ("custom1", "custom1", "Custom1", 20))
        self.assertEqual(cnf["custom2"][:-1], ("custom2", "custom2", "Custom2", "#ffffff"))

    def test_configure_string(self):
        cnf = self.widget.configure("custom1")
        self.assertEqual(cnf[:-1], ("custom1", "custom1", "Custom1", 20))
        cnf = self.widget.configure("custom2")
        self.assertEqual(cnf[:-1], ("custom2", "custom2", "Custom2", "#ffffff"))
        cnf = self.widget.configure("background")
        self.assertEqual(cnf[:-2], ("background", "background", "Background"))

    def test_configure_empty_dict(self):
        self.assertIsNone(self.widget.configure({}))
        self.assertIsNone(self.widget.config({}))

    def test_config(self):
        self.assertEqual(
            self.widget.configure(),
            self.widget.config()
        )

    def test_config_mod(self):
        self.widget.configure(custom1=40)
        self.assertEqual(self.widget.cget("custom1"), 40)
        self.widget.configure(custom1=60, custom2="#ff00ff")
        self.assertEqual(self.widget.cget("custom1"), 60)
        self.assertEqual(self.widget.cget("custom2"), "#ff00ff")

    def test_config_mod_inbuilt(self):
        self.widget.configure(custom1=60, custom2="#ff00ff", bg="red")
        self.assertEqual(self.widget.cget("custom1"), 60)
        self.assertEqual(self.widget.cget("custom2"), "#ff00ff")
        self.assertEqual(self.widget.cget("bg"), "red")

    def test_cget(self):
        self.assertEqual(self.widget.cget("custom1"), self.widget._custom_prop1)
        self.assertEqual(self.widget.cget("custom2"), self.widget._custom_prop2)

    def test_getitem(self):
        self.assertEqual(self.widget["custom1"], self.widget._custom_prop1)
        self.assertEqual(self.widget["custom2"], self.widget._custom_prop2)
        self.widget.configure(bg="green")
        self.assertEqual(self.widget["bg"], "green")

    def test_setitem(self):
        self.widget["custom1"] = 70
        self.assertEqual(self.widget.cget("custom1"), 70)
        self.widget["bg"] = "orange"
        self.assertEqual(self.widget.cget("bg"), "orange")
