import os
import re
import sys

# Nose on Red Hat's Python Import
import multiprocessing

from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError

from setuptools import setup, Extension

cmdclass = {}
PYPY = hasattr(sys, "pypy_version_info")
JYTHON = sys.platform.startswith("java")
requirements = []

if sys.version_info[0] == 2 or (sys.version_info[0] == 3 and sys.version_info[1] < 3):
    requirements.append("ipaddress")
    if os.environ.get("SNYK_TOKEN"):
        with open("requirements.txt", "w") as f:
            for r in requirements:
                f.write(r + "\n")

compile_args = ["-Wall", "-Wextra"]

if sys.version_info[0] == 2:
    compile_args.append("-fno-strict-aliasing")

ext_module = [
    Extension(
        "maxminddb.extension",
        libraries=["maxminddb"],
        sources=["extension/maxminddb.c"],
        extra_compile_args=compile_args,
    )
]

# Pure Python fallback.
ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)


class BuildFailed(Exception):
    def __init__(self):
        self.cause = sys.exc_info()[1]  

class ve_build_ext(build_ext):
    # C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed()
        except ValueError:
            # Windows 64 bit issue fallback
            if "'path'" in str(sys.exc_info()[1]): 
                raise BuildFailed()
            raise


cmdclass["build_ext"] = ve_build_ext

#

ROOT = os.path.dirname(__file__)

with open(os.path.join(ROOT, "README.rst"), "rb") as fd:
    README = fd.read().decode("utf8")

with open(os.path.join(ROOT, "maxminddb", "__init__.py"), "rb") as fd:
    maxminddb_text = fd.read().decode("utf8")
    LICENSE = (
        re.compile(r".*__license__ = \"(.*?)\"", re.S).match(maxminddb_text).group(1)
    )
    VERSION = (
        re.compile(r".*__version__ = \"(.*?)\"", re.S).match(maxminddb_text).group(1)
    )


def status_msgs(*msgs):
    print("*" * 75)
    for msg in msgs:
        print(msg)
    print("*" * 75)


def find_packages(location):
    packages = []
    for pkg in ["maxminddb"]:
        for _dir, subdirectories, files in os.walk(os.path.join(location, pkg)):
            if "__init__.py" in files:
                tokens = _dir.split(os.sep)[len(location.split(os.sep)) :]
                packages.append(".".join(tokens))
    return packages


def run_setup(with_cext):
    kwargs = {}
    if with_cext:
        kwargs["ext_modules"] = ext_module

    setup(
        name="maxminddb",
        version=VERSION,
        author="Gregory Oschwald",
        author_email="programmingwithevin@gmail.com",
        description="MaxMind Reader For DB format",
        long_description=README,
        packages=find_packages("."),
        package_data={"": ["LICENSE"]},
        package_dir={"maxminddb": "maxminddb"},
        python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
        include_package_data=True,
        install_requires=requirements,
        tests_require=["nose"],
        test_suite="nose.collector",
        cmdclass=cmdclass,
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Environment :: Web Environment",
            "Intended Audience :: Developers",
            "Intended Audience :: System Administrators",
            "License :: OSI Approved :: Apache Software License",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python",
            "Topic :: Internet :: Proxy Servers",
            "Topic :: Internet",
        ],
        **kwargs
    )


if PYPY or JYTHON:
    run_setup(False)
    status_msgs(
        "WARNING: Disabling C extension due to Python platform.",
        "Plain-Python build succeeded.",
    )
else:
    try:
        run_setup(True)
    except BuildFailed as exc:
        status_msgs(
            exc.cause,
            "WARNING: The C extension could not be compiled, "
            + "speedups are not enabled.",
            "Failure information, if any, is above.",
            "Retrying the build without the C extension now.",
        )

        run_setup(False)

        status_msgs(
            "WARNING: The C extension could not be compiled, "
            + "speedups are not enabled.",
            "Plain-Python build succeeded.",
        )