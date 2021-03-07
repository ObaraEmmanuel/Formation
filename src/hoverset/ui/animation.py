"""
Animation library for hoverset authors. Allows for animation of various properties
using various easing functions
"""
from threading import Thread
import time
import math


def timed(func):

    def wrap(*args, **kwargs):
        t1 = time.time()
        func(*args, *kwargs)
        t2 = time.time()
        print("function '{}' ran in {} s".format(func.__name__, t2 - t1))

    return wrap


class ChromiumCubicBezier:
    """
    Chromium cubic bezier timing function. The style may not be as pythonic
    owing to the fact that this class was basically directly converted from c++
    (used in the chromium code base) to python.
    """
    # TODO Figure out how to combine solution and slope to factor in velocity of timing
    # till then this implementation is not usable
    k_bezier_epsilon = 1e-7

    def __init__(self, p1x, p1y, p2x, p2y):
        self._cx = 3.0 * p1x
        self._bx = 3.0 * (p2x - p1x) - self._cx
        self._ax = 1.0 - self._cx - self._bx
        self._cy = 3.0 * p1y
        self._by = 3.0 * (p2y - p1y) - self._cy
        self._ay = 1.0 - self._cy - self._by
        self.p1x, self.p1y, self.p2x, self.p2y = p1x, p1y, p2x, p2y

        self.init_gradients()

        self._range_min = 0
        self._range_max = 1

        self.init_range()

    def init_range(self):
        # This works by taking taking the derivative of the cubic bezier, on the y
        # axis. We can then solve for where the derivative is zero to find the min
        # and max distance along the line. We the have to solve those in terms of time
        # rather than distance on the x-axis

        if 0 <= self.p1y < 1 and 0 <= self.p2y <= 1:
            return
        epsilon = self.k_bezier_epsilon

        # Represent the function's derivative in the form at^2 + bt + c
        # as in sampleCurveDerivativeY.
        # (Technically this is (dy/dt)*(1/3), which is suitable for finding zeros
        # but does not actually give the slope of the curve.)

        a = 3.0 * self._ay
        b = 2.0 * self._by
        c = self._cy

        # check if derivative is constant
        if abs(a) < epsilon and abs(b) < epsilon:
            return

        # zeros of te functions derivative
        t1, t2 = 0, 0

        if abs(a) < epsilon:
            # The function's derivative is linear
            t1 = -c / b
        else:
            # Te function's derivative is a quadratic. We find the zeros of this
            # quadratic using the quadratic formula
            discriminant = b * b - 4 * a * c
            if discriminant < 0:
                return
            discriminant_sqrt = math.sqrt(discriminant)
            t1 = (-b + discriminant_sqrt) / (2 * a)
            t2 = (-b - discriminant_sqrt) / (2 * a)

        sol1, sol2 = 0, 0

        # If the solution is in the range [0,1] then we include it, otherwise we
        # ignore it.

        # An interesting fact about these beziers is that they are only
        # actually evaluated in [0,1]. After that we take the tangent at that point
        # and linearly project it out.

        if 0 < t1 < 1:
            sol1 = self.sample_curve_y(t1)

        if 0 < t2 < 1:
            sol2 = self.sample_curve_y(t2)

        self._range_min = min(min(self._range_min, sol1), sol2)
        self._range_max = max(max(self._range_max, sol1), sol2)

    def init_gradients(self):
        # End-point gradients are used to calculate timing function results
        # outside the range [0, 1].
        #
        # There are three possibilities for the gradient at each end:
        # (1) the closest control point is not horizontally coincident with regard to
        #     (0, 0) or (1, 1). In this case the line between the end point and
        #     the control point is tangent to the bezier at the end point.
        # (2) the closest control point is coincident with the end point. In
        #     this case the line between the end point and the far control
        #     point is tangent to the bezier at the end point.
        # (3) the closest control point is horizontally coincident with the end
        #     point, but vertically distinct. In this case the gradient at the
        #     end point is Infinite. However, this causes issues when
        #     interpolating. As a result, we break down to a simple case of
        #     0 gradient under these conditions.

        if self.p1x > 0:
            self._start_gradient = self.p1y / self.p1x
        elif not self.p1y and self.p2x > 0:
            self._start_gradient = self.p2y / self.p2x
        else:
            self._start_gradient = 0

        if self.p2x < 1:
            self._end_gradient = (self.p2y - 1) / (self.p2x - 1)
        elif self.p2x == 1 and self.p1x < 1:
            self._end_gradient = (self.p1y - 1) / (self.p1x - 1)
        else:
            self._end_gradient = 0

    def sample_curve_x(self, t: float) -> float:
        # `ax t ^ 3 + bx t ^ 2 + cx t ' expanded using Horner's rule.
        return ((self._ax * t + self._bx) * t + self._cx) * t

    def sample_curve_y(self, t: float) -> float:
        return ((self._ay * t + self._by) * t + self._cy) * t

    def sample_curve_derivative_x(self, t: float) -> float:
        return (3.0 * self._ax * t + 2.0 * self._bx) * t + self._cx

    def sample_curve_derivative_y(self, t: float) -> float:
        return (3.0 * self._ay * t + 2.0 * self._by) * t + self._cy

    @staticmethod
    def get_default_epsilon() -> float:
        return ChromiumCubicBezier.k_bezier_epsilon

    def solve_curve_x(self, x: float, epsilon: float) -> float:
        # Given an x value, find a parametric value it came from.
        # x must be in [0, 1] range. Doesn't use gradients.
        if not 0.0 <= x <= 1.0:
            raise ValueError("x should be within the closed range [0, 1]")
        t0, t1, t2, x2, d2 = 0, 0, x, 0, 0

        # First try a few iterations of Newton's method -- normally very fast
        for i in range(8):
            x2 = self.sample_curve_x(t2) - x
            if math.fabs(x2) < epsilon:
                return x
            d2 = self.sample_curve_derivative_x(t2)
            if math.fabs(d2) < 1e-6:
                break
            t2 = t2 - x2 / d2

        # Fall back to bisection method for reliability
        t0, t1, t2 = 0, 1, x

        while t0 < t1:
            x2 = self.sample_curve_x(t2)
            if math.fabs(x2 - x) < epsilon:
                return t2
            if x > x2:
                t0 = t2
            else:
                t1 = t2
            t2 = (t1 - t0) * .5 + t0

        # Failure
        return t2

    def solve(self, x: float) -> float:
        # Evaluate y at given x with default epsilon
        return self.solve_with_epsilon(x, self.k_bezier_epsilon)

    def get(self, x: float) -> float:
        # Interface method to allow interfacing with hoverset Animation manager.
        return self.solve(x)

    def solve_with_epsilon(self, x: float, epsilon: float):
        # Evaluates y at the given x. The epsilon parameter provides a hint as to the
        # required accuracy and is not guaranteed. Uses gradients if x is
        # out of [0, 1] range.

        if x < 0.0:
            return 0.0 + self._start_gradient * x
        if x > 1.0:
            return 1.0 + self._end_gradient * (x - 1.0)
        return self.sample_curve_y(self.solve_curve_x(x, epsilon))

    def slope(self, x: float) -> float:
        # Returns an approximation of dy/dx at the given x
        return self.slope_with_epsilon(x, self.k_bezier_epsilon)

    def slope_with_epsilon(self, x: float, epsilon: float) -> float:
        x = min(max(x, 0.0), 1.0)
        t = self.solve_curve_x(x, epsilon)
        return self.sample_curve_derivative_y(t) / self.sample_curve_derivative_x(t)


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
