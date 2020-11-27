import ast
import os
import re

from setuptools import find_packages, setup  # type: ignore

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))


def get_version() -> str:
    main_py = os.path.join(PROJECT_DIR, "sqlvalidator", "main.py")
    _version_re = re.compile(r"__version__\s+=\s+(?P<version>.*)")
    with open(main_py, "r", encoding="utf8") as f:
        match = _version_re.search(f.read())
        version = match.group("version") if match is not None else '"unknown"'
        return str(ast.literal_eval(version))


def get_long_description() -> str:
    readme_md = os.path.join(PROJECT_DIR, "README.md")
    with open(readme_md, encoding="utf8") as md_file:
        return md_file.read()


setup(
    name="sqlvalidator",
    version=get_version(),
    description="SQL queries formatting, syntactic and semantic validation",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/David-Wobrock/sqlvalidator",
    author="David Wobrock",
    author_email="david.wobrock@gmail.com",
    license="MIT",
    packages=find_packages(exclude=["tests/"]),
    extras_require={
        "test": [
            "pytest==6.1.2",
        ]
    },
    keywords=(
        "python sql format "
        "formatter formatting "
        "validation validator validate "
        "automation"
    ),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={"console_scripts": ["sqlvalidator = sqlvalidator.main:_main"]},
)
