import tkinter
import unittest

from formation import AppBuilder
from formation.tests.support import get_resource


class MenuTestCase(unittest.TestCase):
    builder = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("menu.xml"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.builder._app.destroy()

    def test_command(self):
        pass

    def test_menubutton_legacy(self):
        mb1 = self.builder.menubutton_1
        self.assertEqual(mb1.nametowidget(mb1.cget("menu")), self.builder.menu_1)

    def test_menubutton_native(self):
        mb2 = self.builder.menubutton_2
        self.assertEqual(mb2.nametowidget(mb2.cget("menu")), self.builder.menu_2)

    def test_toplevel(self):
        tk1 = self.builder.tk_1
        self.assertEqual(tk1.nametowidget(tk1.cget("menu")), self.builder.menu_3)

    def test_menuitem_config(self):
        m1 = self.builder.menu_1
        self.assertEqual(str(m1.entrycget(0, "background")), "green")
        self.assertEqual(m1.entrycget(1, "label"), "command_2")
        self.assertEqual(str(m1.entrycget(2, "state")), "disabled")
        self.assertEqual(str(m1.entrycget(3, "variable")), str(self.builder.str_var))

    def test_cascade_menu_config(self):
        m1 = self.builder.menu_1
        m2 = m1.nametowidget(m1.entrycget(6, "menu"))
        m3 = m2.nametowidget(m2.entrycget(4, "menu"))
        self.assertEqual(m3.cget("tearoff"), 0)
        self.assertEqual(str(m3.cget("background")), "red")

    def test_menu_config(self):
        m2 = self.builder.menu_2
        self.assertEqual(str(m2.cget("foreground")), "grey20")
        self.assertEqual(m2.cget("title"), "menu_2")

    def test_command_binding(self):
        self.builder.connect_callbacks(self)
        m2 = self.builder.menu_2
        self.assertNotEqual(m2.cget("postcommand"), '')
        self.assertNotEqual(m2.cget("tearoffcommand"), '')
        self.assertNotEqual(m2.entrycget(1, "command"), '')

    def test_old_format_backwards_compatibility(self):
        mb3 = self.builder.menubutton_3
        self.assertIsInstance(mb3.nametowidget(mb3.cget("menu")), tkinter.Menu)