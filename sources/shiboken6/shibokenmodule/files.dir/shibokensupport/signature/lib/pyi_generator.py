# This Python file uses the following encoding: utf-8
#############################################################################
##
## Copyright (C) 2021 The Qt Company Ltd.
## Contact: https://www.qt.io/licensing/
##
## This file is part of Qt for Python.
##
## $QT_BEGIN_LICENSE:LGPL$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and The Qt Company. For licensing terms
## and conditions see https://www.qt.io/terms-conditions. For further
## information use the contact form at https://www.qt.io/contact-us.
##
## GNU Lesser General Public License Usage
## Alternatively, this file may be used under the terms of the GNU Lesser
## General Public License version 3 as published by the Free Software
## Foundation and appearing in the file LICENSE.LGPL3 included in the
## packaging of this file. Please review the following information to
## ensure the GNU Lesser General Public License version 3 requirements
## will be met: https://www.gnu.org/licenses/lgpl-3.0.html.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 2.0 or (at your option) the GNU General
## Public license version 3 or any later version approved by the KDE Free
## Qt Foundation. The licenses are as published by the Free Software
## Foundation and appearing in the file LICENSE.GPL2 and LICENSE.GPL3
## included in the packaging of this file. Please review the following
## information to ensure the GNU General Public License requirements will
## be met: https://www.gnu.org/licenses/gpl-2.0.html and
## https://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
#############################################################################

"""
pyi_generator.py

This script generates .pyi files for arbitrary modules.
"""

import argparse
import io
import logging
import os
import re
import subprocess
import sys
import typing
from pathlib import Path
from contextlib import contextmanager
from textwrap import dedent

sourcepath = Path(__file__).resolve()

from shiboken6 import Shiboken
from shibokensupport.signature.lib.enum_sig import HintingEnumerator
from shibokensupport.signature.lib.tool import build_brace_pattern

# Can we use forward references?
USE_PEP563 = sys.version_info[:2] >= (3, 7)

indent = " " * 4
is_ci = os.environ.get("QTEST_ENVIRONMENT", "") == "ci"
is_debug = is_ci or os.environ.get("QTEST_ENVIRONMENT")

logging.basicConfig(level=logging.DEBUG if is_debug else logging.INFO)
logger = logging.getLogger("generate_pyi")


class Writer(object):
    def __init__(self, outfile):
        self.outfile = outfile
        self.history = [True, True]

    def print(self, *args, **kw):
        # controlling too much blank lines
        if self.outfile:
            if args == () or args == ("",):
                # Python 2.7 glitch: Empty tuples have wrong encoding.
                # But we use that to skip too many blank lines:
                if self.history[-2:] == [True, True]:
                    return
                print("", file=self.outfile, **kw)
                self.history.append(True)
            else:
                print(*args, file=self.outfile, **kw)
                self.history.append(False)


class Formatter(Writer):
    """
    Formatter is formatting the signature listing of an enumerator.

    It is written as context managers in order to avoid many callbacks.
    The separation in formatter and enumerator is done to keep the
    unrelated tasks of enumeration and formatting apart.
    """
    def __init__(self, *args):
        Writer.__init__(self, *args)
        # patching __repr__ to disable the __repr__ of typing.TypeVar:
        """
            def __repr__(self):
                if self.__covariant__:
                    prefix = '+'
                elif self.__contravariant__:
                    prefix = '-'
                else:
                    prefix = '~'
                return prefix + self.__name__
        """
        def _typevar__repr__(self):
            return "typing." + self.__name__
        typing.TypeVar.__repr__ = _typevar__repr__

        # Adding a pattern to substitute "Union[T, NoneType]" by "Optional[T]"
        # I tried hard to replace typing.Optional by a simple override, but
        # this became _way_ too much.
        # See also the comment in layout.py .
        brace_pat = build_brace_pattern(3, ",")
        pattern = fr"\b Union \s* \[ \s* {brace_pat} \s*, \s* NoneType \s* \]"
        replace = r"Optional[\1]"
        optional_searcher = re.compile(pattern, flags=re.VERBOSE)
        def optional_replacer(source):
            return optional_searcher.sub(replace, str(source))
        self.optional_replacer = optional_replacer
        # self.level is maintained by enum_sig.py
        # self.after_enum() is a one-shot set by enum_sig.py .
        # self.is_method() is true for non-plain functions.

    @contextmanager
    def module(self, mod_name):
        self.mod_name = mod_name
        self.print("# Module", mod_name)
        self.print("import PySide6")
        self.print("import typing")
        self.print("from typing import Any, Callable, Dict, List, Optional, Tuple, Union")
        self.print("from PySide6.support.signature.mapping import (")
        self.print("    Virtual, Missing, Invalid, Default, Instance)")
        self.print()
        self.print("class Object(object): pass")
        self.print()
        self.print("from shiboken6 import Shiboken")
        self.print("Shiboken.Object = Object")
        self.print()
        # This line will be replaced by the missing imports postprocess.
        self.print("IMPORTS")
        yield

    @contextmanager
    def klass(self, class_name, class_str):
        spaces = indent * self.level
        while "." in class_name:
            class_name = class_name.split(".", 1)[-1]
            class_str = class_str.split(".", 1)[-1]
        self.print()
        if self.level == 0:
            self.print()
        here = self.outfile.tell()
        if self.have_body:
            self.print(f"{spaces}class {class_str}:")
        else:
            self.print(f"{spaces}class {class_str}: ...")
        yield

    @contextmanager
    def function(self, func_name, signature):
        if self.after_enum() or func_name == "__init__":
            self.print()
        key = func_name
        spaces = indent * self.level
        if type(signature) == type([]):
            for sig in signature:
                self.print(f'{spaces}@typing.overload')
                self._function(func_name, sig, spaces)
        else:
            self._function(func_name, signature, spaces)
        if func_name == "__init__":
            self.print()
        yield key

    def _function(self, func_name, signature, spaces):
        if self.is_method() and "self" not in tuple(signature.parameters.keys()):
            self.print(f'{spaces}@staticmethod')
        signature = self.optional_replacer(signature)
        self.print(f'{spaces}def {func_name}{signature}: ...')

    @contextmanager
    def enum(self, class_name, enum_name, value):
        spaces = indent * self.level
        hexval = hex(value)
        self.print(f"{spaces}{enum_name:25}: {class_name} = ... # {hexval}")
        yield


