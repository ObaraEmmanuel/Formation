"""
Base classes for use by ImageEditor classes
"""


class BaseComponent:
    """
    All components and sub-components must sub-class this base class to allow receiving
    events broadcast by the App
    """

    def select(self, *_):
        self.app.select(self)

    def image_changed(self):
        """
        Any change applied by the app or another component that does not affect the image size or
        orientation. Override this method to implement custom behaviour
        :return:
        """
        pass

    def image_size_changed(self):
        """
        size and orientation related changes. Override this method to implement custom behaviour
        :return:
        """
        pass
