import unittest

from formation.formats import XMLFormat


class EqualityTestCase(unittest.TestCase):

    def test_child_equality(self):
        xml1 = """
        <tag1>
            <tag2/>
            <tag3/>
        </tag1>
        """
        xml2 = """
        <tag1>
            <tag3/>
            <tag2/>
        </tag1>
        """
        node1 = XMLFormat(data=xml1).load()
        node2 = XMLFormat(data=xml2).load()
        self.assertFalse(node1 == node2)
        self.assertTrue(node1 != node2)

    def test_tag_equality(self):
        xml1 = """
        <tag1-ext name="tag1">
            <tag2 width="50"/>
            <tag3/>
        </tag1-ext>
        """
        xml2 = """
        <tag1 name="tag1">
            <tag2 width="50"/>
            <tag3/>
        </tag1>
        """
        node1 = XMLFormat(data=xml1).load()
        node2 = XMLFormat(data=xml2).load()
        self.assertFalse(node1 == node2)
        self.assertTrue(node1 != node2)

    def test_attrib_equality(self):
        xml1 = """
        <tag1 xmlns:attr="http://sample.schema.attr">
            <tag2 attr:width="40" attr:height="50"/>
            <tag3/>
        </tag1>
        """
        xml2 = """
        <tag1 xmlns:attr="http://sample.schema.attr">
            <tag2 attr:height="50" attr:width="40"/>
            <tag3/>
        </tag1>
        """
        xml3 = """
        <tag1 xmlns:attr="http://sample.schema.attr">
            <tag2 attr:height="50"/>
            <tag3 attr:width="40"/>
        </tag1>
        """
        node1 = XMLFormat(data=xml1).load()
        node2 = XMLFormat(data=xml2).load()
        node3 = XMLFormat(data=xml3).load()
        # test correct operator overloading
        self.assertFalse(node1 != node2)
        self.assertTrue(node1 == node2)
        self.assertTrue(node1 != node3)
        self.assertFalse(node1 == node3)


class AttributeHandlingTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.node = XMLFormat(
            data="""
            <tag1
                xmlns:attr="http://www.hoversetformationstudio.com/styles/"
                xmlns:layout="http://www.hoversetformationstudio.com/layouts/"
                attr:background = "#ffffff"
                attr:font = "Arial"
                layout:width = "20"
                layout:height = "40"
                name = "tag1"
            />
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
