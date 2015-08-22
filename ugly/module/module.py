import contextlib
import imp
import sys
import inspect

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
    scope = scope if scope is not None else {}
    module = imp.new_module(name)

    exec code in scope

    for v in scope.values():
        if is_adoptable(v):
            adopt(module, v)

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
    yield create_module(name, code, scope)
    del sys.modules[name]

def adopt(module, entity):
    """
    When a module "adopts" a class or a function, the ``__module__`` attribute
    of the given class or function is set to the name of the module. For
    example, if we have a class as the one below::

    >>> class Example(object):
    ...     def method(self):
    ...         pass

    Then it will have its ``__module__`` values set to the name of the modul ebelow

    >>> with installed_module('example') as m:
    ...     adopt(m, Example)
    ...     Example.__module__
    ...     Example.method.__module__
    'example'
    'example'
    """
    if inspect.isclass(entity):
        entity.__module__ = module.__name__
        attrs = ( getattr(entity, n) for n in dir(entity) )
        methods = ( a for a in attrs if inspect.ismethod(a) )
        for m in methods:
            adopt(module, m.im_func)
    elif inspect.isfunction(entity):
        entity.__module__ = module.__name__

def is_adoptable(obj):
    """
    Checks whether an object is adoptable. Adoptable objects are basically
    classes and functions::

    >>> class Example(object): pass
    >>> def f(a): pass
    >>> is_adoptable(Example)
    True
    >>> is_adoptable(f)
    True
    >>> is_adoptable(Example())
    False
    """
    return inspect.isclass(obj) or inspect.isfunction(obj)