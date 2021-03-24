"""
Common validators used in user input points.
All validators should return true if value is valid and false otherwise
Ensure all validators here obey this fundamental design requirement!
"""

import re
import keyword

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{0,6}$")
SIGNED = re.compile(r"^[+\-]$")


# Most methods here are meant for use in realtime validation data entered through a user interface
# For the sake of user experience you may need to pass empty value as valid
# This accommodates for scenarios where the user deletes everything during typing to type a fresh value
def is_empty(value: str) -> bool:
    return value == ""


# Enforce a numeric constraint to the validator
# This returns false if the input is not numeric
def is_numeric(value: str) -> bool:
    # Check if value can be converted to int
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_floating_numeric(num: str) -> bool:
    try:
        float(num)
        return True
    except ValueError:
        return False


def is_signed(text: str) -> bool:
    return bool(re.match(SIGNED, text))


def is_identifier(text: str) -> bool:
    """
    Check whether a string can be used as a valid identifier. It returns false
    if the string is an invalid identifier or is a python keyword
    :param text:
    :return:
    """
    return not keyword.iskeyword(text) and text.isidentifier()


def validate_all(*validators):
    """
    returns a validator that evaluates to true only if all validators passed through
    the argument validators also evaluate to true
    :param validators: validators to be chained
    :return: a validator function
    """

    def validator(value):
        return all(v(value) for v in validators)

    return validator


def validate_any(*validators):
    """
    returns a validator that evaluates to true only if all validators passed through
    the argument validators also evaluate to true
    :param validators: validators to be chained
    :return: a validator function
    """

    def chained_validator(value):
        return any(v(value) for v in validators)

    return chained_validator


def is_hex_color(hex_color: str) -> bool:
    """
    Ensures values obey the format #xxxxxx where x is a hexadecimal value from 0 to f
    :param hex_color:
    :return: bool
    """
    return bool(re.match(HEX_COLOR, hex_color))


check_hex_color = validate_any(is_empty, is_hex_color)


def limit(lower, upper):
    """
    validator that ensures a floating point value is within the stated lower and upper bounds inclusive
    :param lower: An int value representing the lower bound below which the number is considered invalid
    :param upper:  An int value representing the upper bound above which the number is considered invalid
    :return: a validator function for the given bounds
    """

    # No need to fear using int here since @is_numeric shields us from any non numeric values
    def validator(number):
        if is_floating_numeric(number):
            return lower <= float(number) <= upper
        return False

    return validator


def numeric_limit(value, lower, upper):
    """
    A limit validator adjusted to allow for leniency during typing by the user
    while restricting the user to whole numbers
    :param value: An int value to be tested
    :param lower: An int value representing the lower bound below which the number is considered invalid
    :param upper:  An int value representing the upper bound above which the number is considered invalid
    :return: true if number lies within bounds
    """
    return validate_any(is_empty, validate_all(is_numeric, limit(lower, upper)))(value)
