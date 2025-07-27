# Contributing

Thank you for considering contributing to *Tiến Lên*! The following guidelines help keep development consistent.

## Getting started

1. Fork the repository and create a feature branch from `main`.
2. Install development dependencies and pre-commit hooks:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e .[dev,test]
   pre-commit install
   ```

3. Run `pre-commit run --all-files` before committing to automatically format code and run linters.
4. Add tests where applicable and ensure `pytest -vv` passes.
5. Open a pull request describing your changes.

## Code style

The project uses **Black** and **isort** for formatting. Type checking is performed with **mypy** and linting with **flake8**. The `pre-commit` configuration runs all tools automatically.

## Branching model

Work in feature branches and submit pull requests against `main`. Keep commits focused and write meaningful messages.

## License

By contributing you agree that your work will be released under the MIT License.
