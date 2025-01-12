# -*- coding: utf-8 -*-

#############################################################################
##
## Copyright (C) 2021 The Qt Company Ltd.
## Contact: https://www.qt.io/licensing/
##
## This file is part of the test suite of Qt for Python.
##
## $QT_BEGIN_LICENSE:GPL-EXCEPT$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and The Qt Company. For licensing terms
## and conditions see https://www.qt.io/terms-conditions. For further
## information use the contact form at https://www.qt.io/contact-us.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3 as published by the Free Software
## Foundation with exceptions as appearing in the file LICENSE.GPL3-EXCEPT
## included in the packaging of this file. Please review the following
## information to ensure the GNU General Public License requirements will
## be met: https://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
#############################################################################

import os
import sys
import unittest

from pathlib import Path
sys.path.append(os.fspath(Path(__file__).resolve().parents[1]))
from init_paths import init_test_paths
init_test_paths(True)

from testbinding import ContainerTest


EXPECTED_DICT = {1: ["v1"], 2: ["v2_1", "v2_2"],
                 3: ["v3"],
                 4: ["v4_1", "v4_2"]}


def sort_values(m):
    """Sort value lists in dicts since passing through a QMultiMap changes the order"""
    result = {}
    for key, values in m.items():
        result[key] = sorted(values)
    return result


class ContainerTestTest(unittest.TestCase):

    def testMultiMap(self):
        m1 = ContainerTest.createMultiMap()
        self.assertEqual(sort_values(m1), EXPECTED_DICT)
        m2 = ContainerTest.passThroughMultiMap(m1)
        self.assertEqual(sort_values(m2), EXPECTED_DICT)

    def testMultiHash(self):
        m1 = ContainerTest.createMultiHash()
        self.assertEqual(sort_values(m1), EXPECTED_DICT)
        m2 = ContainerTest.passThroughMultiHash(m1)
        self.assertEqual(sort_values(m2), EXPECTED_DICT)


if __name__ == '__main__':
    unittest.main()

