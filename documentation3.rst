
The ``decorator`` module
=============================================================

:Author: Michele Simionato
:E-mail: michele.simionato@gmail.com
:Version: 3.4.2 (2015-03-17)
:Requires: Python 2.4+
:Download page: http://pypi.python.org/pypi/decorator/3.4.2
:Installation: ``pip install decorator``
:License: BSD license

.. contents::

Introduction
------------------------------------------------

Python decorators are an interesting example of why syntactic sugar
matters. In principle, their introduction in Python 2.4 changed
nothing, since they do not provide any new functionality which was not
already present in the language. In practice, their introduction has
significantly changed the way we structure our programs in Python. I
believe the change is for the best, and that decorators are a great
idea since:

* decorators help reducing boilerplate code;
* decorators help separation of concerns;
* decorators enhance readability and maintenability;
* decorators are explicit.

Still, as of now, writing custom decorators correctly requires
some experience and it is not as easy as it could be. For instance,
typical implementations of decorators involve nested functions, and
we all know that flat is better than nested.

The aim of the ``decorator`` module it to simplify the usage of
decorators for the average programmer, and to popularize decorators by
showing various non-trivial examples. Of course, as all techniques,
decorators can be abused (I have seen that) and you should not try to
solve every problem with a decorator, just because you can.

You may find the source code for all the examples
discussed here in the ``documentation.py`` file, which contains
this documentation in the form of doctests.

Definitions
------------------------------------

Technically speaking, any Python object which can be called with one argument
can be used as  a decorator. However, this definition is somewhat too large
to be really useful. It is more convenient to split the generic class of
decorators in two subclasses:

+ *signature-preserving* decorators, i.e. callable objects taking a
  function as input and returning a function *with the same
  signature* as output;

+ *signature-changing* decorators, i.e. decorators that change
  the signature of their input function, or decorators returning
  non-callable objects.

Signature-changing decorators have their use: for instance the
builtin classes ``staticmethod`` and ``classmethod`` are in this
group, since they take functions and return descriptor objects which
are not functions, nor callables.

However, signature-preserving decorators are more common and easier to
reason about; in particular signature-preserving decorators can be
composed together whereas other decorators in general cannot.

Writing signature-preserving decorators from scratch is not that
obvious, especially if one wants to define proper decorators that
can accept functions with any signature. A simple example will clarify
the issue.

Statement of the problem
------------------------------

A very common use case for decorators is the memoization of functions.
A ``memoize`` decorator works by caching
the result of the function call in a dictionary, so that the next time
the function is called with the same input parameters the result is retrieved
from the cache and not recomputed. There are many implementations of
``memoize`` in http://www.python.org/moin/PythonDecoratorLibrary,
but they do not preserve the signature.
A simple implementation could be the following (notice
that in general it is impossible to memoize correctly something
that depends on non-hashable arguments):

.. code-block:: python

 def memoize_uw(func):
     func.cache = {}
 
     def memoize(*args, **kw):
         if kw:  # frozenset is used to ensure hashability
             key = args, frozenset(kw.iteritems())
         else:
             key = args
         cache = func.cache
         if key in cache:
             return cache[key]
         else:
             cache[key] = result = func(*args, **kw)
             return result
     return functools.update_wrapper(memoize, func)


Here we used the functools.update_wrapper_ utility, which has
been added in Python 2.5 expressly to simplify the definition of decorators
(in older versions of Python you need to copy the function attributes
``__name__``, ``__doc__``, ``__module__`` and ``__dict__``
from the original function to the decorated function by hand).

.. _functools.update_wrapper: https://docs.python.org/3/library/functools.html#functools.update_wrapper

The implementation above works in the sense that the decorator
can accept functions with generic signatures; unfortunately this
implementation does *not* define a signature-preserving decorator, since in
general ``memoize_uw`` returns a function with a
*different signature* from the original function.

Consider for instance the following case:

.. code-block:: python

 >>> @memoize_uw
 ... def f1(x):
 ...     time.sleep(1) # simulate some long computation
 ...     return x

Here the original function takes a single argument named ``x``,
but the decorated function takes any number of arguments and
keyword arguments:

.. code-block:: python

 >>> from inspect import getargspec
 >>> print(getargspec(f1))
 ArgSpec(args=[], varargs='args', keywords='kw', defaults=None)

