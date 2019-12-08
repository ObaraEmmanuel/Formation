from .support import MockApp
from ..app import MAX_GRID_HEIGHT, MAX_GRID_WIDTH, App
import unittest
from .. import components

MAX_GRID_SIZE = MAX_GRID_HEIGHT*MAX_GRID_WIDTH
# For testing purposes ensure these conditions are met
assert MAX_GRID_HEIGHT >= 8, "Height constraint for testing failed"
assert MAX_GRID_WIDTH >= 10, "Width constraint for testing failed"


class AppGridHandlingTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()

    def test_init_grids(self):
        # init_grids runs on initialization so just go ahead and assert
        self.assertEqual(len(self.app.body.winfo_children()), MAX_GRID_SIZE, "Grid initialization failed")
        self.assertEqual(len(self.app.grids), MAX_GRID_WIDTH, "Wrong column arrangement")
        for column in self.app.grids:
            with self.subTest(column=column):
                self.assertEqual(len(column), MAX_GRID_HEIGHT, "column loaded incorrectly")

    def test_size_handling(self):
        size_control = components.RenderSizeControl(self.app)
        self.app.components.append(size_control)
        with self.assertRaises(ValueError, msg="Illegal width size value set"):
            self.app.size = (MAX_GRID_WIDTH + 1, MAX_GRID_HEIGHT)
        with self.assertRaises(ValueError, msg="Illegal height size value set"):
            self.app.size = (MAX_GRID_WIDTH, MAX_GRID_HEIGHT + 1)
        self.app.size = (10, 8)
        self.assertEqual(len(self.app.grid_cluster), 80, "Incorrect size")
        self.assertEqual(size_control.width.get(), 10, "Wrong width value propagated")
        self.assertEqual(size_control.height.get(), 8, "Wrong height value propagated")

    def test_clear_grids(self):
        self.app.clear_grids()
        for grid in self.app.flattened_grids:
            with self.subTest(grid=self.app.flattened_grids.index(grid)):
                self.assertEqual(grid.text, "", "Some grids not cleared")

    def test_rendering(self):
        self.app.size = (10, 8)
        sample_grid = self.app.grid_cluster[0]
        sample_grid.set(45000)
        sample_grid.lock()
        self.app.render(65455)
        for grid in self.app.grid_cluster:
            with self.subTest(grid=grid):
                self.assertNotEqual(grid.text, "", "Incomplete rendering")
        self.assertFalse(sample_grid.is_locked, "Locked not removed by rendering as expected")
        self.app.render(65475)
        # This causes a fracture at 60 grids because then the range is beyond 0xffff
        for grid in self.app.grid_cluster[60:]:
            with self.subTest(grid=grid):
                self.assertEqual(grid.text, "", "Fracture failed. Illegal grid rendering")
        self.app.grid_cluster[0].lock()
        self.app.render(0xffff + 10)
        self.assertTrue(sample_grid.is_locked, "Illegal rendering of a range beyond limit")


class AppFavouritesHandlingTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.prev_fav = self.app.favourites_as_list()

    def tearDown(self) -> None:
        self.app.set_favourites(self.prev_fav)

    def test_key_safety(self):
        self.app.remove_favourites()
        with self.app.get_favourites() as data:
            self.assertIn("favourites", data, "Key safety failed")

    def test_set_favourites(self):
        self.app.set_favourites([(45000, "Arial")])
        self.assertEqual(self.app.favourites_as_list(), [(45000, "Arial")])

    def test_toggling(self):
        self.app.set_favourites([])
        grid = self.app.grid_cluster[0]
        grid.lock()
        self.app.toggle_from_favourites()
        self.assertIn((grid.code_point, grid.font), self.app.favourites_as_list(), "Toggle from favourites failed")
        self.app.toggle_from_favourites()
        self.assertNotIn((grid.code_point, grid.font), self.app.favourites_as_list(), "Toggle from favourites failed")
