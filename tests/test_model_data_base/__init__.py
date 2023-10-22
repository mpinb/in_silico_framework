# import unittest
# import sys
# import pdb
# import functools
# import traceback
#
# #######################################
# #monkypatches for unittest
# #######################################
#
#
# class Empty():
#     '''Empty class for structuring data'''
#     pass
# unittest.monkypatches = Empty()
#
#
# def debug_on(*exceptions):
#     '''automaticaly starts debugger if error in unittest occurs.
#     Doesn't seem to work. Not used.
#     '''
#     if not exceptions:
#         exceptions = (AssertionError, )
#     def decorator(f):
#         #@functools.wraps(f)
#         def wrapper(*args, **kwargs):
#             try:
#                 return f(*args, **kwargs)
#             except exceptions:
#                 info = sys.exc_info()
#                 traceback.print_exception(*info)
#                 pdb.post_mortem(info[2])
#         return wrapper
#     return decorator
# unittest.monkypatches.debug_on = debug_on
#
#
# def run_if_testlevel(flag):
#     '''decorator for test functions using to define testlevels.
#     This allows to run timeconsuming tests only if necessary.
#
#     Recommended usage:
#     testlevel 0: very quick
#     testlevel 1: takes a while
#     testlevel 2: heavy computations'''
#
#     if not isinstance(flag, int) or flag == 'all':
#         raise ValueError("")
#     def deco(f):
#         def wrapper(self, *args, **kwargs):
#             #print(unittest.monkypatches.testlevel)
#             if flag == 'all':
#                 f(self, *args, **kwargs)
#             elif unittest.monkypatches.testlevel >= flag:
#                 f(self, *args, **kwargs)
#             else:
#                 self.skipTest("this test has testlevel %s. Current testlevel is %s" % (str(flag), str(unittest.monkypatches.testlevel)))
#         return wrapper
#     return deco
# unittest.monkypatches.run_if_testlevel = run_if_testlevel
# unittest.monkypatches.testlevel = 'all'