This means that introspection tools such as pydoc will give
wrong informations about the signature of ``f1``. This is pretty bad:
pydoc will tell you that the function accepts a generic signature
``*args``, ``**kw``, but when you try to call the function with more than an
argument, you will get an error:

.. code-block:: python

 >>> f1(0, 1) 
 Traceback (most recent call last):
    ...
 TypeError: f1() takes exactly 1 positional argument (2 given)

The solution
-----------------------------------------

The solution is to provide a generic factory of generators, which
hides the complexity of making signature-preserving decorators
from the application programmer. The ``decorator`` function in
the ``decorator`` module is such a factory:

.. code-block:: python

 >>> from decorator import decorator

``decorator`` takes two arguments, a caller function describing the
functionality of the decorator and a function to be decorated; it
returns the decorated function. The caller function must have
signature ``(f, *args, **kw)`` and it must call the original function ``f``
with arguments ``args`` and ``kw``, implementing the wanted capability,
i.e. memoization in this case:

.. code-block:: python

 def _memoize(func, *args, **kw):
     if kw:  # frozenset is used to ensure hashability
         key = args, frozenset(kw.iteritems())
     else:
         key = args
     cache = func.cache  # attributed added by memoize
     if key in cache:
         return cache[key]
     else:
         cache[key] = result = func(*args, **kw)
         return result


At this point you can define your decorator as follows:

.. code-block:: python

 def memoize(f):
     f.cache = {}
     return decorator(_memoize, f)


The difference with respect to the ``memoize_uw`` approach, which is based
on nested functions, is that the decorator module forces you to lift
the inner function at the outer level (*flat is better than nested*).
Moreover, you are forced to pass explicitly the function you want to
decorate to the caller function.

Here is a test of usage:

.. code-block:: python

 >>> @memoize
 ... def heavy_computation():
 ...     time.sleep(2)
 ...     return "done"

 >>> print(heavy_computation()) # the first time it will take 2 seconds
 done

 >>> print(heavy_computation()) # the second time it will be instantaneous
 done

The signature of ``heavy_computation`` is the one you would expect:

.. code-block:: python

 >>> print(getargspec(heavy_computation))
 ArgSpec(args=[], varargs=None, keywords=None, defaults=None)

A ``trace`` decorator
------------------------------------------------------

As an additional example, here is how you can define a trivial
``trace`` decorator, which prints a message everytime the traced
function is called:

.. code-block:: python

 def _trace(f, *args, **kw):
     kwstr = ', '.join('%r: %r' % (k, kw[k]) for k in sorted(kw))
     print("calling %s with args %s, {%s}" % (f.__name__, args, kwstr))
     return f(*args, **kw)


.. code-block:: python

 def trace(f):
     return decorator(_trace, f)


Here is an example of usage:

.. code-block:: python
 
 >>> @trace
 ... def f1(x):
 ...     pass

It is immediate to verify that ``f1`` works

.. code-block:: python

 >>> f1(0)
 calling f1 with args (0,), {}

and it that it has the correct signature:

.. code-block:: python

 >>> print(getargspec(f1))
 ArgSpec(args=['x'], varargs=None, keywords=None, defaults=None)

The same decorator works with functions of any signature:

.. code-block:: python

 >>> @trace
 ... def f(x, y=1, z=2, *args, **kw):
 ...     pass

 >>> f(0, 3)
 calling f with args (0, 3, 2), {}

 >>> print(getargspec(f))
 ArgSpec(args=['x', 'y', 'z'], varargs='args', keywords='kw', defaults=(1, 2))

Function annotations
---------------------------------------------

Python 3 introduced the concept of `function annotations`_,i.e. the ability
to annotate the signature of a function with additional information,
stored in a dictionary named ``__annotations__``. The decorator module,
starting from release 3.3, is able to understand and to preserve the
annotations. Here is an example:

.. code-block:: python

 >>> @trace
 ... def f(x: 'the first argument', y: 'default argument'=1, z=2,
 ...       *args: 'varargs', **kw: 'kwargs'):
 ...     pass
 
In order to introspect functions with annotations, one needs the
utility ``inspect.getfullargspec``, new in Python 3:

.. code-block:: python

 >>> from inspect import getfullargspec
 >>> argspec = getfullargspec(f)
 >>> argspec.args
 ['x', 'y', 'z']
 >>> argspec.varargs
 'args'
 >>> argspec.varkw
 'kw'
 >>> argspec.defaults
 (1, 2)
 >>> argspec.kwonlyargs
 []
 >>> argspec.kwonlydefaults

