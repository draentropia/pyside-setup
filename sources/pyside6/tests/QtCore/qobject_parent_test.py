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

'''Test cases for parent-child relationship'''

import os
import sys
import unittest

from pathlib import Path
sys.path.append(os.fspath(Path(__file__).resolve().parents[1]))
from init_paths import init_test_paths
init_test_paths(False)

from PySide6.QtCore import QObject, QRegularExpression, QTimer, Qt


class TestObject1(QTimer):
    def __init(self, parent):
        super().__init__(parent)


class TestObject2(TestObject1):
    def __init(self, parent):
        super().__init__(parent)


class ParentRefCountCase(unittest.TestCase):
    '''Test case for the refcount changes of setParent'''

    def setUp(self):
        # Acquire resources
        self.parent = QObject()
        self.child = QObject()

    def tearDown(self):
        # Release resources
        del self.child
        del self.parent

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testSetParent(self):
        # QObject.setParent() refcount changes
        self.assertEqual(sys.getrefcount(self.child), 2)
        self.child.setParent(self.parent)
        self.assertEqual(sys.getrefcount(self.child), 3)

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testSetParentTwice(self):
        self.assertEqual(sys.getrefcount(self.child), 2)
        self.child.setParent(self.parent)
        self.assertEqual(sys.getrefcount(self.child), 3)
        self.child.setParent(self.parent)
        self.assertEqual(sys.getrefcount(self.child), 3)

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testConstructor(self):
        # QObject(QObject) refcount changes
        child = QObject(self.parent)
        self.assertEqual(sys.getrefcount(child), 3)


class ParentCase(unittest.TestCase):
    '''Small collection of tests related to parent-child relationship'''

    def testSetParent(self):
        # QObject.setParent()
        parent = QObject()
        child = QObject()
        child.setParent(parent)

        self.assertEqual(parent, child.parent())

    def testParentConstructor(self):
        # QObject(parent)
        parent = QObject()
        child = QObject(parent)

        self.assertEqual(parent, child.parent())

        orig_repr = repr(child)
        del child
        self.assertEqual(orig_repr, repr(parent.children()[0]))

    def testChildren(self):
        # QObject.children()
        parent = QObject()
        children = [QObject(parent) for x in range(25)]

        self.assertEqual(parent.children(), children)

    def testFindChild(self):
        # QObject.findChild() with all QObject
        parent = QObject()
        children = [QObject(parent) for i in range(20)]

        for i, child in enumerate(children):
            child.setObjectName(f'object{i}')

        for i, child in enumerate(children):
            self.assertEqual(child, parent.findChild(QObject, f'object{i}'))


    def testFindChildOptions(self):
        parent = QObject()
        child  = QObject(parent)
        nested_child_name = 'nestedChild'
        nested_child = QObject(child)
        nested_child.setObjectName(nested_child_name)

        search_result = parent.findChild(QObject, nested_child_name)
        self.assertTrue(search_result)
        search_result = parent.findChild(QObject, nested_child_name,
                                         Qt.FindChildrenRecursively)
        self.assertTrue(search_result)
        search_result = parent.findChild(QObject, nested_child_name,
                                         Qt.FindDirectChildrenOnly)
        self.assertFalse(search_result)

        search_results = parent.findChildren(QObject, nested_child_name)
        self.assertEqual(len(search_results), 1)
        search_result = parent.findChildren(QObject, nested_child_name,
                                            Qt.FindChildrenRecursively)
        self.assertEqual(len(search_results), 1)
        search_results = parent.findChildren(QObject, nested_child_name,
                                             Qt.FindDirectChildrenOnly)
        self.assertEqual(len(search_results), 0)

    def testFindChildWithoutName(self):
        parent = QObject()
        children = [QObject(parent) for i in range(20)]

        for i, child in enumerate(children):
            child.setObjectName(f'object{i}')

        child = parent.findChild(QObject)
        self.assertTrue(isinstance(child, QObject))

    def testFindChildren(self):
        # QObject.findChildren() with all QObject
        parent = QObject()
        target_name = 'foo'
        children = [QTimer(parent) for i in range(20)]
        children.extend([QObject(parent) for i in range(20)])

        for i, child in enumerate(children):
            if i % 5 == 0:
                child.setObjectName(target_name)
            else:
                child.setObjectName(str(i))

        # Emulates findChildren with the intended outcome
        target_children = [x for x in children if x.objectName() == target_name]
        test_children = parent.findChildren(QObject, target_name)
        self.assertEqual(target_children, test_children)

        # test findChildren default value
        res = parent.findChildren(QTimer)
        self.assertEqual(len(res), 20)

        # test findChildren with a QRegularExpression
        res = parent.findChildren(QObject, QRegularExpression("^fo+"))
        self.assertEqual(res, test_children)

    def testParentEquality(self):
        # QObject.parent() == parent
        parent = QObject()
        child = QObject(parent)
        self.assertEqual(parent, child.parent())

    def testFindChildByType(self):
        parent = QObject()
        expected = TestObject2(parent)
        actual = parent.findChild(TestObject2)
        self.assertEqual(actual, expected)
        actual = parent.findChild(TestObject1)
        self.assertEqual(actual, expected)
        actual = parent.findChild(QTimer)
        self.assertEqual(actual, expected)

    def testFindChildrenByType(self):
        parent = QObject()
        expected = [TestObject2(parent)]
        actual = parent.findChildren(TestObject2)
        self.assertEqual(actual, expected)
        actual = parent.findChildren(TestObject1)
        self.assertEqual(actual, expected)
        actual = parent.findChildren(QTimer)
        self.assertEqual(actual, expected)


