import unittest
import tkinter as tk

from formation import AppBuilder
from formation.tests.support import get_resource


class CanvasTestCase(unittest.TestCase):

    def test_load_with_app(self):
        app = tk.Tk()
        build = AppBuilder(app=app, path=get_resource('toplevel.xml'))
        self.assertEqual(app, build._app)

    def test_load_without_app(self):
        build = AppBuilder(path=get_resource('toplevel.xml'))
        self.assertIsNone(build._parent)
        self.assertIsInstance(build._app, tk.Toplevel)

    def test_load_non_toplevel(self):
        build = AppBuilder(path=get_resource('grid_conf.xml'))
        self.assertIsInstance(build._app, tk.Tk)

    def test_toplevel_menu(self):
        build = AppBuilder(path=get_resource('toplevel.xml'))
        self.assertTrue(bool(build._app['menu']))
