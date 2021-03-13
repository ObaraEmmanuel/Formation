"""
Animation library for hoverset authors. Allows for animation of various properties
using various easing functions
"""
from threading import Thread
import time


class CubicBezier:
    #  FIXME Bezier does not function with very small duration values, at least for tkinter
    """
    KSpline bezier curve engine implementation similar to that in Mozilla and Chromium
    Utilises Newton Raphson iteration method to perform approximations for parametric cubic bezier function
    """
    NEWTON_ITERATIONS = 4
    NEWTON_MIN_SLOPE = 0.001
    SUBDIVISION_PRECISION = 0.0000001
    SUBDIVISION_MAX_ITERATIONS = 10

    def __init__(self, p0, p1, p2, p3):
        self.p1x = p0
        self.p1y = p1
        self.p2x = p2
        self.p2y = p3
        self.k_spline_table_size = 11
        self.step_size = 1 / (self.k_spline_table_size - 1)
        self.sample_values = [self.calc_bezier(i * self.step_size, p0, p2) for i in range(self.k_spline_table_size)]
        if self.p1x == self.p1y and self.p2x == self.p2y:
            self.get = self.linear_easing
        else:
            self.get = self.bezier_easing

    @staticmethod
    def linear_easing(t):
        return t

    def get_for_x(self, t):
        start, current_sample, last_sample = 0.0, 1, self.k_spline_table_size - 1
        while current_sample != last_sample and self.sample_values[current_sample] <= t:
            start += self.step_size
            current_sample += 1
        current_sample -= 1

        dist = (t - self.sample_values[current_sample]) / (
                self.sample_values[current_sample + 1] - self.sample_values[current_sample])
        guess_for_t = start + dist * self.step_size
        init_slope = self.get_slope(guess_for_t, self.p1x, self.p2x)
        if init_slope >= CubicBezier.NEWTON_MIN_SLOPE:
            return self.newton_raphson_iterate(t, guess_for_t)
        elif init_slope == 0:
            return guess_for_t
        else:
            return self.binary_subdivide(t, start, start + self.step_size)

    def bezier_easing(self, t):
        if t == 0:
            return 0
        if t == 1:
            return 1
        else:
            return self.calc_bezier(self.get_for_x(t), self.p1y, self.p2y)

    def calc_bezier(self, at, a1, a2):
        # checked
        return ((self.a(a1, a2) * at + self.b(a1, a2)) * at + self.c(a1)) * at

    def binary_subdivide(self, ax, a, b):
        # checked
        current_t = a + (b - a) / 2
        current_x = self.calc_bezier(current_t, self.p1x, self.p2x) - ax
        i = 1
        while abs(current_x) > CubicBezier.SUBDIVISION_PRECISION and i < CubicBezier.SUBDIVISION_MAX_ITERATIONS:
            if current_x > 0:
                b = current_t
            else:
                a = current_t
            current_t = a + (b - a) / 2
            current_x = self.calc_bezier(current_t, self.p1x, self.p2x) - ax
            i += 1
        return current_t

    def newton_raphson_iterate(self, ax, at_guess):
        # Newton Raphson iteration
        # checked
        for i in range(CubicBezier.NEWTON_ITERATIONS):
            current_slope = self.get_slope(at_guess, self.p1x, self.p2x)
            if current_slope == 0:
                return at_guess
            current_x = self.calc_bezier(at_guess, self.p1x, self.p2x) - ax
            at_guess -= current_x / current_slope
        return at_guess

    def get_slope(self, at, a1, a2):
        # checked
        return 3 * self.a(a1, a2) * at ** 2 + 2 * self.b(a1, a2) * at + self.c(a1)

    @staticmethod
    def a(a1, a2):
        return 1 - 3 * a2 + 3 * a1

    @staticmethod
    def b(a1, a2):
        return 3 * a2 - 6 * a1

    @staticmethod
    def c(a1):
        return 3 * a1


class Easing:
    # W3C easing specification for web
    # http://www.w3.org/TR/css3-transitions/#transition-timing-function_tag.
    LINEAR = CubicBezier(0, 0, 1, 1)
    EASE = CubicBezier(0.25, 0.1, 0.25, 1)
    EASE_IN = CubicBezier(0.42, 0, 1, 1)
    EASE_OUT = CubicBezier(0, 0, 0.58, 1)
    EASE_IN_OUT = CubicBezier(0.42, 0, 0.58, 1)

    # Custom easing
    SLING_SHOT = CubicBezier(0.7, 0, 0, 1)


class Animate(Thread):
    SLEEP_PRECISION = 0.001  # Average sleep function precision on WINDOWS
    # TODO Determine sleep precision for other OS and implement accordingly
    STEPS = 50

    def __init__(self, element, initial, final, func, **options):
        super().__init__()
        self.count = 0
        self.initial = float(initial)
        self.final = float(final)
        self.duration = self._corrected(float(options.get("dur", 2)))
        self.step_time = self.duration / self.STEPS
        self.range = self.final - self.initial
        self.bezier = options.get("easing", Easing.LINEAR)
        self._on_complete = options.get("on_complete")
        self.func = func
        self.element = element
        self.start()  # Start animation in thread.

    def _get(self):
        count = self.count
        self.count += 1
        return self.range * self.bezier.get(count / self.STEPS) + self.initial

    def _animate(self):
        # Legacy method that utilised tkinter .after method
        # .after method has limitations in that it has an unbound upper limit and yields unstable timing
        # Unstable timing disrupts interpolation hence animations do not appear to follow their timing functions.
        if self.count > self.STEPS:
            self.count = 0
            self.func(self.final)
            return
        self.element.after(int(self.step_time), self._animate)
        value = self._get()
        self.func(value)

    def _corrected(self, duration):
        return max(duration - self.SLEEP_PRECISION * self.STEPS, 0)

    # noinspection PyBroadException
    # @timed
    def run(self) -> None:
        """
        Animation function. It runs in the thread hence does not interfere with the rest of the program thus
        improving user experience. It is less computationally expensive compared to other animation functions defined
        here as only :var self.STEPS number of cycles are performed with the rest of the time spent in sleep. However,
        time.sleep is inaccurate on the upper bound hence animations may take longer than expected! This is the
        preferred method since it's computationally cheap and hence more power efficient.
        :return:
        """
        while self.count <= self.STEPS:
            time.sleep(self.step_time)
            self.func(self._get())
        self.func(self.final)
        if self._on_complete:
            self._on_complete()

    # @timed
    def run_(self) -> None:
        """
        Alternative animation function. It ensures that animations are completed within the specified duration by
        checking time on each loop. The means that if time is up it will be able to determine and end immediately.
        This method is computationally expensive compared to the previous one since all while loop cycles possible
        within the animation duration are carried out each performing expensive time calculations!
        :return:
        """
        bench = time.time()
        while self.count <= self.STEPS:
            t1 = time.time()
            t1 - bench > self.count*self.step_time and self.func(self._get())
        self.func(self.final)
        if self._on_complete:
            self._on_complete()


class AnimateProperty(Animate):

    def __init__(self, element, initial, final, property_, **options):
        self.property = property_
        super().__init__(element, initial, final, self._animate_property, **options)

    def _animate_property(self, value):
        self.element[self.property] = value


if __name__ == '__main__':
    total = 0
    for _ in range(100):
        d = time.time_ns()
        600 * Easing.SLING_SHOT.get(_ / 100) + 50
        total += time.time_ns() - d

    print("Average execution in nanoseconds", total / 100)
