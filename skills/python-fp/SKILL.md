---
name: python-fp
description: Guide to functional-style Python — pure functions, immutability, HOFs, functools/itertools, typed functional patterns. Use when writing new code in a functional style, refactoring classes into functions, mentioning "functional approach", "pure functions", "immutability", or asking to remove side effects.
---

# Functional Python

## When to use

- Writing serializers, helpers, formatters, validators, mappers, converters — anything stateless
- Refactoring a class with a single method + `__init__` into a plain function
- A data transformation pipeline (load → filter → map → aggregate)
- Making code easier to test (a pure function = `assert f(x) == y`, no mocks)

When **not** to use: ORM models, framework extensions (Flask/Marshmallow), long-lived objects with invariants.

## 1. Pure functions

A pure function:
1. **Deterministic** — the same inputs produce the same output.
2. **No side effects** — does not write to globals, files, or the database, and does not mutate its arguments.

```python
# Bad: mutates argument + reads global
TAX = 0.2
def add_total(items):
    for it in items:
        it["total"] = it["price"] * (1 + TAX)
    return items

# Good: pure, tax is a parameter
def with_total(item: dict, tax: float) -> dict:
    return {**item, "total": item["price"] * (1 + tax)}

results = [with_total(it, 0.2) for it in items]
```

Rule: if a function returns `None` and does something, that's a side effect. Isolate such functions at the system boundary (handlers, repositories), and keep the core pure.

## 2. Immutability

Immutable types in Python: `int`, `str`, `bytes`, `tuple`, `frozenset`, `NamedTuple`.

