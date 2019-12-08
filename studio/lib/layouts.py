from hoverset.ui.icons import get_icon
from studio import layouts
from studio.lib.pseudo import Groups, PseudoWidget


class FrameLayout(PseudoWidget, layouts.FrameLayout):
    icon = get_icon("frame")
    display_name = "FrameLayout"
    impl = layouts.FrameLayout
    group = Groups.layout

    def __init__(self, master, id_):
        super().__init__(master)
        self.id = id_
        self.setup_widget()

layouts = (
    FrameLayout,
)