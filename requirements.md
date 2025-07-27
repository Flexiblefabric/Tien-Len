# Project Requirements

This project relies on a small set of runtime libraries. The versions are pinned to ensure compatibility across platforms. Install these packages from `requirements.txt` inside your virtual environment.

## Runtime libraries

- `pillow>=10,<12` – used for image loading in the Pygame interface.
- `pygame-ce>=2.5,<3` – provides the Pygame bindings for graphics and input handling.

## Development and testing

Additional tools for formatting, linting and running the test suite are declared in *pyproject.toml* under the optional `dev` and `test` extras:

- `pytest>=8,<9`
- `coverage>=7,<8`
- `pre-commit>=3,<4`
- `black>=24,<25`
- `isort>=5,<6`
- `flake8>=6,<7`
- `mypy>=1,<2`

Install them with `pip install -e .[dev,test]` when working on the codebase.