def get_license_text():
    with sourcepath.open() as f:
        lines = f.readlines()
        license_line = next((lno for lno, line in enumerate(lines)
                             if "$QT_END_LICENSE$" in line))
    return "".join(lines[:license_line + 3])


def find_imports(text):
    return [imp for imp in PySide6.__all__ if imp + "." in text]


def find_module(import_name, outpath):
    """
    Find a module either directly by import, or use the full path,
    add the path to sys.path and import then.
    """
    if import_name.startswith("PySide6."):
        # internal mode for generate_pyi.py
        plainname = import_name.split(".")[-1]
        outfilepath = Path(outpath) / (plainname + ".pyi")
        return import_name, plainname, outfilepath
    # we are alone in external module mode
    p = Path(import_name).resolve()
    if not p.exists():
        raise ValueError(f"File {import_name} does not exist.")
    if not outpath:
        outpath = p.parent
    # temporarily add the path and do the import
    sys.path.insert(0, os.fspath(p.parent))
    plainname = p.name.split(".")[0]
    return plainname, plainname, outpath / (plainname + ".pyi")


def generate_pyi(import_name, outpath, options):
    """
    Generates a .pyi file.
    """
    import_name, plainname, outfilepath = find_module(import_name, outpath)
    top = __import__(import_name)
    obj = getattr(top, plainname) if import_name != plainname else top
    if not getattr(obj, "__file__", None) or Path(obj.__file__).is_dir():
        raise ModuleNotFoundError(f"We do not accept a namespace as module {plainname}")
    module = sys.modules[import_name]

    outfile = io.StringIO()
    fmt = Formatter(outfile)
    fmt.print(get_license_text())  # which has encoding, already
    need_imports = options._pyside_call and not USE_PEP563
    if USE_PEP563:
        fmt.print("from __future__ import annotations")
        fmt.print()
    fmt.print(dedent(f'''\
        """
        This file contains the exact signatures for all functions in module
        {import_name}, except for defaults which are replaced by "...".
        """
        '''))
    HintingEnumerator(fmt).module(import_name)
    fmt.print()
    fmt.print("# eof")
    # Postprocess: resolve the imports
    if options._pyside_call:
        global PySide6
        import PySide6
    with open(outfilepath, "w") as realfile:
        wr = Writer(realfile)
        outfile.seek(0)
        while True:
            line = outfile.readline()
            if not line:
                break
            line = line.rstrip()
            # we remove the IMPORTS marker and insert imports if needed
            if line == "IMPORTS":
                if need_imports:
                    for mod_name in find_imports(outfile.getvalue()):
                        imp = "PySide6." + mod_name
                        if imp != import_name:
                            wr.print("import " + imp)
                wr.print("import " + import_name)
                wr.print()
                wr.print()
            else:
                wr.print(line)
    logger.info(f"Generated: {outfilepath}")
    if options and options.check or is_ci:
        # Python 3.7 and up: We can check the file directly if the syntax is ok.
        if USE_PEP563:
            subprocess.check_output([sys.executable, outfilepath])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This script generates the .pyi file for an arbitrary module.")
    parser.add_argument("module",
        help="The name of an importable module, or the full path to the binary")
    parser.add_argument("--check", action="store_true", help="Test the output")
    parser.add_argument("--outpath",
        help="the output directory (default = binary location)")
    options = parser.parse_args()
    module = options.module
    # XXX find a path that ends in a module and use that
    outpath = options.outpath
    if outpath and not Path(outpath).exists():
        os.makedirs(outpath)
        logger.info(f"+++ Created path {outpath}")
    options._pyside_call = False
    generate_pyi(module, outpath, options=options)

# eof
