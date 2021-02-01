import unittest

from formation import AppBuilder
from formation.tests.support import get_resource


class Binding(unittest.TestCase):

    def setUp(self) -> None:
        self.clicked = False
        self.builder = AppBuilder(path=get_resource("bindings.xml"))
        self.builder.connect_callbacks(self)

    def on_clk(self, *_):
        self.clicked = True


class EventBindingTestCase(Binding):

    def test_native_binding(self):
        widgets = ("b1", "e1", "f1", "m1")
        for w in widgets:
            with self.subTest(widget_id=w):
                self.clicked = False
                widget = getattr(self.builder, w)
                widget.event_generate("<Button-1>")
                self.assertTrue(self.clicked)

    def test_classic_binding(self):
        widgets = ("b2", "e2", "f2", "m2")
        for w in widgets:
            with self.subTest(widget_id=w):
                self.clicked = False
                widget = getattr(self.builder, w)
                # event generation is sometimes delayed for classic
                # widgets so we gotta force it to work fast
                widget.update()
                widget.event_generate("<Button-1>")
                self.assertTrue(self.clicked)


class CommandBindingTestCase(Binding):

    def test_native_command(self):
        btn = self.builder.b1
        self.assertIn(btn["command"], btn._tclCommands)
        entry = self.builder.e1
        self.assertIn(entry["invalidcommand"], entry._tclCommands)
        self.assertIn(entry["validatecommand"], entry._tclCommands)

    def test_classic_command(self):
        btn = self.builder.b2
        self.assertIn(btn["command"], btn._tclCommands)
        entry = self.builder.e2
        self.assertIn(entry["invalidcommand"], entry._tclCommands)
        self.assertIn(entry["validatecommand"], entry._tclCommands)
        self.assertIn(entry["xscrollcommand"], entry._tclCommands)


class MenuCommandBindingTestCase(Binding):

    def test_native_menu(self):
        menu = self.builder.m1_m
        menu.nametowidget(menu["menu"]).invoke(0)
        self.assertTrue(self.clicked)

    def test_classic_menu(self):
        menu = self.builder.m2_m
        menu.nametowidget(menu["menu"]).invoke(0)
        self.assertTrue(self.clicked)
