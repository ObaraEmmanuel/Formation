from .support import MockApp
from .. import dialogs
import unittest
from .. import components
import random


class AllDialogTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()

    def test_unicode_info(self):
        self.app.grid_cluster[0].lock()
        dialog = dialogs.UnicodeInfo(self.app)
        self.assertIsInstance(dialog, dialogs.UnicodeInfo)
        self.assertEqual(dialog.data, self.app.active_grid.data, "Wrong grid loaded")

    def test_save_as_image(self):
        self.app.grid_cluster[0].lock()
        dialog = dialogs.SaveAsImage(self.app)
        self.assertIsNone(dialog.image, "Premature image grabbing")
        dialog.snip_img()
        self.assertIsNotNone(dialog.image, "Image grab failed")


class ManageFavouritesTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.dialog = dialogs.ManageFavourites(self.app)
        self.prev_fav = self.app.favourites_as_list()

    def tearDown(self) -> None:
        self.app.set_favourites(self.prev_fav)

    def test_favourite_loading(self):
        self.app.set_favourites([
            (45000, 'Arial'), (45000, 'Arial black'), (5000, 'Elephant'), (6000, 'Courier'),
            (45000, 'Courier New'), (5000, 'Lucida Sans'), (4000, 'Lucida Fax')
        ])
        self.dialog.load_favourites()
        self.assertEqual(len(self.dialog.grids), len(self.app.favourites_as_list()), "Could not load favourites")
        self.assertEqual(self.dialog.grids[0].font, 'Arial', 'Incorrect font loaded')
        self.assertEqual(ord(self.dialog.grids[0]['text']), 45000, 'Incorrect code point loaded')

    def test_favourite_clearing(self):
        self.dialog.clear_favourites()
        self.app.set_favourites([(45000, 'Arial'), (45000, 'Arial black')])
        self.dialog.load_favourites()
        self.assertEqual(len(self.dialog.grids), len(self.app.favourites_as_list()), "Could not load favourites")
        self.dialog.clear_favourites()
        self.assertEqual(len(self.dialog.grids), 0, "Could not clear favourites")

    def test_hovering(self):
        self.dialog.clear_favourites()
        self.app.set_favourites([(45000, 'Arial'), (45000, 'Arial black')])
        self.dialog.load_favourites()
        tracker = components.GridTracker(self.dialog)
        self.dialog.components.append(tracker)
        grid_1 = random.choice(self.dialog.grids)
        grid_1.hover(True)
        self.assertEqual(grid_1.text, tracker.text, "Failed to dispatch hovered grid")
        grid_1.hover(False)
        self.dialog.deactivate_grid()
        self.assertEqual(tracker.text, "", "Failed to remove no longer hovered grid")

    def test_lock_mechanism(self):
        self.app.set_favourites([(45000, 'Arial'), (45000, 'Arial black')])
        self.dialog.load_favourites()
        tracker = components.GridTracker(self.dialog)
        self.dialog.components.append(tracker)
        grid_1, grid_2, *_ = self.dialog.grids
        grid_1.lock()
        self.assertEqual(self.dialog.active_grid, grid_1, "Locked failed")
        grid_2.lock()
        self.assertEqual(self.dialog.active_grid, grid_2, "Unlock then lock new failed")
        grid_1.hover(True)
        self.dialog.deactivate_grid()
        self.assertEqual(tracker.text, grid_2.text, "Failed to persist locked grid")

    def test_remove_favourite(self):
        self.app.set_favourites([(45000, 'Arial'), (45000, 'Arial black')])
        self.dialog.load_favourites()
        grid = self.dialog.grids[0]
        grid.lock()
        self.dialog.remove()
        self.assertIsNone(self.dialog.active_grid, "Failed to remove grid")
        self.assertFalse(grid.winfo_ismapped(), "Failed to remove grid from user interface")
        self.assertNotIn((45000, 'Arial'), self.app.favourites_as_list(), "Could not remove grid from shelve")
