import unittest

from ugly.finder import TestFinder

class TestTestFinder(unittest.TestCase):

    def test_is_test_suite(self):
        """
        The ``TestFinder`` class should be a test suite.
        """
        finder = TestFinder()

        self.assertTrue(isinstance(finder, unittest.TestSuite))

    def test_find_test_case_classes(self):
        """
        The ``TestFinder`` test suite should find test cases classes from the
        given modules.
        """
        class TestCase1(unittest.TestCase):
            def test_pass(self):
                pass
            def test_fail(self):
                self.fail()

        class TestCase2(unittest.TestCase):
            def test_pass(self):
                pass
            def test_error(self):
                raise Exception()

        with installed_module('m1', scope={'TestCase1': TestCase1}) as m1, \
                installed_module('m2', scope={'TestCase2': TestCase2}) as m2:
            result = unittest.TestResult()
            finder = TestFinder(m1, m2)
            finder.run(result)

            self.assertEquals(4, result.testsRun)
            self.assertEquals(1, len(result.failures))
            self.assertEquals(1, len(result.errors))

import contextlib

def create_module(name, code='', scope=None):
    """
    This function creates a module and adds it to the available ones::

    >>> m = create_module('my_module')
    >>> import my_module
    >>> my_module == m
    True

    You can give the code of the module to it::

    >>> m = create_module('with_code', code='x = 3')
    >>> import with_code
    >>> with_code.x
    3

    It also can receive a dictionary representing a previously set up scope
    (i.e. containing values that will be set in the module)::

    >>> m = create_module('with_scope', scope={'y': 32})
    >>> import with_scope
    >>> with_scope.y
    32

    It is possible to give both arguments as well and the code will work over
    the scope::

    >>> m = create_module('intricate', code='z = z+1', scope={'z': 4})
    >>> import intricate
    >>> intricate.z
    5
    """
    import imp
    import sys
    import inspect

    scope = scope if scope is not None else {}
    module = imp.new_module(name)

    exec(code, scope)

    module_objs = [
        obj for n, obj in scope.items()
         if (
            not n.startswith('__') and hasattr(obj, '__module__') and
            (name not in locals()) and (name not in globals())
        )
    ]

    for obj in module_objs:
        obj.__module__ = name

    module.__dict__.update(scope)
    sys.modules[name] = module

    return module

@contextlib.contextmanager
def installed_module(name, code='', scope=None):
    """
    This is a context manager to have a module created during a context::

    >>> with installed_module('a', code='x=3', scope={'y': 4}) as m:
    ...     import a
    ...     m == a
    ...     a.x
    ...     a.y
    True
    3
    4

    On the context exit the module will be removed from ``sys.modules``::

    >>> import a
    Traceback (most recent call last):
      ...
    ImportError: No module named a
    """
    import sys

    yield create_module(name, code, scope)
    del sys.modules[name]
