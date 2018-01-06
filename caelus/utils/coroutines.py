# -*- coding: utf-8 -*-

"""\
Coroutines

Some code snippets inspired by http://www.dabeaz.com/coroutines/
"""

import re
import functools
import six

def coroutine(func):
    """Prime a coroutine for send commands

    Args:
        func (coroutine): A consumer that is to be automatically initialized
    """
    @functools.wraps(func)
    def corut(*args, **kwargs):
        fn = func(*args, **kwargs)
        six.next(fn)
        return fn
    return corut

@coroutine
def grep(pattern, targets, send_close=True, flags=0):
    """A unix grep-like utility.

    If the line matches the "pattern" provided, then forward the re.match
    object to the targets registered to this utility.

    Args:
        pattern (regex): A ``re``-compatible regular expression
        targets (list): A list of consumers for the matching lines
        send_close (bool): Clean up consumer targets upon exit

        flags (int): Regular expression flags for compiling pattern, e.g., case
                     insensitive etc.

    """
    pat = re.compile(pattern, flags=flags)
    try:
        while True:
            line = (yield)
            mat = pat.match(line)
            if mat:
                for tgt in targets:
                    tgt.send(mat)
    except GeneratorExit:
        if send_close:
            for tgt in targets:
                tgt.close()
