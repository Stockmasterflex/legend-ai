import os
import re
from foreman_bot import _slugify, _branch_name

def test_slugify_basic():
    assert _slugify("Hello, World!") == "hello-world"


def test_branch_name_format():
    name = _branch_name("bot-fix", "Fix CI exists()")
    assert name.startswith("bot-fix/")
    assert re.search(r"-\d{8}-\d{6}$", name)