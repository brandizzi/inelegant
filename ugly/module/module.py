# coding: utf-8
import contextlib
import imp
import sys
import inspect
import textwrap
import importlib

def create_module(name, code='', scope=None, defs=()):
    """
    This function creates a module and adds it to the available ones::

    >>> m = create_module('my_module')
    >>> import my_module
    >>> my_module == m
    True

    Executing code
    --------------

    You can give the code of the module to it::

    >>> m = create_module('with_code', code='x = 3')
    >>> import with_code
    >>> with_code.x
    3

    The block of code can be indented (very much like doctests)::

    >>> m = create_module('with_code', code='''
    ...                                         x = 3
    ...                                         y = x+3
    ... ''')
    >>> import with_code
    >>> with_code.x
    3
    >>> with_code.y
    6

    Defining classes and functions
    ------------------------------

    Most of the time, one wants to define functions and classes inside a module,
    but putting them into a block of code can be cumbersome. One can, then,
    define them externally and pass them as the ``defs`` argument::

    >>> def function():
    ...     pass
    >>> class Class(object):
    ...     pass
    >>> m = create_module('m', defs=[Class, function])
    >>> m.Class
    <class 'm.Class'>
    >>> m.function # doctest: +ELLIPSIS
    <function function at ...>

    Setting a scope
    ---------------

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
    code = dedent(code)

    module = imp.new_module(name)
    adopt(module, *defs)
    sys.modules[name] = module

    module.__dict__.update(scope)

    for d in defs:
        module.__dict__[d.__name__] = d

    exec code in module.__dict__

    return module

@contextlib.contextmanager
def installed_module(name, code='', defs=(), scope=None):
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
    yield create_module(name, code=code, defs=defs, scope=scope)
    del sys.modules[name]

def adopt(module, *entities):
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

    This function can adopt many values at once as well::

    >>> def function():
    ...     pass
    >>> with installed_module('example') as m:
    ...     adopt(m, Example, function)
    ...     Example.__module__
    ...     function.__module__
    'example'
    'example'
    """
    unadoptable = [e for e in entities if not is_adoptable(e)]
    if unadoptable:
        raise AdoptException(*unadoptable)

    for entity in entities:
        entity = get_adoptable_value(entity)

        if inspect.isclass(entity):
            for a in get_adoptable_attrs(entity):
                adopt(module, a)

        entity.__module__ = module.__name__

def get_adoptable_value(obj):
    """
    Methods by themselves are not adoptable, but their functions are. This
    function will check whether an object is a method. If it is not, it will
    return the object itself::

    >>> class Class(object):
    ...     def m(self):
    ...         pass
    >>> get_adoptable_value(Class)
    <class 'ugly.module.module.Class'>
    >>> def f():
    ...     pass
    >>> get_adoptable_value(f) # doctest: +ELLIPSIS
    <function f at ...>

    If it is a method, however, it will return the function "enveloped" by it::

    >>> get_adoptable_value(Class.m) # doctest: +ELLIPSIS
    <function m at ...>
    """
    if inspect.ismethod(obj):
        return obj.im_func
    else:
        return obj

def get_adoptable_attrs(obj):
    """
    Get all attributes from the object which can be adopted::

    >>> class Example(object):
    ...     def method(self):
    ...         pass
    ...     class Inner(object):
    ...         pass
    ...     value = 3
    ...     builtin = dict
    >>> adoptable = list(get_adoptable_attrs(Example))
    >>> len(adoptable)
    2
    >>> Example.method in adoptable
    True
    >>> Example.Inner in adoptable
    True
    >>> Example.builtin in adoptable
    False
    >>> Example.value in adoptable
    False
    """
    attrs = ( getattr(obj, n) for n in dir(obj) )
    return (
        a
            for a in attrs
            if is_adoptable(a) and a.__module__ == obj.__module__
    )

def is_adoptable(obj):
    """
    Checks whether an object is adoptable - i.e., whether such an object can
    have its ``__module__`` attribute set.

    To be adoptable, an object should have a ``__module__`` attribute. In
    general, functions and classes satisfies these criteria::

    >>> class Example(object): pass
    >>> def f(a): pass
    >>> is_adoptable(Example)
    True
    >>> is_adoptable(f)
    True
    >>> is_adoptable(3)
    False

    Any object with these properites, however, would be adoptable::

    >>> e = Example()
    >>> e.__module__ = ''
    >>> is_adoptable(e)
    True

    Some classes and functions have read-only ``__module__`` attributes. Those
    are not adoptable::

    >>> is_adoptable(dict)
    False
    """
    obj = get_adoptable_value(obj)

    conditions = [
        hasattr(obj, '__module__'),
        is_module_rewritable(obj)
    ]

    return all(conditions)

