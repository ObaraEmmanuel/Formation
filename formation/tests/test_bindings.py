import tkinter
import unittest

from formation import AppBuilder
from formation.tests.support import get_resource
from formation.utils import callback_parse


class Binding(unittest.TestCase):

    def setUp(self) -> None:
        self.clicked = False
        self.args = None
        self.builder = AppBuilder(path=get_resource("bindings.xml"))
        self.builder.connect_callbacks(self)

    def tearDown(self) -> None:
        self.builder._app.destroy()

    def on_clk(self, *_):
        self.clicked = True

    def on_lambda(self, a, b, c, **kw):
        self.args = (a, b, c, kw.get("d"))


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


class LambdaCommand(unittest.TestCase):

    def setUp(self) -> None:
        self.args = None
        self.builder = AppBuilder(path=get_resource("lambda.json"))
        self.builder.connect_callbacks(self)

    def tearDown(self) -> None:
        self.builder._app.destroy()

    def single_arg(self, a):
        self.args = a

    def dual_arg(self, a, b):
        self.args = (a, b)

    def kwarg(self, **kw):
        self.args = kw

    def mixed_arg(self, a, b, **kw):
        self.args = (a, b, kw)

    def test_single_arg(self):
        widgets = ("b1", "b2", "b3", "b4")

        for i, w in enumerate(widgets, 1):
            with self.subTest(widget_id=w):
                self.arg = None
                widget = getattr(self.builder, w)
                # event generation is sometimes delayed for classic
                # widgets so we gotta force it to work fast
                widget.update()
                widget.invoke()
                self.assertEqual(self.args, i)

    def test_dual_arg(self):
        self.args = None
        widget = self.builder.b56
        widget.invoke()
        self.assertEqual(self.args, (5, 6))

    def test_kwarg(self):
        self.args = None
        widget = self.builder.b7
        widget.invoke()
        self.assertEqual(self.args, {"text": "seven"})

    def test_mixed_arg(self):
        self.args = None
        widget = self.builder.b8
        widget.invoke()
        self.assertEqual(self.args, (6, "yes", {"text": "seven", "num": 5}))


class LambdaBinding(unittest.TestCase):

    def setUp(self) -> None:
        self.args = None
        self.event = None
        self.builder = AppBuilder(path=get_resource("lambda.json"))
        self.builder.connect_callbacks(self)

    def tearDown(self) -> None:
        self.builder._app.destroy()

    def single_arg(self, e, a):
        self.args = a
        self.event = e

    def dual_arg(self, e, a, b):
        self.args = (a, b)
        self.event = e

    def kwarg(self, e, **kw):
        self.args = kw
        self.event = e

    def mixed_arg(self, e, a, b, **kw):
        self.args = (a, b, kw)
        self.event = e

    def test_single_arg(self):
        widgets = ("b1", "b2", "b3", "b4")

        for i, w in enumerate(widgets, 1):
            with self.subTest(widget_id=w):
                self.arg = None
                self.event = None
                widget = getattr(self.builder, w)
                # event generation is sometimes delayed for classic
                # widgets so we gotta force it to work fast
                widget.update()
                widget.event_generate("<Button-1>")
                self.assertEqual(self.args, i)
                self.assertIsInstance(self.event, tkinter.Event)

    def test_dual_arg(self):
        self.args = None
        self.event = None
        widget = self.builder.b56
        widget.update()
        widget.event_generate("<Button-1>")
        self.assertEqual(self.args, (5, 6))
        self.assertIsInstance(self.event, tkinter.Event)

    def test_kwarg(self):
        self.args = None
        self.event = None
        widget = self.builder.b7
        widget.update()
        widget.event_generate("<Button-1>")
        self.assertEqual(self.args, {"text": "seven"})
        self.assertIsInstance(self.event, tkinter.Event)

    def test_mixed_arg(self):
        self.args = None
        self.event = None
        widget = self.builder.b8
        widget.update()
        widget.event_generate("<Button-1>")
        self.assertEqual(self.args, (6, "yes", {"text": "seven", "num": 5}))
        self.assertIsInstance(self.event, tkinter.Event)


class CallbackParseTest(unittest.TestCase):

    def test_args(self):
        self.assertEqual(callback_parse("func(2)"), ("func", (2,), {}))
        self.assertEqual(callback_parse("func(2, 3)"), ("func", (2, 3), {}))
        self.assertEqual(callback_parse("func(2, '3', 4)"), ("func", (2, '3', 4), {}))
        self.assertEqual(callback_parse("func(2, \"3\", 4)"), ("func", (2, '3', 4), {}))

    def test_keyword_rejection(self):
        self.assertEqual(callback_parse("whilee()"), ("whilee", (), {}))
        self.assertIsNone(callback_parse("while()"))
        self.assertIsNone(callback_parse("True(45)"))
        self.assertIsNone(callback_parse("True"))

    def test_kwargs(self):
        self.assertEqual(callback_parse("func(a=2)"), ("func", (), {"a": 2}))
        self.assertEqual(callback_parse("func(a= 2, b=3)"), ("func", (), {"a": 2, "b": 3}))
        self.assertEqual(callback_parse("func(a=2, b='3', c=4)"), ("func", (), {"a": 2, "b": '3', "c": 4}))
        self.assertEqual(callback_parse("func(a= 2, b=\"3\", c=4)"), ("func", (), {"a": 2, "b": '3', "c": 4}))

    def test_arg_eval(self):
        self.assertEqual(callback_parse("func(2+3)"), ("func", (5,), {}))
        self.assertEqual(callback_parse("func(2, '3'+'4')"), ("func", (2, '34'), {}))
        self.assertEqual(callback_parse("func(bool(1), arg= float('4.556'))"), ("func", (True,), {'arg': 4.556}))

    def test_no_args(self):
        self.assertEqual(callback_parse("func()"), ("func", (), {}))
        self.assertEqual(callback_parse("func"), ("func", (), {}))

    def test_format_fail(self):
        self.assertIsNone(callback_parse("func(2+3"))
        self.assertIsNone(callback_parse("func(2, '3'+'4'"))
        self.assertIsNone(callback_parse("34func(bool(1), arg= float('4.556'))"))
        self.assertIsNone(callback_parse("func(2+3)r34"))

    def test_eval_fail(self):
        self.assertIsNone(callback_parse("func(2+*3)"))
        self.assertIsNone(callback_parse("func(2, '3'+4)"))
        self.assertIsNone(callback_parse("func(bool(1), arg= float('4.556')"))
