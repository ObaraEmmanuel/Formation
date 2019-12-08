import unittest
from .support import MockApp
from .. import components
import random


def is_sorted(array):
    return sorted(array) == array


class InputBoxTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.component = components.RenderRangeControl(self.app)
        self.app.components.append(self.component)

    def tearDown(self) -> None:
        self.app.destroy()

    def test_hex_int_input(self):
        # Test data in the form (input_value, expected_value)
        test_data = (
            ("2345", 2345),
            ("234555", 2345),
            ("ffff", int("ffff", 16)),
            ("fffff", int("ffff", 16)),
            ("50000", 50000)
        )
        for datum in test_data:
            self.component.input.set(datum[0])
            with self.subTest(test_data=datum):
                self.assertEqual(self.component.input.get(), datum[1], "Validation failed!")

    def test_range_rendering(self):
        self.component.input.set("50000")
        self.component.render_range()
        self.assertEqual(self.app._from, 50000, "Range not rendered correctly")

    def test_receives_range(self):
        self.app.render(40000)
        self.assertEqual(self.component.input.get(), 40000, "Could not receive range.")


class SwipeTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.component = components.Swipe(self.app)
        self.app.components.append(self.component)

    def test_render_next(self):
        self.app.render(40000)
        self.component.next_render()
        size = self.app.size[0] * self.app.size[1]
        self.assertEqual(self.component.range[0], 40000 + size, "Failed to render next batch")
        self.app.size = (15, 8)
        self.assertTupleEqual(self.app.size, (15, 8), "Could not change render size.")
        self.app.render(40000)
        self.component.next_render()
        self.assertEqual(self.component.range[0], 40000 + 15 * 8, "Failed to render next batch at different size")

    def test_render_prev(self):
        self.app.render(40000)
        self.component.prev_render()
        size = self.app.size[0] * self.app.size[1]
        self.assertEqual(self.component.range[0], 40000 - size, "Failed to render previous batch")
        self.app.size = (15, 8)
        self.assertTupleEqual(self.app.size, (15, 8), "Could not change render size.")
        self.app.render(40000)
        self.component.prev_render()
        self.assertEqual(self.component.range[0], 40000 - 15 * 8, "Failed to render previous batch at different size")


class GridTrackerTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.component = components.GridTracker(self.app)
        self.app.components.append(self.component)
        self.grid = self.app.grid_cluster[0]

    def test_grid_reception(self):
        self.assertIsNone(self.app.active_grid, "Active grid prematurely set")
        self.grid.hover(True)
        self.assertEqual(self.component.text, self.grid.text, "Improper grid reception")
        self.app.deactivate_grid()
        self.assertFalse(self.component.text, "Could not reset text")

    def test_grid_deactivation(self):
        self.grid.hover(True)
        self.app.deactivate_grid()
        self.assertFalse(self.component.text, "Could not reset text")

    def test_grid_persistence(self):
        other_grid = self.app.grid_cluster[1]
        self.grid.lock()
        other_grid.hover(True)
        self.assertEqual(self.component.text, other_grid.text, "Improper grid reception")
        self.app.deactivate_grid()
        self.assertEqual(self.component.text, self.grid.text, "Failed to persists locked grid")

    def test_text_format(self):
        self.grid.hover(True)
        # Text format for grid tracker
        for i in range(10, 0xffff, 1310):
            with self.subTest(code_point=i):
                self.grid.set(i)
                self.grid.hover(True)
                t_format = "{} : {}".format(chr(int(self.grid.text, 16)), self.grid.text.replace("0x", ""))
                self.assertEqual(t_format, self.component.info['text'], "Improper text format")


class RenderSizeControlTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.component = components.RenderSizeControl(self.app)
        self.app.components.append(self.component)

    def test_change_reception(self):
        self.app.size = (15, 8)  # size as (width, height)
        self.assertEqual(self.component.width.get(), 15, "Width change not received")
        self.assertEqual(self.component.height.get(), 8, "Height change not received")

    def test_change_width(self):
        self.component.width.set(14)
        self.assertEqual(self.app.size[0], 14, "Could not set width")
        self.assertEqual(self.component.width_val['text'], str(14), "Failed to display width change")

    def test_change_height(self):
        self.component.height.set(9)
        self.assertEqual(self.app.size[1], 9, "Could not set height")
        self.assertEqual(self.component.height_val['text'], str(9), "Failed to display height change")


class FontSelectorTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.component = components.FontSelector(self.app)
        self.app.components.append(self.component)
        self.font = random.choice(self.component._get_fonts())

    def test_font_change(self):
        self.component.input.set(self.font)
        self.component.value_changed()  # We need to do this since there is no mainloop to handle changes
        self.assertEqual(self.component.input.get(), self.font, "Font combobox failed")
        for grid in self.app.grid_cluster:
            with self.subTest(grid=self.app.grid_cluster.index(grid)):
                self.assertEqual(grid.font, self.font, "Could not change font uniformly")

    def test_font_filtering(self):
        fonts = self.component._get_fonts()
        self.assertIsInstance(fonts, list, "Could not fetch fonts")
        self.assertTrue(is_sorted(fonts), "Fonts not sorted")


if __name__ == '__main__':
    unittest.main()
