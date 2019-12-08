import unittest
from .support import MockApp, MockEvent
from .. import widgets


class GridTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.app = MockApp()
        self.grid = self.app.grid_cluster[0]

    def test_hover(self):
        self.grid.hover(True)
        self.assertEqual(self.grid["bg"], "#bbb", "Hovering failed")
        self.grid.hover(False)
        self.assertEqual(self.grid['bg'], "#f7f7f7", "Could not exit hovering")
        self.grid.set(None)
        self.app.deactivate_grid()
        self.grid.hover(True)
        self.assertEqual(self.grid['bg'], "#f7f7f7", "Illegal hovering. Text required constraint failed")

    def test_lock_system(self):
        self.grid.lock()
        self.assertTrue(self.grid.is_locked, "Failed to lock grid")
        other_grid = self.app.grid_cluster[1]
        other_grid.lock()
        self.assertFalse(self.grid.is_locked, "Could not unlock grid")
        self.grid.hover(True)
        self.grid.lock()
        self.grid.hover(False)
        self.assertEqual(self.grid['bg'], "#bbb", "Grid lost lock on hover exit")
        self.grid.unlock()
        self.grid.set(None)
        self.grid.lock()
        self.assertFalse(self.grid.is_locked, "Text required constraint failed")

    def test_font_handling(self):
        test_fonts = (
            (('Arial', 12), "Arial"),
            ('Arial 12', 'Arial'),
            ('Arial', 'Arial'),
            (('Arial Black', 12), 'Arial Black'),
            ('{Arial Black} 12', 'Arial Black')
        )
        for test_font in test_fonts:
            with self.subTest(font=test_font[0]):
                self.grid['font'] = test_font[0]
                self.assertEqual(self.grid.font, test_font[1])

    def test_copy_mechanism(self):
        self.grid.set(45000)
        self.grid.copy(0)
        self.assertEqual(self.grid.clipboard_get(), "\uafc8", "Failed to copy unicode")
        self.grid.copy(1)
        self.assertEqual(self.grid.clipboard_get(), "afc8", "Failed to copy hex scalar")
        self.grid.copy(2)
        self.assertEqual(self.grid.clipboard_get(), "45000", "Failed to copy code point")

    def test_text_set(self):
        self.grid.set(45000)
        self.assertEqual(self.grid.text, "0xafc8", "Text set incorrectly")
        self.assertEqual(self.grid['text'], chr(45000), "Text set incorrectly")
        self.grid.set(None)
        self.assertEqual(self.grid.text, "", "Text unset incorrectly")
        self.assertEqual(self.grid['text'], "", "Text unset incorrectly")

    def test_menu_request(self):
        self.grid.request_menu(MockEvent())
        self.assertTrue(self.grid.is_locked, "Lock not set on menu request")
        self.grid.set(None)
        self.grid.unlock()
        self.grid.request_menu(MockEvent())
        self.assertFalse(self.grid.is_locked, "Illegal menu request went through")

    def test_data_retrieval(self):
        self.grid['font'] = ('Arial Black', 12)
        self.grid.set(45000)
        data = self.grid.data
        self.assertEqual(data["Font family"], "Arial Black", "Incorrect font returned")
        self.assertEqual(data["Code point"], "45000", "Incorrect code point returned")
        self.assertEqual(data["Hexadecimal scalar"], "afc8", "Incorrect hex scalar returned")


class HexadecimalIntegerTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.widget = widgets.HexadecimalIntegerControl()

    def test_get(self):
        self.widget._data.set('45000')
        self.assertEqual(self.widget.get(), 45000, 'Incorrect get value')
        self.widget._data.set('ffff')
        self.assertEqual(self.widget.get(), 65535, 'Incorrect get value')
        self.widget._data.set('xyz')
        self.assertEqual(self.widget.get(), 0, 'Incorrect get value')

    def test_set(self):
        self.widget.set('45000')
        self.assertEqual(self.widget.get(), 45000, 'Incorrect value set')
        self.widget.set('xyz')
        self.assertEqual(self.widget.get(), 45000, 'Illegal value set')
        self.widget.set('450000')
        self.assertEqual(self.widget.get(), 45000, 'Incorrect get value')

    def test_validator(self):
        self.assertTrue(self.widget.validator('45000'), 'Validator failed')
        self.assertTrue(self.widget.validator('ffff'), 'Validator failed')
        self.assertFalse(self.widget.validator('450000'), 'Validator failed')
        self.assertFalse(self.widget.validator('fffff'), 'Validator failed')


class KeyValueLabelTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.widget = widgets.KeyValueLabel(MockApp(), "key", "value")

    def test_initialization(self):
        self.assertEqual(self.widget._key['text'], "key", "Key set incorrectly")
        self.assertEqual(self.widget._val['text'], "value", "Value set incorrectly")

    def test_copy(self):
        self.widget.copy(None)
        self.assertEqual(self.widget.clipboard_get(), self.widget._val['text'], 'Copying failed')


if __name__ == '__main__':
    unittest.main()
