import os
import re
from setuptools import setup, find_packages


HERE = os.path.abspath(os.path.dirname(__file__))


def read_file(filepath):
    with open(filepath, "r") as fd:
        return fd.read()


META_PATH = os.path.join(HERE, "src", "futureproof", "__init__.py")
META_FILE = read_file(META_PATH)


def find_meta(name):
    dunder_name = "__" + name + "__"
    string = META_FILE[META_FILE.index(dunder_name) :]
    try:
        return re.match(r'.*__{0}__ = [\'"]([^\'"]+)[\'"]'.format(name), string).group(
            1
        )
    except AttributeError:
        raise RuntimeError("Unable to find meta value.")


EXTRAS_REQUIRE = {"tests": ["pytest-mock", "pytest-timeout", "coverage"]}

CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

setup(
    name="futureproof",
    version=find_meta("version"),
    url="https://github.com/yeraydiazdiaz/futureproof",
    license="MIT",
    description=find_meta("description"),
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Yeray Diaz Diaz",
    author_email="yeraydiazdiaz@gmail.com",
    packages=find_packages(where="src", exclude=("tests",)),
    package_dir={"": "src"},
    include_package_data=True,
    keywords="concurrent futures multithreading",
    classifiers=CLASSIFIERS,
    install_requires=["attrs"],
    extras_require=EXTRAS_REQUIRE,
)
