import unittest

from formation.formats import JSONFormat


class EqualityTestCase(unittest.TestCase):

    def test_child_equality(self):
        json1 = """
        {
            "type":"tag1",
            "children": [
                {"type": "tag2"},
                {"type": "tag3"}
            ]
        }
        """

        json2 = """
        {
            "type":"tag1",
            "children": [
                {"type": "tag3"},
                {"type": "tag2"}
            ]
        }
        """
        node1 = JSONFormat(data=json1).load()
        node2 = JSONFormat(data=json2).load()
        self.assertFalse(node1 == node2)
        self.assertTrue(node1 != node2)

    def test_tag_equality(self):
        json1 = """
        {
            "type":"tag1-ext",
            "attrib": {
                "name": "tag1"
            },
            "children": [
                {
                    "type": "tag2",
                    "attrib": {
                        "width": "50"
                    }
                },
                {"type": "tag3"}
            ]
        }
        """

        json2 = """
        {
            "type":"tag1",
            "attrib": {
                "name": "tag1"
            },
            "children": [
                {
                    "type": "tag2",
                    "attrib": {
                        "width": "50"
                    }
                },
                {"type": "tag3"}
            ]
        }
        """
        node1 = JSONFormat(data=json1).load()
        node2 = JSONFormat(data=json2).load()
        self.assertFalse(node1 == node2)
        self.assertTrue(node1 != node2)

    def test_attrib_equality(self):
        json1 = """
        {
            "type":"tag1",
            "attrib": {
                "name": "tag1"
            },
            "children": [
                {
                    "type": "tag2",
                    "attrib": {
                        "attr": {
                            "width": "40",
                            "height": "50"
                        }
                    }
                },
                {"type": "tag3"}
            ]
        }
        """

        json2 = """
        {
            "type":"tag1",
            "attrib": {
                "name": "tag1"
            },
            "children": [
                {
                    "type": "tag2",
                    "attrib": {
                        "attr": {
                            "height": "50",
                            "width": "40"
                        }
                    }
                },
                {"type": "tag3"}
            ]
        }
        """

        json3 = """
        {
            "type":"tag1",
            "attrib": {
                "name": "tag1"
            },
            "children": [
                {
                    "type": "tag2",
                    "attrib": {
                        "attr": {
                            "height": "50",
                        }
                    }
                },
                {
                    "type": "tag3",
                    "attrib": {
                        "attr": {
                            "width": "40"
                        }
                    }
                },
            ]
        }
        """

        node1 = JSONFormat(data=json1).load()
        node2 = JSONFormat(data=json2).load()
        node3 = JSONFormat(data=json3).load()
        # test correct operator overloading
        self.assertFalse(node1 != node2)
        self.assertTrue(node1 == node2)
        self.assertTrue(node1 != node3)
        self.assertFalse(node1 == node3)


class AttributeHandlingTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.node = JSONFormat(
            data="""
            {
                "type": "tag1",
                "attrib": {
                    "name": "tag1",
                    "attr": {
                        "background": "#ffffff",
                        "font": "Arial"
                    },
                    "layout": {
                        "width": "20",
                        "height": "40"
                    }
                }
            }
            """
        ).load()

    def test_get_attr(self):
        self.assertEqual(self.node["layout"]["height"], "40")
        self.assertEqual(self.node["name"], "tag1")

    def test_remove_attr(self):
        self.node.remove_attrib("width", "layout")
        self.assertNotIn("width", self.node.attrib["layout"])
        # should not cause an exception removing something already removed
        self.node.remove_attrib("width", "layout")

    def test_load_attr(self):
        self.node["layout"]["anchor"] = "left"
        self.assertIn("anchor", self.node.attrib["layout"])
        self.assertEqual(self.node["layout"]["anchor"], "left")
        self.node["id"] = "200"
        self.assertIn("id", self.node.attrib)
        self.assertEqual(self.node["id"], "200")

    def test_attrib_grouping(self):
        grouped = self.node.attrib
        self.assertDictEqual(grouped.get("layout"), {"width": "20", "height": "40"})
        self.assertDictEqual(grouped.get("attr"), {"background": "#ffffff", "font": "Arial"})


if __name__ == '__main__':
    unittest.main()
