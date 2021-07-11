import enum


class GuideMode(enum.IntEnum):
    MOVE = 1
    RESIZE = 2


class GuideSpec:

    def __init__(self, guide, *args):
        self.guide = guide
        self.snap_delta = (0, 0)
        self.mode = GuideMode.MOVE

    def trigger_snap(self, snap_delta):
        self._throttle = 2
        self.snap_delta = snap_delta

    def reset_snap_delta(self):
        self.snap_delta = (0, 0)

    def draw_guide(self, bounds):
        # renders guides at given bounds
        pass

    def clear_guides(self):
        # removes all guides from view
        pass

    def get_reference(self):
        # get bounding box (x1, y1, x2, y2) of object being moved
        pass

    def get_object_bounds(self):
        # return a tuple (x1, y1, x2, y2) for all objects of interest
        # where x1, y1 is top left corner and x2, y2 is bottom right corner
        pass

    def on_move_start(self):
        self.mode = GuideMode.MOVE
        self.guide.on_drag_start(self)

    def on_resize_start(self):
        self.mode = GuideMode.RESIZE
        self.guide.on_drag_start(self)

    def on_drag(self, point=None):
        self.guide.on_drag(point)

    def on_drag_release(self):
        self.reset_snap_delta()
        self.clear_guides()
        self.guide.on_drag_release()


class Guide:
    __instance = None
    __specs = {}

    def __init__(self, studio):
        self.studio = studio
        self.current_spec = None
        self.index = None
        self.reference = None
        if self.__instance is None:
            self.__instance = self

    def _build_index(self):
        # build vertical and horizontal indices from guidespec.get_object_bounds
        # store at self.index
        pass

    def _render(self):
        if not self.current_spec or self.reference is None:
            return
        # all analysis and guide rendering goes here

    def on_drag_start(self, guidespec):
        self.current_spec = guidespec
        self._build_index()

    def on_drag(self, point=None):
        if self.current_spec is None:
            return
        if point is None and self.current_spec.mode == GuideMode.RESIZE:
            raise ValueError("A reference point is required in resize mode")
        elif self.current_spec.mode == GuideMode.MOVE:
            self.reference = self.current_spec.get_reference()
        else:
            self.reference = point
        self._render()

    def on_drag_release(self):
        # clean up , clear guides, clear index, reset current spec
        # just in case loop was waiting for resume signal
        self.reference = None
        self.current_spec = None

    @classmethod
    def register_spec(cls, key, spec):
        cls.__specs[key] = spec

    @classmethod
    def get_spec(cls, key):
        if key in cls.__specs:
            return cls.__specs[key]
        raise KeyError("Could not find matching spec for {key}")

    @classmethod
    def acquire(cls):
        return cls.__instance
