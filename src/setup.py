# -*- coding: utf-8 -*-
import setuptools
import py_compile

from vmconstruct import __version__

orig_py_compile = py_compile.compile

def doraise_py_compile(file, cfile=None, dfile=None, doraise=False):
        orig_py_compile(file, cfile=cfile, dfile=dfile, doraise=True)

py_compile.compile = doraise_py_compile

try:
    from Cython.Build import cythonize
except ImportError:
    CYTHON = False
else:
    CYTHON = True


def read__version__():
    """\
    If we don't have all modules for the program available during the build
    we can't complete all the imports.  Instead search for the version
    string by parsing the text.
    """
    with open(".__version__", "wb") as wvp:
        wvp.write(__version__.encode("utf-8"))

    return(__version__)



setuptools.setup(
    zip_safe=False,
    name="vmconstruct",
    version=read__version__(),
    url="https://github.com/JKDingwall/vmconstruct.git",
    author="James Dingwall",
    author_email="james@dingwall.me.uk",
    description="DMUK VM Constructor Tool",
#    long_description=open("README.rst").read(),
    license="Proprietary",
#   Any external package dependencies should be listed
    install_requires=[
        "tabulate"
    ],
    packages=setuptools.find_packages(),
    package_dir={"vmconstruct": "vmconstruct"},
    include_package_data=True,
    package_data={
    },
    entry_points={
        "console_scripts": [
            "vmconstruct = vmconstruct:main"
        ]
    },
    classifiers=[
#        "Development Status :: 5 - Production/Stable",
#        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Environment :: Console",
#        "Operating System :: OS Independent",
#        "Programming Language :: Python :: 3.4",
#        "Programming Language :: Python :: Implementation :: PyPy",
#        "Topic :: Software Development :: Code Generators",
#        "Topic :: Software Development :: Compilers",
#        "Topic :: Software Development :: Interpreters",
#        "Topic :: Text Processing :: General"
    ],
#    extras_require={
#        "future-regex": ["regex"]
#    },
    ext_modules=cythonize(
        "vmconstruct/**/*.py",
        exclude=[
            "vmconstruct/__main__.py",
            "vmconstruct/test/__main__.py",
            "vmconstruct/test/*.py"
        ]
    ) if CYTHON else [],
)