You can also check that the ``__annotations__`` dictionary is preserved:

.. code-block:: python

  >>> f.__annotations__ == f.__wrapped__.__annotations__
  True

Depending on the version of the decorator module, the two dictionaries can
be the same object or not: you cannot rely on object identity, but you can
rely on the content being the same.

``decorator`` is a decorator
---------------------------------------------

It may be annoying to write a caller function (like the ``_trace``
function above) and then a trivial wrapper
(``def trace(f): return decorator(_trace, f)``) every time. For this reason,
the ``decorator`` module provides an easy shortcut to convert
the caller function into a signature-preserving decorator:
you can just call ``decorator`` with a single argument.
In our example you can just write ``trace = decorator(_trace)``.
The ``decorator`` function can also be used as a signature-changing
decorator, just as ``classmethod`` and ``staticmethod``.
However, ``classmethod`` and ``staticmethod`` return generic
objects which are not callable, while ``decorator`` returns
signature-preserving decorators, i.e. functions of a single argument.
For instance, you can write directly

.. code-block:: python

 >>> @decorator
 ... def trace(f, *args, **kw):
 ...     kwstr = ', '.join('%r: %r' % (k, kw[k]) for k in sorted(kw))
 ...     print("calling %s with args %s, {%s}" % (f.__name__, args, kwstr))
 ...     return f(*args, **kw)

and now ``trace`` will be a decorator. Actually ``trace`` is a ``partial``
object which can be used as a decorator:

.. code-block:: python

 >>> trace 
 <function trace at 0x...>

Here is an example of usage:

.. code-block:: python

 >>> @trace
 ... def func(): pass

 >>> func()
 calling func with args (), {}

If you are using an old Python version (Python 2.4) the
``decorator`` module provides a poor man replacement for
``functools.partial``.

``blocking``
-------------------------------------------

Sometimes one has to deal with blocking resources, such as ``stdin``, and
sometimes it is best to have back a "busy" message than to block everything.
This behavior can be implemented with a suitable family of decorators,
where the parameter is the busy message:

.. code-block:: python

 def blocking(not_avail):
     def blocking(f, *args, **kw):
         if not hasattr(f, "thread"):  # no thread running
             def set_result():
                 f.result = f(*args, **kw)
             f.thread = threading.Thread(None, set_result)
             f.thread.start()
             return not_avail
         elif f.thread.isAlive():
             return not_avail
         else:  # the thread is ended, return the stored result
             del f.thread
             return f.result
     return decorator(blocking)

   
Functions decorated with ``blocking`` will return a busy message if
the resource is unavailable, and the intended result if the resource is
available. For instance:

.. code-block:: python

 >>> @blocking("Please wait ...")
 ... def read_data():
 ...     time.sleep(3) # simulate a blocking resource
 ...     return "some data"

 >>> print(read_data())  # data is not available yet
 Please wait ...

 >>> time.sleep(1)
 >>> print(read_data())  # data is not available yet
 Please wait ...

 >>> time.sleep(1)
 >>> print(read_data())  # data is not available yet
 Please wait ...

 >>> time.sleep(1.1)  # after 3.1 seconds, data is available
 >>> print(read_data())
 some data

``async``
--------------------------------------------

We have just seen an examples of a simple decorator factory,
implemented as a function returning a decorator.
For more complex situations, it is more
convenient to implement decorator factories as classes returning
callable objects that can be converted into decorators.

As an example, here will I show a decorator
which is able to convert a blocking function into an asynchronous
function. The function, when called,
is executed in a separate thread. Moreover, it is possible to set
three callbacks ``on_success``, ``on_failure`` and ``on_closing``,
to specify how to manage the function call (of course the code here
is just an example, it is not a recommended way of doing multi-threaded
programming). The implementation is the following:

.. code-block:: python

 def on_success(result):  # default implementation
     "Called on the result of the function"
     return result

.. code-block:: python

 def on_failure(exc_info):  # default implementation
     "Called if the function fails"
     pass

.. code-block:: python

 def on_closing():  # default implementation
     "Called at the end, both in case of success and failure"
     pass

