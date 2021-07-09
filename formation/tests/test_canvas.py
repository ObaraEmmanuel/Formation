import unittest

from formation import AppBuilder
from formation.tests.support import get_resource


class CanvasTestCase(unittest.TestCase):
    builder = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("canvas.xml"))
        cls.canvas1 = cls.builder.canvas1
        cls.canvas2 = cls.builder.canvas2

    def test_loading(self):
        self.assertEqual(len(self.canvas1.find_all()), 19)
        self.assertEqual(len(self.canvas2.find_all()), 6)

    def test_line(self):
        line = self.builder.cv1_line
        coords = self.canvas1.coords(line)
        self.assertListEqual(
            list(coords),
            [25, 33, 292, 33, 382, 128, 542, 128, 542, 226]
        )

    def test_polygon(self):
        poly = self.builder.cv1_polygon
        coords = self.canvas1.coords(poly)
        self.assertListEqual(
            list(coords),
            [68, 216, 67, 284, 151, 339, 366, 340, 448, 272, 448, 216]
        )
        self.assertEqual(self.canvas1.itemcget(poly, "fill"), "#1d731d")

    def test_rectangle(self):
        rec = self.builder.cv2_rectangle
        coords = self.canvas2.coords(rec)
        self.assertListEqual(list(coords), [372, 88, 423, 136])
        self.assertEqual(self.canvas2.itemcget(rec, "stipple"), "gray12")
        self.assertEqual(self.canvas2.itemcget(rec, "fill"), "#1d731d")

    def test_oval(self):
        circle = self.builder.cv1_circle2
        coords = self.canvas1.coords(circle)
        self.assertListEqual(list(coords), [177, 59, 288, 169])
        self.assertEqual(self.canvas1.itemcget(circle, "stipple"), "gray12")
        self.assertEqual(self.canvas1.itemcget(circle, "fill"), "#ff0000")
        self.assertEqual(self.canvas1.itemcget(circle, "outline"), "#1d731d")

    def test_arc(self):
        arc = self.builder.cv2_arc1
        coords = self.canvas2.coords(arc)
        self.assertListEqual(list(coords), [78, 37, 190, 133])
        self.assertEqual(float(self.canvas2.itemcget(arc, "extent")), 90.0)
        self.assertEqual(float(self.canvas2.itemcget(arc, "start")), 0.0)
        self.assertEqual(self.canvas2.itemcget(arc, "style"), "pieslice")

    def test_image(self):
        image = self.builder.cv1_image
        self.assertListEqual(list(self.canvas1.coords(image)), [472, 67])
        self.assertTrue(bool(self.canvas1.itemcget(image, "image")))

    def test_bitmap(self):
        bit = self.builder.cv1_bitmap
        self.assertListEqual(list(self.canvas1.coords(bit)), [84, 115])
        self.assertEqual(self.canvas1.itemcget(bit, "bitmap"), "gray12")
        self.assertEqual(self.canvas1.itemcget(bit, "anchor"), "nw")
        self.assertEqual(self.canvas1.itemcget(bit, "background"), "#1d731d")

    def test_text(self):
        text = self.builder.cv2_text
        self.assertListEqual(list(self.canvas2.coords(text)), [280, 114])
        self.assertEqual(self.canvas2.itemcget(text, "text"), "yet another layout")
        self.assertEqual(self.canvas2.itemcget(text, "fill"), "#1d731d")