def is_module_rewritable(obj):
    """
    Checks whether the ``__module__`` attribute of the object is rewritable::

    >>> def f():
    ...     pass
    >>> is_module_rewritable(f)
    True
    >>> is_module_rewritable(dict)
    False
    """
    try:
        obj.__module__ = obj.__module__
        return True
    except:
        return False

def is_builtin(obj):
    """
    Checks whether an object is built-in - either is a built-in function or
    belongs to the ``builtin`` module::

    >>> class Example(object): pass
    >>> is_builtin(Example)
    False
    >>> is_builtin(dict)
    True
    """
    return inspect.isbuiltin(obj) or obj.__module__ == '__builtin__'

class AdoptException(ValueError):
    """
    Exception raised when trying to make a module to adopt an unadoptable
    object, such as one that is not a function or object...

    ::

    >>> with installed_module('m') as m:
    ...     adopt(m, 3)
    Traceback (most recent call last):
        ...
    AdoptException: 3 has no __module__ attribute.

    ...or a built-in function::

    >>> with installed_module('m') as m:
    ...     adopt(m, dict)
    Traceback (most recent call last):
        ...
    AdoptException: <type 'dict'> __module__ attribute is ready-only.

    It can also receive more than one value::

    >>> with installed_module('m') as m:
    ...     adopt(m, dict, 3)
    Traceback (most recent call last):
        ...
    AdoptException: <type 'dict'> __module__ attribute is ready-only.
        3 has no __module__ attribute.
    """

    def __init__(self, *objs):
        messages = []
        for obj in objs:
            if not hasattr(obj, '__module__'):
                messages.append(
                    "{0} has no __module__ attribute.".format(repr(obj))
                )
            elif not is_module_rewritable(obj):
                messages.append(
                    "{0} __module__ attribute is ready-only.".format(repr(obj))
                )

        if messages:
            Exception.__init__(self, "\n    ".join(messages))
        else:
            Exception.__init__(self)


def get_caller_module(index=1):
    """
    ``get_caller_module()`` returns the module from where a specific frame from
    the frame stack was called.

    A throughout explanation
    ------------------------

    Let's suppose it is called inside a function defined in a module ``a`` that
    is called by a function defined in a module ``b``, which is called by a
    function defined in a module ``c``:

    - if it ``get_caller_module()`` module is called with the index 0, it will
    return the ``a`` module;
    - if it is called with index 1, it will return the ``b`` module;
    - and if its index is 2, it will return the ``c`` module.

    Something like this:

    2 - c
    1   └ b
    0     └ a
            └ get_caller_module()

    Here is a working example::

    >>> from ugly.module import installed_module
    >>> scope_a = {'get_caller_module': get_caller_module}
    >>> code_a = '''
    ...     def f_a():
    ...         print get_caller_module(0)
    ...         print get_caller_module(1)
    ...         print get_caller_module(2)
    ...     '''
    >>> with installed_module('a', code=code_a, scope=scope_a):
    ...     code_b = '''
    ...         import a
    ...         def f_b():
    ...             a.f_a()
    ...     '''
    ...     with installed_module('b', code=code_b):
    ...         code_c = '''
    ...             import b
    ...             def f_c():
    ...                 b.f_b()
    ...         '''
    ...         with installed_module('c', code=code_c) as c:
    ...             c.f_c() # doctest: +ELLIPSIS
    <module 'a' ...>
    <module 'b' ...>
    <module 'c' ...>

    The default index
    -----------------

    The index, however, is optional: ``get_caller_module()`` by default uses the
    index 1.

    It may be counterintuitive at first - why not zero?. But it is a more useful
    default. The function will rarely be called to discover in which module it
    is being called because _it is already there_. Most of the time one will
    want to discover where _the function which called ``get_caller_module()``
    was called.

    For example, we could have the following function::

    >>> def print_current_module():
    ...     print get_caller_module()

    Were the default index 0, it would print the module where
    ``get_current_module()`` was defined. However, we want the module where it
    was _called_ - and this is a level higher::

    >>> scope = {'print_current_module': print_current_module}
    >>> with installed_module('m', code='print_current_module()', scope=scope):
    ...     pass # doctest: +ELLIPSIS
    <module 'm' ...>
    """
    frame = sys._getframe(index+1)

    return importlib.import_module(frame.f_globals['__name__'])

def dedent(code):
    """
    Remove any consistent indentation found in a string. For example, consider
    the block below::

    >>> a = '''
    ...         for i in range(10):
    ...             print i
    ... '''
    >>> a
    '\\n        for i in range(10):\\n            print i\\n'

    When dendented, it will look like this::

    >>> dedent(a)
    'for i in range(10):\\n    print i\\n'
    """
    if isinstance(code, basestring) and code.startswith('\n'):
        code = code.replace('\n', '', 1)

    return textwrap.dedent(code)