class TestParentOwnership(unittest.TestCase):
    '''Test case for Parent/Child object ownership'''

    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testParentDestructor(self):
        parent = QObject()
        self.assertEqual(sys.getrefcount(parent), 2)

        child = QObject(parent)
        self.assertEqual(sys.getrefcount(child), 3)
        self.assertEqual(sys.getrefcount(parent), 2)

        del parent
        self.assertEqual(sys.getrefcount(child), 2)

        # this will fail because parent deleted child cpp object
        self.assertRaises(RuntimeError, lambda: child.objectName())

    # test parent with multiples children
    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testMultipleChildren(self):
        o = QObject()
        self.assertEqual(sys.getrefcount(o), 2)

        c = QObject(o)
        self.assertEqual(sys.getrefcount(c), 3)
        self.assertEqual(sys.getrefcount(o), 2)

        c2 = QObject(o)
        self.assertEqual(sys.getrefcount(o), 2)
        self.assertEqual(sys.getrefcount(c), 3)
        self.assertEqual(sys.getrefcount(c2), 3)

        del o
        self.assertEqual(sys.getrefcount(c), 2)
        self.assertEqual(sys.getrefcount(c2), 2)

        # this will fail because parent deleted child cpp object
        self.assertRaises(RuntimeError, lambda: c.objectName())
        self.assertRaises(RuntimeError, lambda: c2.objectName())

    # test recursive parent
    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testRecursiveParent(self):
        o = QObject()
        self.assertEqual(sys.getrefcount(o), 2)

        c = QObject(o)
        self.assertEqual(sys.getrefcount(c), 3)
        self.assertEqual(sys.getrefcount(o), 2)

        c2 = QObject(c)
        self.assertEqual(sys.getrefcount(o), 2)
        self.assertEqual(sys.getrefcount(c), 3)
        self.assertEqual(sys.getrefcount(c2), 3)

        del o
        self.assertEqual(sys.getrefcount(c), 2)
        self.assertEqual(sys.getrefcount(c2), 2)

        # this will fail because parent deleted child cpp object
        self.assertRaises(RuntimeError, lambda: c.objectName())
        self.assertRaises(RuntimeError, lambda: c2.objectName())

    # test parent transfer
    @unittest.skipUnless(hasattr(sys, "getrefcount"), f"{sys.implementation.name} has no refcount")
    def testParentTransfer(self):
        o = QObject()
        self.assertEqual(sys.getrefcount(o), 2)

        c = QObject()
        self.assertEqual(sys.getrefcount(c), 2)

        c.setParent(o)
        self.assertEqual(sys.getrefcount(c), 3)

        c.setParent(None)
        self.assertEqual(sys.getrefcount(c), 2)

        del c
        del o


class ExtQObject(QObject):
    def __init__(self):
        super().__init__()


class ReparentingTest(unittest.TestCase):
    '''Test cases for reparenting'''

    def testParentedQObjectIdentity(self):
        object_list = []
        parent = QObject()
        for i in range(3):
            obj = QObject()
            object_list.append(obj)
            obj.setParent(parent)
        for child in parent.children():
            self.assertTrue(child in object_list)

    def testParentedExtQObjectType(self):
        object_list = []
        parent = QObject()
        for i in range(3):
            obj = ExtQObject()
            object_list.append(obj)
            obj.setParent(parent)
        for orig, child in zip(object_list, parent.children()):
            self.assertEqual(type(orig), type(child))

    def testReparentedQObjectIdentity(self):
        object_list = []
        old_parent = QObject()
        new_parent = QObject()
        for i in range(3):
            obj = QObject()
            object_list.append(obj)
            obj.setParent(old_parent)
        for obj in object_list:
            obj.setParent(new_parent)
        for child in new_parent.children():
            self.assertTrue(child in object_list)

    def testReparentedExtQObjectType(self):
        object_list = []
        old_parent = QObject()
        new_parent = QObject()
        for i in range(3):
            obj = ExtQObject()
            object_list.append(obj)
            obj.setParent(old_parent)
        for obj in object_list:
            obj.setParent(new_parent)
        for orig, child in zip(object_list, new_parent.children()):
            self.assertEqual(type(orig), type(child))


if __name__ == '__main__':
    unittest.main()
