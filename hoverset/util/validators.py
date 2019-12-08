"""
Common validators used in user input points.
All validators should return true if value is valid and false otherwise
Ensure all validators here obey this fundamental design requirement!
"""

import re
import functools

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{0,6}$")


# Most methods here are meant for use in realtime validation data entered through a user interface
# For the sake of user experience you may need to pass empty value as valid
# This accommodates for scenarios where the user deletes everything during typing to type a fresh value
def empty_is_valid(func):

    @functools.wraps(func)  # Pass the functions attributes to the returned wrapped function
    def wrap(value: str, *args):
        if value == "":
            return True
        return func(value, *args)

    return wrap


# Enforce a numeric constraint to the validator
# This returns false if the input is not numeric
def is_numeric(func):

    @functools.wraps(func)  # Pass the functions attributes to the returned wrapped function
    def wrap(value: str, *args):
        # Check if value can be converted to int
        try:
            int(value)
            return func(value, *args)
        except ValueError:
            return False

    return wrap


@empty_is_valid
def check_hex_color(hex_color: str) -> bool:
    """
    Ensures values obey the format #xxxxxx where x is a hexadecimal value from 0 to f
    :param hex_color:
    :return: bool
    """
    if re.match(HEX_COLOR, hex_color):
        return True
    return False


@empty_is_valid
@is_numeric
def numeric_limit(number, lower, upper):
    """
    Multipurpose validator that ensures the number is within the stated lower and upper bounds
    :param number: An int value to be tested
    :param lower: An int value representing the lower bound below which the number is considered invalid
    :param upper:  An int value representing the upper bound above which the number is considered invalid
    :return: bool
    """
    # No need to fear using int here since @is_numeric shields us from any non numeric values
    if int(number) < lower or int(number) > upper:
        return False
    return True