For records in FP style, use **`NamedTuple`** (it's a tuple under the hood, with no `__dict__` and no class behavior):

```python
from typing import NamedTuple

class User(NamedTuple):
    id: int
    name: str
    email: str

u  = User(1, "Alice", "a@x.com")
u2 = u._replace(email="alice@x.com")  # new object, u is untouched
```

If the data has no behavior at all, use a plain `dict` returned from a factory function:

```python
def make_user(id: int, name: str, email: str) -> dict:
    return {"id": id, "name": name, "email": email}

def with_email(user: dict, email: str) -> dict:
    return {**user, "email": email}
```

Read-only view of a dictionary or module constants — via `types.MappingProxyType`:

```python
from types import MappingProxyType

CONFIG = MappingProxyType({"host": "localhost", "port": 5432})
CONFIG["host"] = "x"  # TypeError: 'mappingproxy' does not support item assignment
```

`@dataclass(frozen=True)` is a pragmatic compromise when you need methods, validation in `__post_init__`, or framework integration. In strictly functional code, prefer `NamedTuple` or a dict factory.

For collections, return new ones rather than mutating:

```python
# Bad
def add_tag(tags: list[str], tag: str) -> list[str]:
    tags.append(tag)
    return tags

# Good
def add_tag(tags: tuple[str, ...], tag: str) -> tuple[str, ...]:
    return (*tags, tag)
```

## 3. Higher-order functions

A first-class function: can be passed, returned, and captured in closures.

```python
from functools import partial, reduce
from operator import add, attrgetter, itemgetter

# partial: fix part of the arguments
to_usd = partial(format, fmt="${:.2f}")

# reduce: fold
total = reduce(add, prices, 0)

# operator: atomic operations without lambdas
users.sort(key=attrgetter("created_at"))
rows.sort(key=itemgetter("id"))
```

**Rule**: use `lambda` only for a single short expression inside `key=` / `map` / `filter`. If the body is longer than one line, use a regular `def`.

## 4. Closures and currying

A **closure** is an inner function that captures variables from an outer scope. Useful for configuration and accumulators:

```python
def make_multiplier(factor: int):
    def multiply(x: int) -> int:
        return x * factor
    return multiply

double = make_multiplier(2)
triple = make_multiplier(3)
double(10)  # 20
triple(10)  # 30
```

**Currying** turns a function of N arguments into a chain of one-argument functions. In Python, this is usually done via `functools.partial` (without proper currying):

```python
from functools import partial

def add(a: int, b: int) -> int:
    return a + b

inc = partial(add, 1)
inc(10)  # 11
```

Via a closure (classic currying):

```python
def curry_add(a: int):
    def inner(b: int) -> int:
        return a + b
    return inner

curry_add(2)(3)  # 5
```

If you want true currying with any number of arguments, use `toolz.curry`. The standard library does not provide it.

## 5. functools — must know

```python
from functools import (
    lru_cache,        # memoization of a pure function
    cache,            # = lru_cache(maxsize=None), Python 3.9+
    reduce,           # fold
    partial,          # partial application
    cached_property,  # lazy property, computed once
    singledispatch,   # overload by the type of the first argument
    wraps,            # preserves metadata when decorating
)

@lru_cache(maxsize=128)
def fetch_user(user_id: int) -> User:
    ...
```

You can cache **only pure functions**. Otherwise you'll get stale data.

## 6. itertools — lazy and copy-free

```python
from itertools import (
    chain,        # concatenate iterators
    groupby,      # group ADJACENT items (requires sort)
    islice,       # slice without list()
    accumulate,   # running sum / max / custom function
    takewhile,    # while condition is True
    dropwhile,    # skip while True
    starmap,      # like map, but unpacks tuples
    product,      # Cartesian product
    combinations, # combinations
    pairwise,     # (a, b), (b, c), (c, d), ... — Python 3.10+
)

# Group sorted data
rows.sort(key=itemgetter("category"))
for cat, group in groupby(rows, key=itemgetter("category")):
    process(cat, list(group))

# Running sum
running = list(accumulate([1, 2, 3, 4]))  # [1, 3, 6, 10]
```

## 7. Comprehensions vs map/filter

Idiomatic Python prefers comprehensions for simple cases:

```python
# Good
active = [u for u in users if u.is_active]
emails = [u.email for u in users]

# Use map/filter when you already have a function and don't want a lambda wrapper
parsed = list(map(json.loads, lines))
```

Use a generator expression `(x for x in ...)` instead of a list when materialization isn't needed.

## 8. Composition

Without external libraries, a simple `compose`:

```python
from functools import reduce
from typing import Callable, TypeVar

T = TypeVar("T")

def compose(*funcs: Callable[[T], T]) -> Callable[[T], T]:
    """compose(f, g, h)(x) == f(g(h(x)))"""
    return reduce(lambda f, g: lambda x: f(g(x)), funcs)

normalize = compose(str.strip, str.lower)
normalize("  Hello  ")  # 'hello'
```

For a large pipeline, prefer several lines with named variables over a long chain. Readability beats brevity.

## 9. Typing functional patterns

```python
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import TypeVar, ParamSpec

T = TypeVar("T")
U = TypeVar("U")
P = ParamSpec("P")

def map_filter(
    items: Iterable[T],
    pred: Callable[[T], bool],
    fn: Callable[[T], U],
) -> Iterator[U]:
    return (fn(x) for x in items if pred(x))

# Decorator that preserves the signature
def trace(fn: Callable[P, T]) -> Callable[P, T]:
    @wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        result = fn(*args, **kwargs)
        return result
    return wrapped
```

For a clean callback, use `Protocol` if you need several methods; `Callable` if just one.

## 10. Anti-patterns

```python
# Bad: mutable default
def append_id(item, ids=[]):
    ids.append(item["id"])
    return ids

# Good
def append_id(item, ids: tuple[int, ...] = ()) -> tuple[int, ...]:
    return (*ids, item["id"])
```

```python
# Bad: side effect in a comprehension
[print(x) for x in items]

# Good: a regular loop
for x in items:
    print(x)
```

```python
# Bad: mutation while iterating
for u in users:
    if u.expired:
        users.remove(u)

# Good: a new list
active = [u for u in users if not u.expired]
```

```python
# Bad: deeply nested lambdas
list(map(lambda x: x * 2, filter(lambda x: x > 0, map(lambda x: x - 1, nums))))

# Good: named steps
shifted   = (n - 1 for n in nums)
positive  = (n for n in shifted if n > 0)
result    = [n * 2 for n in positive]
```

## 11. Optional libraries

- `toolz` / `cytoolz` — `pipe`, `curry`, `merge`, `groupby` (with an arbitrary key function, unlike `itertools.groupby`)
- `funcy` — `compose`, `iffy`, `lmap`, `ldistinct`, useful helpers
- `returns` — `Result`, `Maybe`, `IO` for strict FP

Don't pull these in unnecessarily. The standard `functools + itertools + operator` covers 90% of cases.

## 12. Architecture: immutable core — mutable shell

Pure functional code is impossible in a real application: somewhere you have to read the database, write files, hit the network. The principle:

- **Core** — pure functions, immutable data, no side effects. Business logic lives here.
- **Shell** — handlers, repositories, API clients, file I/O. Side effects only happen here.

```
HTTP request → handler (shell)
                  ↓
              parse + validate → pure functions (core)
                  ↓
              compute result → pure functions (core)
                  ↓
              save / send (shell) → response
```

In a Flask stack, the core is `serializers.py`, `validators.py`, and pure helper functions. The shell is endpoints in `app1.py`, `db.py`, and ORM methods. Core tests need no mocks — just asserts. Shell tests are integration tests.

## Pre-commit checklist

```
- [ ] Function returns a value rather than mutating arguments
- [ ] Default arguments are immutable (None, (), frozenset())
- [ ] Global state is not read from inside
- [ ] Type hints: Callable / Iterable / Iterator / Sequence
- [ ] @lru_cache only on pure functions
- [ ] If a function returns None, it's clearly a side effect (DB/file/log write)
- [ ] lambda only one-liner and only inside key=/map/filter
- [ ] map/filter/reduce chains broken into named variables when > 3 steps
```
