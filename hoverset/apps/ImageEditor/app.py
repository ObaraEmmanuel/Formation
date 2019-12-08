from hoverset.ui import widgets
from hoverset.ui.icons import get_icon
from hoverset.apps import Categories, BaseApp

from PIL import Image, ImageTk

from .sizing import SizingComponent
from .color import ColorComponent


class App(BaseApp):
    icon = get_icon("image_editor")
    NAME = "Image Editor"
    CATEGORY = Categories.IMAGE_PROCESSING
    IMAGE_PADDING = 20
    SWITCH_SIZE = 50

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)
        self._image_pad = widgets.Frame(self)
        self.switch = widgets.Frame(self, **self.style.dark_on_hover, width=self.SWITCH_SIZE)
        self.control = widgets.ScrolledFrame(self, **self.style.dark, width=300)
        self.switch.pack(fill="y", side="left")
        self.control.pack(fill="y", side="left")
        self._image_pad.pack(fill="both", expand=True, side="left")
        self._image_pad.pack_propagate(False)
        self.canvas = widgets.Canvas(self._image_pad, **self.style.dark_canvas)
        self.canvas.pack(fill="both", expand=True)
        self._image = self.canvas.create_image(self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                                               anchor="center", tags="image")
        self.original = None
        self.image = None
        self.load_image()
        self.components = (
            SizingComponent(self),
            ColorComponent(self),
        )
        self._image_pad.bind("<Configure>", self._image_resized)
        self.selectors = []
        self.install_components()
        self._image_size = (1, 1)
        self.select(self.components[0])
        self.show()

    def install_components(self):
        for index in range(len(self.components)):
            component = self.components[index]
            setattr(component, "selector",
                    widgets.Button(self.switch, **self.style.dark_icon_medium_accent_1,
                                   text=component.ICON))
            component.selector.place(x=0, y=index * self.SWITCH_SIZE, relwidth=1, height=self.SWITCH_SIZE)
            component.selector.on_click(component.select)
            self.selectors.append(component.selector)

    def select(self, component):
        self.control.clear_children()
        for selector in self.selectors:
            selector.config(**self.style.dark_on_hover)
        component.selector.config(**self.style.dark_on_hover_ended)
        component.pack(fill="both", expand=True)

    def load_image(self, path=r"C:\Users\MANU\Desktop\sample.jpg"):
        self.original = Image.open(path)
        self.image = self.original.copy()
        self._render_image()

    def _render_image(self, event=None):
        width, height = self._image_pad.winfo_width(), self._image_pad.winfo_height()
        if event:
            image = self._fit_image(event.width, event.height)
        else:
            self._image_pad.update_idletasks()
            image = self._fit_image(width, height)
        image = ImageTk.PhotoImage(image=image)
        self.canvas.coords(self._image, width // 2, height // 2)
        self.canvas.itemconfigure(self._image, image=image)
        self.canvas.update_idletasks()
        self.canvas.image = image

    def _fit_image(self, width=0, height=0):
        # Sometimes the GUI is still opening up so width and height are 0
        # Well this causes errors during generation of the thumbnails so lets set it to 1 on such occasions
        dimensions = max(1, width - self.IMAGE_PADDING), max(1, height - self.IMAGE_PADDING)
        image = self.image.copy()
        image.thumbnail(dimensions, Image.ANTIALIAS)
        self._image_size = image.size
        return image

    def get_image_size(self):
        return self._image_size

    def update_render(self, image=None):
        # Public method to allow components to update the image externally
        self.image = image
        self._render_image()

    def get_image(self) -> Image:
        return self.image.copy()

    def _image_resized(self, event=None):
        self._render_image(event)
        for component in self.components:
            component.image_size_changed()

    def image_bounds(self):
        return self.canvas.bbox(self._image)

    def show_grid(self, row=8, column=8):
        self.remove_grid()
        x1, y1, x2, y2 = self.image_bounds()
        column_width = (x2 - x1) / column
        row_width = (y2 - y1) / row
        # We need to draw two lines, one black and one white. This allows the user to see the grid
        # despite the image color below.
        for i in range(1, column):
            self.canvas.create_line(x1 + column_width * i, y1, x1 + column_width * i, y2, fill="#000",
                                    tags="grid", width=0.5)
            self.canvas.create_line(x1 + column_width * i+1, y1, x1 + column_width * i+1, y2, fill="#fff",
                                    tags="grid", width=0.5)
        for j in range(1, row):
            self.canvas.create_line(x1, y1 + row_width * j, x2, y1 + row_width * j, fill="#000",
                                    tags="grid", width=0.01)
            self.canvas.create_line(x1, y1 + row_width * j+1, x2, y1 + row_width * j+1, fill="#fff",
                                    tags="grid", width=0.01)

    def remove_grid(self):
        self.canvas.delete("grid")
