import unittest
from studio.tests.support import TestStudioApp
from studio.feature.component_tree import ComponentTree


class StudioMainTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.studio = TestStudioApp.get_instance(className='Formation Studio')

    @classmethod
    def tearDownClass(cls) -> None:
        cls.studio.destroy()

    def test_get_feature(self):
        self.assertIsNone(self.studio.get_feature(str))
        self.assertIsNotNone(self.studio.get_feature(ComponentTree))


if __name__ == '__main__':
    unittest.main()