.. code-block:: python

 class Async(object):
     """
     A decorator converting blocking functions into asynchronous
     functions, by using threads or processes. Examples:
 
     async_with_threads =  Async(threading.Thread)
     async_with_processes =  Async(multiprocessing.Process)
     """
 
     def __init__(self, threadfactory, on_success=on_success,
                  on_failure=on_failure, on_closing=on_closing):
         self.threadfactory = threadfactory
         self.on_success = on_success
         self.on_failure = on_failure
         self.on_closing = on_closing
 
     def __call__(self, func, *args, **kw):
         try:
             counter = func.counter
         except AttributeError:  # instantiate the counter at the first call
             counter = func.counter = itertools.count(1)
         name = '%s-%s' % (func.__name__, next(counter))
 
         def func_wrapper():
             try:
                 result = func(*args, **kw)
             except:
                 self.on_failure(sys.exc_info())
             else:
                 return self.on_success(result)
             finally:
                 self.on_closing()
         thread = self.threadfactory(None, func_wrapper, name)
         thread.start()
         return thread


The decorated function returns
the current execution thread, which can be stored and checked later, for
instance to verify that the thread ``.isAlive()``.

Here is an example of usage. Suppose one wants to write some data to
an external resource which can be accessed by a single user at once
(for instance a printer). Then the access to the writing function must
be locked. Here is a minimalistic example:

.. code-block:: python

 >>> async = decorator(Async(threading.Thread))

 >>> datalist = [] # for simplicity the written data are stored into a list.

 >>> @async
 ... def write(data):
 ...     # append data to the datalist by locking
 ...     with threading.Lock():
 ...         time.sleep(1) # emulate some long running operation
 ...         datalist.append(data)
 ...     # other operations not requiring a lock here

Each call to ``write`` will create a new writer thread, but there will
be no synchronization problems since ``write`` is locked.

.. code-block:: python

 >>> write("data1") 
 <Thread(write-1, started...)>
 
 >>> time.sleep(.1) # wait a bit, so we are sure data2 is written after data1
 
 >>> write("data2") 
 <Thread(write-2, started...)>
 
 >>> time.sleep(2) # wait for the writers to complete
 
 >>> print(datalist)
 ['data1', 'data2']

contextmanager
-------------------------------------

For a long time Python had in its standard library a ``contextmanager``
decorator, able to convert generator functions into
``_GeneratorContextManager`` factories. For instance if you write

.. code-block:: python

 >>> from contextlib import contextmanager
 >>> @contextmanager
 ... def before_after(before, after):
 ...     print(before)
 ...     yield
 ...     print(after)


then ``before_after`` is a factory function returning
``_GeneratorContextManager`` objects which can be used with
the ``with`` statement:

.. code-block:: python

 >>> ba = before_after('BEFORE', 'AFTER')
 >>> type(ba)
 <class 'contextlib._GeneratorContextManager'>
 >>> with ba:
 ...     print('hello')
 BEFORE
 hello
 AFTER

Basically, it is as if the content of the ``with`` block was executed
in the place of the ``yield`` expression in the generator function.
In Python 3.2 ``_GeneratorContextManager``
objects were enhanced with a ``__call__``
method, so that they can be used as decorators as in this example:

.. code-block:: python

 >>> @ba 
 ... def hello():
 ...     print('hello')
 ...
 >>> hello() 
 BEFORE
 hello
 AFTER

The ``ba`` decorator is basically inserting a ``with ba:``
block inside the function.
However there two issues: the first is that ``_GeneratorContextManager``
objects are callable only in Python 3.2, so the previous example will break
in older versions of Python; the second is that
``_GeneratorContextManager`` objects do not preserve the signature
of the decorated functions: the decorated ``hello`` function here will have
a generic signature ``hello(*args, **kwargs)`` but will break when
called with more than zero arguments. For such reasons the decorator
module, starting with release 3.4, offers a ``decorator.contextmanager``
decorator that solves both problems and works even in Python 2.5.
The usage is the same and factories decorated with ``decorator.contextmanager``
will returns instances of ``ContextManager``, a subclass of
``contextlib._GeneratorContextManager`` with a ``__call__`` method
acting as a signature-preserving decorator.

The ``FunctionMaker`` class
---------------------------------------------------------------

You may wonder about how the functionality of the ``decorator`` module
is implemented. The basic building block is
a ``FunctionMaker`` class which is able to generate on the fly
functions with a given name and signature from a function template
passed as a string. Generally speaking, you should not need to
resort to ``FunctionMaker`` when writing ordinary decorators, but
it is handy in some circumstances. You will see an example shortly, in
the implementation of a cool decorator utility (``decorator_apply``).

