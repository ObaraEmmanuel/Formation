import unittest

from formation import AppBuilder
from formation.tests.support import get_resource


class VariablesTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = AppBuilder(path=get_resource("variables.xml"))

    def test_string_var(self):
        var = self.builder.string_var
        self.assertEqual(var.get(), "Sample text")
        self.assertEqual(self.builder.str_1["textvariable"], str(var))
        self.assertEqual(self.builder.str_2["textvariable"], str(var))

    def test_int_var(self):
        var = self.builder.int_var
        self.assertEqual(var.get(), 200)
        self.assertEqual(self.builder.int_1["textvariable"], str(var))
        self.assertEqual(self.builder.int_2["textvariable"], str(var))

    def test_double_var(self):
        var = self.builder.double_var
        self.assertAlmostEqual(var.get(), 50.08)
        self.assertEqual(self.builder.double_1["textvariable"], str(var))
        self.assertEqual(self.builder.double_2["textvariable"], str(var))

    def test_bool_var(self):
        var = self.builder.boolean_var
        self.assertEqual(var.get(), False)
        self.assertEqual(str(self.builder.bool_1["variable"]), str(var))
        self.assertEqual(str(self.builder.bool_2["variable"]), str(var))


if __name__ == '__main__':
    unittest.main()
