#############################################################################
##
## Copyright (C) 2016 The Qt Company Ltd.
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

'''Test cases for QLayout handling of child widgets references'''

import os
import sys
import unittest

from pathlib import Path
sys.path.append(os.fspath(Path(__file__).resolve().parents[1]))
from init_paths import init_test_paths
init_test_paths(False)

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QWidget
from PySide6.QtWidgets import QStackedLayout, QFormLayout
from PySide6.QtWidgets import QApplication, QPushButton, QLabel

from helper.usesqapplication import UsesQApplication


class SaveReference(UsesQApplication):
    '''Test case to check if QLayout-derived classes increment the refcount
    of widgets passed to addWidget()'''

    # Adding here as nose can't see the qapplication attrib we inherit
    qapplication = True

    def setUp(self):
        # Acquire resources
        super(SaveReference, self).setUp()
        self.widget1 = QPushButton('click me')
        self.widget2 = QLabel('aaa')

    def tearDown(self):
        # Release resources
        del self.widget2
        del self.widget1
        super(SaveReference, self).tearDown()

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def checkLayoutReference(self, layout):
        # Checks the reference cound handling of layout.addWidget
        self.assertEqual(sys.getrefcount(self.widget1), 2)
        layout.addWidget(self.widget1)
        self.assertEqual(sys.getrefcount(self.widget1), 3)

        self.assertEqual(sys.getrefcount(self.widget2), 2)
        layout.addWidget(self.widget2)
        self.assertEqual(sys.getrefcount(self.widget2), 3)

        # Check if doesn't mess around with previous widget refcount
        self.assertEqual(sys.getrefcount(self.widget1), 3)

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testMoveLayout(self):
        l = QHBoxLayout()
        self.assertEqual(sys.getrefcount(self.widget1), 2)
        l.addWidget(self.widget1)
        self.assertEqual(sys.getrefcount(self.widget1), 3)

        w = QWidget()
        w.setLayout(l)
        self.assertEqual(sys.getrefcount(self.widget1), 3)

    def testHBoxReference(self):
        # QHBoxLayout.addWidget reference count
        w = QWidget()
        self.checkLayoutReference(QHBoxLayout(w))

    def testVBoxReference(self):
        # QVBoxLayout.addWidget reference count
        w = QWidget()
        self.checkLayoutReference(QVBoxLayout(w))

    def testGridReference(self):
        # QGridLayout.addWidget reference count
        w = QWidget()
        self.checkLayoutReference(QGridLayout(w))

    def testFormReference(self):
        # QFormLayout.addWidget reference count
        w = QWidget()
        self.checkLayoutReference(QFormLayout(w))

    def testStackedReference(self):
        # QStackedLayout.addWidget reference count
        w = QWidget()
        self.checkLayoutReference(QStackedLayout(w))


class MultipleAdd(UsesQApplication):
    '''Test case to check if refcount is incremented only once when multiple
    calls to addWidget are made with the same widget'''

    qapplication = True

    def setUp(self):
        # Acquire resources
        super(MultipleAdd, self).setUp()
        self.widget = QPushButton('click me')
        self.win = QWidget()
        self.layout = QHBoxLayout(self.win)

    def tearDown(self):
        # Release resources
        del self.widget
        del self.layout
        del self.win
        super(MultipleAdd, self).tearDown()

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testRefCount(self):
        # Multiple QLayout.addWidget calls on the same widget
        self.assertEqual(sys.getrefcount(self.widget), 2)
        self.layout.addWidget(self.widget)
        self.assertEqual(sys.getrefcount(self.widget), 3)
        self.layout.addWidget(self.widget)
        self.assertEqual(sys.getrefcount(self.widget), 3)
        self.layout.addWidget(self.widget)
        self.assertEqual(sys.getrefcount(self.widget), 3)


class InternalAdd(UsesQApplication):
    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testInternalRef(self):
        mw = QWidget()
        w = QWidget()
        ow = QWidget()

        topLayout = QGridLayout()

        # unique reference
        self.assertEqual(sys.getrefcount(w), 2)
        self.assertEqual(sys.getrefcount(ow), 2)

        topLayout.addWidget(w, 0, 0)
        topLayout.addWidget(ow, 1, 0)

        # layout keep the referemce
        self.assertEqual(sys.getrefcount(w), 3)
        self.assertEqual(sys.getrefcount(ow), 3)

        mainLayout = QGridLayout()

        mainLayout.addLayout(topLayout, 1, 0, 1, 4)

        # the same reference
        self.assertEqual(sys.getrefcount(w), 3)
        self.assertEqual(sys.getrefcount(ow), 3)

        mw.setLayout(mainLayout)

        # now trasfer the ownership to mw
        self.assertEqual(sys.getrefcount(w), 3)
        self.assertEqual(sys.getrefcount(ow), 3)

        del mw

        # remove the ref and invalidate the widget
        self.assertEqual(sys.getrefcount(w), 2)
        self.assertEqual(sys.getrefcount(ow), 2)


if __name__ == '__main__':
    unittest.main()