``FunctionMaker`` provides a ``.create`` classmethod which
takes as input the name, signature, and body of the function
we want to generate as well as the execution environment
were the function is generated by ``exec``. Here is an example:

.. code-block:: python

 >>> def f(*args, **kw): # a function with a generic signature
 ...     print(args, kw)

 >>> f1 = FunctionMaker.create('f1(a, b)', 'f(a, b)', dict(f=f))
 >>> f1(1,2)
 (1, 2) {}

It is important to notice that the function body is interpolated
before being executed, so be careful with the ``%`` sign!

``FunctionMaker.create`` also accepts keyword arguments and such
arguments are attached to the resulting function. This is useful
if you want to set some function attributes, for instance the
docstring ``__doc__``.

For debugging/introspection purposes it may be useful to see
the source code of the generated function; to do that, just
pass the flag ``addsource=True`` and a ``__source__`` attribute will
be added to the generated function:

.. code-block:: python

 >>> f1 = FunctionMaker.create(
 ...     'f1(a, b)', 'f(a, b)', dict(f=f), addsource=True)
 >>> print(f1.__source__)
 def f1(a, b):
     f(a, b)
 <BLANKLINE>

``FunctionMaker.create`` can take as first argument a string,
as in the examples before, or a function. This is the most common
usage, since typically you want to decorate a pre-existing
function. A framework author may want to use directly ``FunctionMaker.create``
instead of ``decorator``, since it gives you direct access to the body
of the generated function. For instance, suppose you want to instrument
the ``__init__`` methods of a set of classes, by preserving their
signature (such use case is not made up; this is done in SQAlchemy
and in other frameworks). When the first argument of ``FunctionMaker.create``
is a function, a ``FunctionMaker`` object is instantiated internally,
with attributes ``args``, ``varargs``,
``keywords`` and ``defaults`` which are the
the return values of the standard library function ``inspect.getargspec``.
For each argument in the ``args`` (which is a list of strings containing
the names of the mandatory arguments) an attribute ``arg0``, ``arg1``,
..., ``argN`` is also generated. Finally, there is a ``signature``
attribute, a string with the signature of the original function.

Notice that while I do not have plans
to change or remove the functionality provided in the
``FunctionMaker`` class, I do not guarantee that it will stay
unchanged forever. For instance, right now I am using the traditional
string interpolation syntax for function templates, but Python 2.6
and Python 3.0 provide a newer interpolation syntax and I may use
the new syntax in the future.
On the other hand, the functionality provided by
``decorator`` has been there from version 0.1 and it is guaranteed to
stay there forever.

Getting the source code
---------------------------------------------------

Internally ``FunctionMaker.create`` uses ``exec`` to generate the
decorated function. Therefore
``inspect.getsource`` will not work for decorated functions. That
means that the usual '??' trick in IPython will give you the (right on
the spot) message ``Dynamically generated function. No source code
available``.  In the past I have considered this acceptable, since
``inspect.getsource`` does not really work even with regular
decorators. In that case ``inspect.getsource`` gives you the wrapper
source code which is probably not what you want:

.. code-block:: python

 def identity_dec(func):
     def wrapper(*args, **kw):
         return func(*args, **kw)
     return wrapper


.. code-block:: python

 @identity_dec
 def example(): pass

 >>> print(inspect.getsource(example))
     def wrapper(*args, **kw):
         return func(*args, **kw)
 <BLANKLINE>

(see bug report 1764286_ for an explanation of what is happening).
Unfortunately the bug is still there, even in Python 2.7 and 3.1.
There is however a workaround. The decorator module adds an
attribute ``.__wrapped__`` to the decorated function, containing
a reference to the original function. The easy way to get
the source code is to call ``inspect.getsource`` on the
undecorated function:

.. code-block:: python

 >>> print(inspect.getsource(factorial.__wrapped__))
 @tail_recursive
 def factorial(n, acc=1):
     "The good old factorial"
     if n == 0:
         return acc
     return factorial(n-1, n*acc)
 <BLANKLINE>

.. _1764286: http://bugs.python.org/issue1764286

Dealing with third party decorators
-----------------------------------------------------------------

Sometimes you find on the net some cool decorator that you would
like to include in your code. However, more often than not the cool
decorator is not signature-preserving. Therefore you may want an easy way to
upgrade third party decorators to signature-preserving decorators without
having to rewrite them in terms of ``decorator``. You can use a
``FunctionMaker`` to implement that functionality as follows:

