# Contributing to Digital Wellbeing

First off, thank you for considering contributing to Digital Wellbeing! It's people like you that make Digital Wellbeing such a great tool.

## How Can I Contribute?

### Reporting Bugs
If you find a bug, please create an issue on GitHub. Include:
- Your operating system version
- The version of the application
- Steps to reproduce the bug
- Expected vs. actual behavior

### Suggesting Enhancements
We are always looking for ways to improve! Please open an issue to suggest a feature. Try to be as detailed as possible.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code lints.
5. Issue that pull request!

### Running automated tests

Install the application dependencies and pytest, then run the suite from the
repository root:

```bash
python -m pip install -r requirements.txt pytest
python -m pytest
```

On a machine without a display, set `QT_QPA_PLATFORM=offscreen` for the test
process. The repository also contains manual launch and screenshot scripts at
the root; these are intentionally excluded from pytest collection and can be
run directly when performing visual QA.

## Code Style
Please adhere to standard PEP 8 guidelines for Python code.
