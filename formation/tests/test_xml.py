import unittest

from lxml import etree

from formation.xml import BaseConverter


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
        node1 = etree.fromstring(xml1)
        node2 = etree.fromstring(xml2)
        self.assertFalse(BaseConverter.is_equal(node1, node2))

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
        node1 = etree.fromstring(xml1)
        node2 = etree.fromstring(xml2)
        self.assertFalse(BaseConverter.is_equal(node1, node2))

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
        node1 = etree.fromstring(xml1)
        node2 = etree.fromstring(xml2)
        node3 = etree.fromstring(xml3)
        self.assertTrue(BaseConverter.is_equal(node1, node2))
        self.assertFalse(BaseConverter.is_equal(node1, node3))


class AttributeHandlingTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.node = etree.fromstring(
            """
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
        )

    def test_get_attr_name(self):
        name = BaseConverter.get_attr_name("layout", "height")
        self.assertEqual(name, "{http://www.hoversetformationstudio.com/layouts/}height")
        self.assertEqual(BaseConverter.get_attr_name(None, "name"), "name")

    def test_extract_attr_name(self):
        attr = "{http://www.hoversetformationstudio.com/layouts/}height"
        self.assertEqual(BaseConverter.extract_attr_name(attr), "height")
        self.assertEqual(BaseConverter.extract_attr_name("name"), "name")

    def test_get_attr(self):
        self.assertEqual(BaseConverter.get_attr(self.node, "height", "layout"), "40")
        self.assertEqual(BaseConverter.get_attr(self.node, "name"), "tag1")

    def test_drop_attr(self):
        BaseConverter.drop_attr(self.node, "width", "layout")
        self.assertNotIn("{http://www.hoversetformationstudio.com/layouts/}width", self.node.attrib)
        # should not cause an exception removing something already removed
        BaseConverter.drop_attr(self.node, "width", "layout")

    def test_load_attr(self):
        BaseConverter.load_attributes({"anchor": "left"}, self.node, "layout")
        self.assertIn("{http://www.hoversetformationstudio.com/layouts/}anchor", self.node.attrib)
        self.assertEqual(BaseConverter.get_attr(self.node, "anchor", "layout"), "left")
        BaseConverter.load_attributes({"id": "200"}, self.node)
        self.assertIn("id", self.node.attrib)
        self.assertEqual(BaseConverter.get_attr(self.node, "id", None), "200")

    def test_attrib_grouping(self):
        grouped = BaseConverter.attrib(self.node)
        self.assertDictEqual(grouped.get("layout"), {"width": "20", "height": "40"})
        self.assertDictEqual(grouped.get("attr"), {"background": "#ffffff", "font": "Arial"})


class MiscUtilitiesTestCase(unittest.TestCase):

    def test_is_var(self):
        self.assertTrue(BaseConverter._is_var("BooleanVar"))
        self.assertFalse(BaseConverter._is_var("IntVariable"))

    def test_get_source_line_info(self):
        node = etree.fromstring("<tag1/>")
        self.assertEqual(BaseConverter.get_source_line_info(node), "Line 1: ")
        # with no source line info available should return empty string
        node = etree.Element('tag1')
        self.assertEqual(BaseConverter.get_source_line_info(node), "")

    def test_get_class(self):
        with self.assertRaises(NotImplementedError):
            BaseConverter._get_class(None)


if __name__ == '__main__':
    unittest.main()
