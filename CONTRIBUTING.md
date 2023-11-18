# Contributing Guidelines

The following are some guidelines to follow when contributing to TimeBot.

They are **not** strictly enforced, as all Pull Requests are reviewed before accepting, but they should be followed
to the best of your ability.


## Python Version
`TimeBot` targets `Python 3.11` as a minimum. `>=3.12` may currently have issues with installing dependencies.


## Licensing
`TimeBot` uses [Apache License 2.0](https://github.com/TimeEnjoyed/TimeBot/blob/main/LICENSE).
**Apache License 2.0** is a permissive license, and such has few restrictions.


The following license header should be included in any significant portion of original code.

```
Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

If you wish to include your Name/GitHub/Email in any original work, please add it to the top line, E.g.
`Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>, EvieePy <http://github.com/EvieePy>`

If you use any significant portion of code from any other source that is appropriately licensed:
- **Relicensing Allowed:**
  - E.g: MIT License.
  - Inlcude attribution of the original owner, `Name/GitHub/Email` in the top line of *this* license header.

- **Relicensing Not Allowed (File Level):**
  - E.g: Mozilla Public License.
  - Ensure the original licnese allows you to use the code.
  - Include the original license header with original attribution.

- **Proprietary/Relicensing Not Allowed (Project Level):**
  - E.g: `GNU PUblic License` and variations.
  - Do **NOT** use this code in `TimeBot`.

Ultimately it is your responsibility to make sure any code is able to be used under the terms of all licenses involved.


## Virtual Environments
The use of a virtual environment is highly encouraged.

When creating and using a virtual environment please ensure your virtual environment is named:
- `venv`

or

- `.venv`

This will ensure `Typing Coverage and Linting` doesn't break.


## Typing Coverage and Linting
`TimeBot` uses `PyRight` for Type Checking and `Ruff` for linting.
Both have been pre-configured in `pyproject.toml`

**Note:** Any Pull Request must pass all checks before being accepted.

**Note:** If you are unsure on how to fix a particular issue with Typing/Linting, feel free to make your PR and ask for a review.

**Installing:**
The requirements for linting are found in `dev-requirements.txt`.

```
pip install -Ur dev-requirements.txt
```

To ensure your code passes all the checks, run the following before making a Pull Request:

- `ruff check . --fix`
- `pyright .`
  - After running pyright you should get something like this:
    - `0 errors, 0 warnings, 0 informations `


Again, it's ok if you get errors or warnings, as it will be reviewed.

**Key Notes:**

- Use Double Quotes for strings.
- Line Length is `120`.
- There should be atleast `2` lines of whitespace after your imports.
- Comment code where it could be unclear.


Please use typing where you feel comfortable. Your PR will be reviewed later for any issues. Some common patterns:

**Return Types:**
```py
def my_func(...) -> RETURN_TYPE:
    ...

# Real example...
def my_func() -> int:
    return 1
```

**Variable Annotations:**
```py
my_var: TYPE = TYPE()


# Real examples...
my_var: int = 1
other: str = "2"
thing: SomeClass = SomeClass()
```

**Nested Annotations:**
```py
# The following variable is list that should only contain strings...
my_var: list[str] = []

# The following is a list that contains a list of strings and ints...
my_var: list[str | int] = []
```

**Unions:**
```py
# You can use | (Pipe Syntax for unions in Python 3.11) to accept multiple Types.
my_var: int | None = None
my_var = 1

# Another example...
my_var: int | str = 1
my_var = "1"  # Later...
```

**Argument Annotations:**
```py
def my_func(arg: str, other: int, stuff: list[str | float]) ...:
    ...
```

**Default Arguments:**
```py
# arg will default to None if not passed when calling the function...
def my_func(arg: int | None = None) -> int | None:
    return arg

my_func()  # arg is None
my_func(1)  # arg is 1

# This is not allowed
my_func("1")  # type is a str not int or None
```


## Pull Requests
Please ensure you add a detailed/clear description of what you are requesting when opening a pull request.


### Have Fun!