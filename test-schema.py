from io import StringIO
import os
from dataclasses import dataclass, field
from typing import List, Dict, Text, Union, Optional
from dateutil.relativedelta import relativedelta
from datetime import datetime
import dataconf
from pyhocon import HOCONConverter


@dataclass
class Nested:
    a: Text
    b: Text

    def _capitalize_attributes(self):
        attrs = vars(self)
        for key, val in attrs.items():
            setattr(self, key.upper(), val)

    def __post_init__(self):
        self._capitalize_attributes()


@dataclass
class Example:
    hello: Text
    nested: Nested
    world: Text

    def _capitalize_attributes(self):
        attrs = vars(self)
        for key, val in attrs.items():
            setattr(self, key.upper(), val)

    def __post_init__(self):
        self.another = 1
        self._capitalize_attributes()


default_config = """
hello = hi
world = ${?HOME}
# This is a comment
nested {
    a = AAA
    b = BBB
}
"""

config = dataconf.multi.string(default_config).env("DC").on(Example)

print(config)

print(vars(config))