.. code-block:: python

 def decorator_apply(dec, func):
     """
     Decorate a function by preserving the signature even if dec
     is not a signature-preserving decorator.
     """
     return FunctionMaker.create(
         func, 'return decorated(%(signature)s)',
         dict(decorated=dec(func)), __wrapped__=func)


``decorator_apply`` sets the attribute ``.__wrapped__`` of the generated
function to the original function, so that you can get the right
source code.

Notice that I am not providing this functionality in the ``decorator``
module directly since I think it is best to rewrite the decorator rather
than adding an additional level of indirection. However, practicality
beats purity, so you can add ``decorator_apply`` to your toolbox and
use it if you need to.

In order to give an example of usage of ``decorator_apply``, I will show a
pretty slick decorator that converts a tail-recursive function in an iterative
function. I have shamelessly stolen the basic idea from Kay Schluehr's recipe
in the Python Cookbook,
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496691.

.. code-block:: python

 class TailRecursive(object):
     """
     tail_recursive decorator based on Kay Schluehr's recipe
     http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496691
     with improvements by me and George Sakkis.
     """
 
     def __init__(self, func):
         self.func = func
         self.firstcall = True
         self.CONTINUE = object()  # sentinel
 
     def __call__(self, *args, **kwd):
         CONTINUE = self.CONTINUE
         if self.firstcall:
             func = self.func
             self.firstcall = False
             try:
                 while True:
                     result = func(*args, **kwd)
                     if result is CONTINUE:  # update arguments
                         args, kwd = self.argskwd
                     else:  # last call
                         return result
             finally:
                 self.firstcall = True
         else:  # return the arguments of the tail call
             self.argskwd = args, kwd
             return CONTINUE


Here the decorator is implemented as a class returning callable
objects.

.. code-block:: python

 def tail_recursive(func):
     return decorator_apply(TailRecursive, func)


Here is how you apply the upgraded decorator to the good old factorial:

.. code-block:: python

 @tail_recursive
 def factorial(n, acc=1):
     "The good old factorial"
     if n == 0:
         return acc
     return factorial(n-1, n*acc)


.. code-block:: python

 >>> print(factorial(4))
 24

This decorator is pretty impressive, and should give you some food for
your mind ;) Notice that there is no recursion limit now, and you can
easily compute ``factorial(1001)`` or larger without filling the stack
frame. Notice also that the decorator will not work on functions which
are not tail recursive, such as the following

.. code-block:: python

 def fact(n):  # this is not tail-recursive
     if n == 0:
         return 1
     return n * fact(n-1)


(reminder: a function is tail recursive if it either returns a value without
making a recursive call, or returns directly the result of a recursive
call).

Caveats and limitations
-------------------------------------------

The first thing you should be aware of, it the fact that decorators
have a performance penalty.
The worse case is shown by the following example::

 $ cat performance.sh
 python3 -m timeit -s "
 from decorator import decorator

 @decorator
 def do_nothing(func, *args, **kw):
     return func(*args, **kw)

 @do_nothing
 def f():
     pass
 " "f()"

 python3 -m timeit -s "
 def f():
     pass
 " "f()"

On my MacBook, using the ``do_nothing`` decorator instead of the
plain function is more than three times slower::

 $ bash performance.sh
 1000000 loops, best of 3: 0.669 usec per loop
 1000000 loops, best of 3: 0.181 usec per loop

It should be noted that a real life function would probably do
something more useful than ``f`` here, and therefore in real life the
performance penalty could be completely negligible.  As always, the
only way to know if there is
a penalty in your specific use case is to measure it.

You should be aware that decorators will make your tracebacks
longer and more difficult to understand. Consider this example:

.. code-block:: python

 >>> @trace
 ... def f():
 ...     1/0

Calling ``f()`` will give you a ``ZeroDivisionError``, but since the
function is decorated the traceback will be longer:

.. code-block:: python

 >>> f() 
 Traceback (most recent call last):
   ...
      File "<string>", line 2, in f
      File "<doctest __main__[22]>", line 4, in trace
        return f(*args, **kw)
      File "<doctest __main__[51]>", line 3, in f
        1/0
 ZeroDivisionError: ...

