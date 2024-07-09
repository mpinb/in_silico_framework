current_testlevel = 'all'


def testlevel(flag):
    '''decorator for test functions using to define testlevels.
    This allows to run timeconsuming tests only if necessary.
     
    Recommended usage:
    testlevel 0: very quick
    testlevel 1: takes a while
    testlevel 2: heavy computations'''

    if not isinstance(flag, int) or flag == 'all':
        raise ValueError("")

    def deco(f):

        def wrapper(self, *args, **kwargs):
            if flag == 'all':
                f(self, *args, **kwargs)
            elif current_testlevel == 'all' or current_testlevel >= flag:
                f(self, *args, **kwargs)
            else:
                self.skipTest(
                    "this test has testlevel %s. Current testlevel is %s" %
                    (str(flag), str(current_testlevel)))

        return wrapper

    return deco