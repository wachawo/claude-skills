---
name: python-pep8
description: Detailed PEP 8 guide for Python code — layout, imports, names, whitespace, comments, programming recommendations (None comparisons, exceptions, return, strings). Use when reviewing or fixing the style of a Python file, mentioning "PEP 8", "code style", or wanting to bring code into line with the canon.
---

# PEP 8 for Python

A summary of [PEP 8](https://peps.python.org/pep-0008/) with practical do/don't examples. Ruff/black handle formatting automatically — this guide is about the *semantic* decisions auto-formatters do not make.

## 1. Code layout

### Indentation

4 spaces per level. No tabs in new code.

```python
# OK
def f(
        a, b, c,
        d):
    print(a)

# OK (vertical alignment)
result = some_fn(arg1, arg2,
                 arg3, arg4)
```

### Line length

- Code: **79** characters (PEP 8) or **88** (black/ruff default — recommended).
- Docstrings/comments: **72**.

```python
# Bad (too long)
result = some_very_long_function_name_that_exceeds_the_character_limit(a, b, c)

# Good
result = some_very_long_function_name_that_exceeds_the_character_limit(
    a, b, c,
)
```

### Blank lines

- **Two** blank lines between top-level functions/classes.
- **One** between methods of a class.
- Blank lines inside a function — sparingly, for logical blocks.

```python
class A:
    def m1(self): ...

    def m2(self): ...


def standalone():
    ...
```

### Line breaks at binary operators

Break **before** the operator, not after (mathematical convention, reads more clearly).

```python
# Good
income = (gross_wages
          + taxable_interest
          - ira_deduction)

# Bad
income = (gross_wages +
          taxable_interest -
          ira_deduction)
```

### Encoding

UTF-8 without BOM. No `# -*- coding: utf-8 -*-` in Python 3 (it is already the default).

## 2. Imports

Groups (with a blank line between):
1. Standard library.
2. Third-party packages.
3. Local modules.

```python
import os
import sys
from datetime import datetime

import flask
import peewee

from models import User
from serializers import user_serializer
```

- **One import per line**: `import os` + `import sys`, not `import os, sys`.
- **Absolute imports preferred**: `from myapp.utils import x`, not `from .utils import x` (except in explicit package cases).
- **No** `from x import *`.
- Imports at the top of the file, after the module docstring.

## 3. Naming

| Entity | Style | Example |
|---|---|---|
| Module / package | `snake_case` | `data_processor.py` |
| Class | `PascalCase` | `UserAccount`, `HTTPServer` |
| Exception | `PascalCase` + `Error` | `ValidationError` |
| Function, method | `snake_case` | `calculate_total` |
| Variable | `snake_case` | `user_count` |
| Constant | `UPPER_CASE` | `MAX_CONNECTIONS = 100` |
| Type variable | short `PascalCase` | `T`, `KT`, `VT` |

Special notes:

- `self` for instance methods, `cls` for classmethod. Not `this`, not `obj`.
- Conflict with a keyword: `class_`, `type_` (trailing underscore).
- **One** leading `_` — non-public (by convention, not enforced).
- **Two** leading `__` — name mangling (only meaningful in inheritance).
- **Two** on both sides `__name__` — dunder, do not define your own.

```python
# Bad
class user_account: pass         # should be PascalCase
def CalcTotal(): pass            # should be snake_case
maxConnections = 100             # should be UPPER_CASE
def m(this, x): pass             # should be self
```

## 4. Whitespace in expressions

### Don't crowd

```python
# Good
spam(ham[1], {eggs: 2})
if x == 4:
    print(x)

# Bad
spam( ham[ 1 ], { eggs: 2 } )
if x == 4 :
    ...
```

### Binary operators

One space around. With mixed precedence, you may omit spaces around higher-precedence operators.

```python
# Good
i = i + 1
hypot2 = x*x + y*y    # acceptable: multiplication has higher precedence

# Bad
i=i+1
x = x*2-1             # inconsistent
```

### Keyword arguments / default values

**No** spaces around `=` for default parameter values and kwargs.

```python
# Good
def fn(real, imag=0.0):
    return magic(r=real, i=imag)

# Bad
def fn(real, imag = 0.0):
    return magic(r = real, i = imag)
```

But when there is a type annotation, spaces around `=` **are** present:

```python
# Good
def fn(real: float, imag: float = 0.0): ...

# Bad
def fn(real: float, imag: float=0.0): ...
```

### Commas, colons, semicolons

Space after, not before.

```python
# Good
if x == 4: print(x, y)
foo = (0,)

# Bad
if x == 4 : print(x , y)
foo = (0, )
```

## 5. Comments and docstrings

### Block comments

`#` + one space. Full sentences, capital letter. Indentation level matches the code being commented on.

```python
# Apply tax at the regional rate.
# Round to two decimal places — compliance requirement.
total = base * (1 + tax_rate)
```

### Inline comments

At least **2 spaces** before `#`, then `# `. Use sparingly — only when explaining *why*, not *what*.

```python
x = x + 1  # Compensate for boundary offset
```

### Docstrings (PEP 257)

- All public modules, functions, classes, methods.
- Single-line — `"""..."""`, no blank lines.
- Multi-line — closing `"""` on its own line.

```python
def fetch_data():
    """Return processed data."""

def long_one():
    """Short summary.

    Longer description with details and examples.
    """
```

## 6. Programming recommendations

### Comparing with None — `is` / `is not`

```python
# Good
if x is None: ...
if x is not None: ...

# Bad
if x == None: ...
if not x is None: ...     # reads ambiguously
```

### Boolean — without explicit comparison

```python
# Good
if greeting:
    ...

# Bad
if greeting == True: ...
if greeting is True:  ...   # has cases, but usually redundant
```

### Empty sequences — truthiness, not len()

```python
# Good
if not items: ...
if items:     ...

# Bad
if len(items) == 0: ...
if len(items) > 0:  ...
```

### Exceptions — specific, not bare except

```python
# Good
try:
    import platform
except ImportError:
    platform = None

# Bad
try:
    ...
except:               # also catches KeyboardInterrupt, SystemExit
    pass
```

`except Exception:` is acceptable when you really do catch everything and log it. `except:` — almost never.

### return — consistent style

Either every branch returns a value, or none do. Explicit `return None`.

```python
# Good
def f(x):
    if x >= 0:
        return math.sqrt(x)
    return None

# Bad
def f(x):
    if x >= 0:
        return math.sqrt(x)
    # implicit return None — unclear to the reader whether intentional
```

### Strings — startswith/endswith instead of slices

```python
# Good
if filename.endswith(".txt"): ...
if name.startswith("test_"):  ...

# Bad
if filename[-4:] == ".txt": ...
```

### Type — isinstance, not type()

```python
# Good
if isinstance(x, int): ...
if isinstance(x, (int, float)): ...

# Bad
if type(x) is int: ...
if type(x) == int: ...
```

### String concatenation

Don't accumulate via `+=` in a loop — `O(n²)`. `"".join(...)` is linear.

```python
# Good
result = "".join(parts)

# Bad
result = ""
for p in parts:
    result += p
```

### Functions instead of `lambda` in `def`

```python
# Good
def square(x):
    return x * x

# Bad
square = lambda x: x * x
```

### Context managers for resources

```python
# Good
with open(path) as f:
    data = f.read()

# Bad
f = open(path)
try:
    data = f.read()
finally:
    f.close()
```

## 7. Modern additions (Python 3.9+)

PEP 8 is the baseline. Modern rules ruff enables by default:

- `list[int]` instead of `List[int]` (Python 3.9+).
- `int | None` instead of `Optional[int]` (Python 3.10+).
- f-strings instead of `%` and `.format()`.
- `match/case` instead of long `if/elif` by type.
- `pathlib.Path` instead of `os.path.join`.

## Automation

Manual PEP 8 → 0. Use:

```bash
ruff check .       # linting (replaces flake8/pylint/isort/...)
ruff format .      # formatting (replaces black)
mypy .             # types
```

`ruff` is the only linter you need in 2025+. Configure in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E", "W",   # pycodestyle (PEP 8)
    "F",        # pyflakes
    "I",        # isort
    "B",        # bugbear
    "UP",       # pyupgrade
    "SIM",      # simplify
    "C4",       # comprehensions
    "N",        # pep8-naming
]
```

## Checklist

```
Layout:
- [ ] 4-space indent, no tabs
- [ ] Lines ≤ 88 characters (docstrings ≤ 72)
- [ ] 2 blank lines between top-level def/class
- [ ] Line break BEFORE the binary operator

Imports:
- [ ] Groups: stdlib / third-party / local
- [ ] One import per line
- [ ] No `from x import *`

Names:
- [ ] Class — PascalCase
- [ ] Function/variable — snake_case
- [ ] Constant — UPPER_CASE

Programming:
- [ ] `is None` / `is not None` (not `== None`)
- [ ] Specific `except`, not bare
- [ ] `if not items` (not `len(items) == 0`)
- [ ] `isinstance(x, T)` (not `type(x) is T`)
- [ ] `"".join(parts)` for concatenation in a loop
- [ ] `with open(...)` for resources
- [ ] `def`, not `name = lambda`

Tooling:
- [ ] `ruff check .` passes
- [ ] `ruff format .` applied
- [ ] `mypy .` passes (in strict, if possible)
```