You see here the inner call to the decorator ``trace``, which calls
``f(*args, **kw)``, and a reference to  ``File "<string>", line 2, in f``.
This latter reference is due to the fact that internally the decorator
module uses ``exec`` to generate the decorated function. Notice that
``exec`` is *not* responsibile for the performance penalty, since is the
called *only once* at function decoration time, and not every time
the decorated function is called.

At present, there is no clean way to avoid ``exec``. A clean solution
would require to change the CPython implementation of functions and
add an hook to make it possible to change their signature directly.
That could happen in future versions of Python (see PEP 362_) and
then the decorator module would become obsolete. However, at present,
even in Python 3.2 it is impossible to change the function signature
directly, therefore the ``decorator`` module is still useful.
Actually, this is one of the main reasons why I keep maintaining
the module and releasing new versions.

.. _362: http://www.python.org/dev/peps/pep-0362

In the present implementation, decorators generated by ``decorator``
can only be used on user-defined Python functions or methods, not on generic
callable objects, nor on built-in functions, due to limitations of the
``inspect`` module in the standard library.

There is a restriction on the names of the arguments: for instance,
if try to call an argument ``_call_`` or ``_func_``
you will get a ``NameError``:

.. code-block:: python

 >>> @trace
 ... def f(_func_): print(f)
 ... 
 Traceback (most recent call last):
   ...
 NameError: _func_ is overridden in
 def f(_func_):
     return _call_(_func_, _func_)

Finally, the implementation is such that the decorated function shares
the original function dictionary:

.. code-block:: python

 >>> def f(): pass # the original function
 >>> f.attr1 = "something" # setting an attribute
 >>> f.attr2 = "something else" # setting another attribute

 >>> traced_f = trace(f) # the decorated function

 >>> traced_f.attr1
 'something'
 >>> traced_f.attr2 = "something different" # setting attr
 >>> f.attr2 # the original attribute did not change
 'something else'

Compatibility notes
---------------------------------------------------------------

Version 3.4 fixes some bugs in the support of recent versions of
Python 3.  Version 3.3 was the first version of the ``decorator``
module to fully support Python 3, including `function
annotations`_. Version 3.2 was the first version to support Python 3
via the ``2to3`` conversion tool.  The hard work (for me) has been
converting the documentation and the doctests.  This has been possible
only after that docutils_ and pygments_ have been ported to Python 3.

Version 3 of the ``decorator`` module do not contain any backward
incompatible change, apart from the removal of the functions
``get_info`` and ``new_wrapper``, which have been deprecated for
years. ``get_info`` has been removed since it was little used and
since it had to be changed anyway to work with Python 3.0;
``new_wrapper`` has been removed since it was useless: its major use
case (converting signature changing decorators to signature preserving
decorators) has been subsumed by ``decorator_apply``, whereas the other use
case can be managed with the ``FunctionMaker``.

There are a few changes in the documentation: I removed the
``decorator_factory`` example, which was confusing some of my users,
and I removed the part about exotic signatures in the Python 3
documentation, since Python 3 does not support them.

Finally ``decorator`` cannot be used as a class decorator and the
`functionality introduced in version 2.3`_ has been removed. That
means that in order to define decorator factories with classes you
need to define the ``__call__`` method explicitly (no magic anymore).
All these changes should not cause any trouble, since they were
all rarely used features. Should you have any trouble, you can always
downgrade to the 2.3 version.

The examples shown here have been tested with Python 2.6. Python 2.4
is also supported - of course the examples requiring the ``with``
statement will not work there. Python 2.5 works fine, but if you
run the examples in the interactive interpreter
you will notice a few differences since
``getargspec`` returns an ``ArgSpec`` namedtuple instead of a regular
tuple. That means that running the file
``documentation.py`` under Python 2.5 will print a few errors, but
they are not serious.

.. _functionality introduced in version 2.3: http://www.phyast.pitt.edu/~micheles/python/documentation.html#class-decorators-and-decorator-factories
.. _function annotations: http://www.python.org/dev/peps/pep-3107/
.. _distribute: http://packages.python.org/distribute/
.. _docutils: http://docutils.sourceforge.net/
.. _pygments: http://pygments.org/

LICENCE
---------------------------------------------

Copyright (c) 2005-2015, Michele Simionato
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.
  Redistributions in bytecode form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in
  the documentation and/or other materials provided with the
  distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.

If you use this software and you are happy with it, consider sending me a
note, just to gratify my ego. On the other hand, if you use this software and
you are unhappy with it, send me a patch!
