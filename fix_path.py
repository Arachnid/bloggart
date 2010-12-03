import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# see issue772: http://code.google.com/p/googleappengine/issues/detail?id=772
ultimate_sys_path = None

def fix_sys_path():
    global ultimate_sys_path
    if ultimate_sys_path is None:
        ultimate_sys_path = list(sys.path)
    else:
        sys.path[:] = ultimate_sys_path
