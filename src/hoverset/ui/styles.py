"""
Custom theme css file parsers loaders and delegator.
"""

import re

patterns = dict(
    selectors=re.compile(r"(?P<selector>.+){"),  # css selectors e.s. .sample1{rule1:val1;} => sample1 is a selector
    bundle=re.compile(r"[^}]+{[^}]*}"),  # css selector and rules combined
    rules=re.compile(r"[^{; ]+:[^};]+"),  # a single css style rule e.s. rule1:val1
    comments=re.compile(r"/\*.*\*/"),  # css comments /*this is a css comment*/
    string_selector=re.compile(r"(?P<selector>[_a-zA-Z]+[_a-zA-Z0-9]*)")  # extract a valid python variable name
)


class RuleContainer(dict):

    def __setitem__(self, k, value):
        if self.get(k):
            if not self.get(k).endswith("!important") or value.endswith("!important"):
                super().__setitem__(k, value)
        else:
            super().__setitem__(k, value)

    def __add__(self, other):
        merged = RuleContainer(self)
        # prevent iteration if other is a None-type
        # this reduces the need to check every time two rule containers are to be merged
        if not other:
            return merged
        for rule in other:
            merged[rule] = other[rule]
        return merged


class StyleContainer(dict):
    """
    The StyleContainer is a specialized dictionary which simplifies handling of selectors and their respective
    style rules from css style sheets. The keys are the css selectors and the values are lists of all rules under that given
    selector.
    Notice that __setitem__ has been overridden to allow:
        1. Automatic overriding of values from redundant selectors and most importantly redundant style
           rules.
        2. Allow for easy implementation of css style precedence where the most important style is added last
           overriding the less important style

    __getitem__ has been overridden for the purposes of memory efficiency in which values are stored as a list of
    tuples but converted to dictionaries on the fly.

    """

    def __setitem__(self, k, value):
        if self.get(k):
            key_map = RuleContainer(self.get(k))
            for rule in value:
                key_map[rule[0]] = rule[1]
            super().__setitem__(k, [(rule, key_map[rule]) for rule in key_map])
        else:
            super().__setitem__(k, value)

    def __getitem__(self, item):
        return RuleContainer(super().__getitem__(item))

    def get_list(self, item):
        return super().__getitem__(item)

    def __add__(self, other):
        merged = StyleContainer(self)
        # prevent iteration if other is a None-type
        # this reduces the need to check every time two style containers are to be merged
        if not other:
            return merged
        for rule in other:
            merged[rule] = other.get_list(rule)
        return merged

    def get(self, item):
        value = super().get(item)
        if value:
            return RuleContainer(value)
        return RuleContainer()


def read_file(file_name):
    # helper function to open files using context
    with open(file_name, "r") as test_file:
        return str(test_file.read())


def merged_files(files):
    """
    :param files:
    :return: A unified file containing rules from all files with the order of addition obeyed
    """
    return "".join([read_file(file) for file in files])


def cleaned_file(file):
    # remove new lines, tabs and comments for easy parsing
    cleaned = read_file(file).replace("\n", "").replace("\t", "")
    for comment in re.findall(patterns["comments"], cleaned):
        cleaned = cleaned.replace(comment, "")
    return cleaned


def tokenize_bundle(bundle):
    # convert all the rules encompassed by a selector to a list of tuples each containing the rule and the value
    return list(map(lambda rule: tuple(map(lambda value: value.strip(), rule.split(":"))),
                    re.findall(patterns["rules"], bundle)))


def parse(files):
    """
    :param files:
    :return: Parse the css files specified in the :param files, build and return a styleContainer
    """
    bundles = re.findall(patterns["bundle"], merged_files(files))
    rule_book = StyleContainer()
    for bundle in bundles:
        selectors = re.search(patterns["selectors"], bundle).group("selector")
        for selector in selectors.split(","):
            rule_book[selector.replace(" ", "")] = tokenize_bundle(bundle)
    return rule_book


class StyleDelegator:

    def __init__(self, *files):
        styles = parse(files)
        # We need to populate the delegator with the css selectors to allow python dot access through the object
        # We don't want to confuse the interpreter so we pick only qualified variable name from the selector
        # This is made possible using the string_selector pattern
        # we then assign the dictionary of rules to the generated attribute
        for selector in styles:
            identifier = re.search(patterns["string_selector"], selector)
            if identifier:
                setattr(self, identifier.group("selector"), dict(styles[selector]))


if __name__ == '__main__':
    s = StyleDelegator("themes/default.css")
    assert hasattr(s, "colors")
