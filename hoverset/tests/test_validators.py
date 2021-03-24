import unittest
from hoverset.util.validators import *


class ValidatorTestCase(unittest.TestCase):

    def test_is_numeric(self):
        self.assertFalse(is_numeric("some_text_43"))
        self.assertFalse(is_numeric("2.0"))
        self.assertTrue(is_numeric("6"))
        self.assertTrue(is_numeric("+6"))
        self.assertTrue(is_numeric("-6"))

    def test_is_floating_numeric(self):
        self.assertTrue(is_floating_numeric("6.90"))
        self.assertTrue(is_floating_numeric("+6.70"))
        self.assertTrue(is_floating_numeric("-6.6"))
        self.assertTrue(is_floating_numeric("6"))

    def test_is_identifier(self):
        self.assertTrue(is_identifier("var45"))
        self.assertFalse(is_identifier("from"))
        self.assertFalse(is_identifier("45var"))

    def test_is_signed(self):
        self.assertFalse(is_signed("-rtpur"))
        self.assertFalse(is_signed("--"))
        self.assertFalse(is_signed("+6"))
        self.assertTrue(is_signed("+"))
        self.assertTrue(is_signed("-"))

    def test_is_hex(self):
        self.assertTrue(is_hex_color("#ff00ff"))
        self.assertTrue(is_hex_color("#f"))
        self.assertTrue(is_hex_color("#"))
        self.assertTrue(is_hex_color("#abcdef"))
        self.assertFalse(is_hex_color("#fgj"))
        self.assertFalse(is_hex_color("d#k"))
        self.assertFalse(is_hex_color("#fffffff"))

    def test_test_limit(self):
        self.assertTrue(limit(20, 300)("25.6"))
        self.assertTrue(limit(20, 300)("20"))
        self.assertTrue(limit(20, 300)("300"))
        self.assertFalse(limit(20, 300)("2000"))
        self.assertFalse(limit(20, 300)("gkgllk"))


class TestCompositeValidators(unittest.TestCase):

    def test_check_hex_color(self):
        self.assertTrue(check_hex_color(""))
        self.assertTrue(check_hex_color("#ff"))
        self.assertTrue(check_hex_color("#"))

    def test_numeric_limit(self):
        self.assertTrue(numeric_limit("20", 15, 30))
        self.assertFalse(numeric_limit("20.0", 15, 30))
        self.assertFalse(numeric_limit("10", 15, 30))
        self.assertFalse(numeric_limit("40", 15, 30))
        self.assertFalse(numeric_limit("gkgkhk", 15, 30))


class ChainingTestCase(unittest.TestCase):

    def test_validate_all(self):
        validator = validate_all(is_numeric, limit(20, 300))
        self.assertFalse(validator("dfhlhld"))
        self.assertFalse(validator("15"))
        self.assertFalse(validator("400"))
        self.assertTrue(validator("100"))

    def test_validate_any(self):
        validator = validate_any(is_empty, is_floating_numeric, is_hex_color)
        self.assertTrue(validator("#ffe"))
        self.assertTrue(validator(""))
        self.assertTrue(validator("23.6"))
        self.assertFalse(validator("fjlljd"))
