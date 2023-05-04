import unittest
from formation.meth import Meth
from formation.formats import Node


class MethTestCase(unittest.TestCase):

    def test_initialization_no_type(self):
        m = Meth("func", False, "arg1", "arg2", namedarg="arg3")

        def test(arg1, arg2, **kw):
            self.assertEqual(arg1, "arg1")
            self.assertEqual(arg2, "arg2")
            self.assertEqual(kw["namedarg"], "arg3")

        m.call(test)

    def test_initialization_with_type(self):
        m = Meth("func", False, (1, int), (True, bool), namedarg=(4.5, float))

        def test(arg1, arg2, **kw):
            self.assertEqual(arg1, 1)
            self.assertEqual(arg2, True)
            self.assertEqual(kw["namedarg"], 4.5)

        m.call(test)

    def test_equality(self):

        m1 = Meth("func1", False, "arg1", "arg2", namedarg="arg3")
        m2 = Meth("func2", False, "arg1", namedarg="arg3")
        m3 = Meth("func3", False, ("arg1", str), ("arg2", str), namedarg=("arg3", str))
        m4 = Meth("func4", False, ("arg1", "str"), ("arg2", "str"), namedarg=("arg3", "str"))
        m5 = Meth("func5", False, (1, int), (True, bool), namedarg=(4, float))
        m6 = Meth("func6", False, (1, int), (True, bool), namedarg=(4, int))
        m7 = Meth("func7", False, (1, 'int'), (True, 'bool'), namedarg=(4, 'float'))

        self.assertEqual(m1, m3)
        self.assertEqual(m1, m4)
        self.assertEqual(m4, m3)
        self.assertNotEqual(m1, m2)
        self.assertNotEqual(m5, m6)
        self.assertEqual(m7, m5)

    def test_call(self):
        m = Meth("func", False, "arg1", "arg2", namedarg="arg3")
        arg1 = arg2 = arg3 = None

        def test1(a1, a2, **kw):
            nonlocal arg1, arg2, arg3
            arg1 = a1
            arg2 = a2
            arg3 = kw["namedarg"]

        m.call(test1)

        self.assertEqual(arg1, "arg1")
        self.assertEqual(arg2, "arg2")
        self.assertEqual(arg3, "arg3")

        def test(name, _, __, namedarg):
            self.assertEqual(name, "func")
            self.assertEqual(namedarg, "arg3")

        m.call(test, with_name=True)

    def test_call_deferred(self):
        m = Meth("func", True, "arg1", "arg2", namedarg="arg3")
        arg1 = arg2 = arg3 = None

        def test(a1, a2, **kw):
            nonlocal arg1, arg2, arg3
            arg1 = a1
            arg2 = a2
            arg3 = kw["namedarg"]

        m.call(test, context="mycontext")

        self.assertNotEqual(arg1, "arg1")
        self.assertNotEqual(arg2, "arg2")
        self.assertNotEqual(arg3, "arg3")

        m.call_deferred("othercontext")

        self.assertNotEqual(arg1, "arg1")
        self.assertNotEqual(arg2, "arg2")
        self.assertNotEqual(arg3, "arg3")

        m.call_deferred("mycontext")

        self.assertEqual(arg1, "arg1")
        self.assertEqual(arg2, "arg2")
        self.assertEqual(arg3, "arg3")

    def test_to_node(self):
        m1 = Meth("func", False, "arg1", "arg2", namedarg="arg3")

        parent = Node(None, "test")

        expected = Node(parent, "meth", attrib={"name": "func"})
        Node(expected, "arg", attrib={"value": "arg1"})
        Node(expected, "arg", attrib={"value": "arg2"})
        Node(expected, "arg", attrib={"value": "arg3", "name": "namedarg"})

        actual = m1.to_node(parent)

        self.assertEqual(expected, actual)
        self.assertEqual(parent, actual.parent)

        m2 = Meth("func5", True, (1, int), (True, bool), namedarg=(4.5, float))

        expected = Node(parent, "meth", attrib={"name": "func5", "defer": True})
        Node(expected, "arg", attrib={"value": 1, "type": "int"})
        Node(expected, "arg", attrib={"value": True, "type": "bool"})
        Node(expected, "arg", attrib={"value": 4.5, "name": "namedarg", "type": "float"})

        actual = m2.to_node(parent)

        self.assertEqual(expected, actual)

    def test_from_node(self):
        node = Node(None, "meth", attrib={"name": "func1"})
        Node(node, "arg", attrib={"value": "arg1"})
        Node(node, "arg", attrib={"value": "arg2"})
        Node(node, "arg", attrib={"value": "arg3", "name": "namedarg"})

        expected = Meth("func1", False, "arg1", "arg2", namedarg="arg3")
        actual = Meth.from_node(node)

        self.assertEqual(expected, actual)

        node = Node(None, "meth", attrib={"name": "func", "defer": True})
        Node(node, "arg", attrib={"value": 1, "type": "int"})
        Node(node, "arg", attrib={"value": True, "type": "bool"})
        Node(node, "arg", attrib={"value": 4.5, "name": "namedarg", "type": "float"})

        expected = Meth("func", True, (1, int), (True, bool), namedarg=(4.5, float))
        actual = Meth.from_node(node)

        self.assertEqual(expected, actual)
        self.assertEqual(actual.name, expected.name)
