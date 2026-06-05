#!/usr/bin/env python3
import os, sys
print('cwd:', os.getcwd())
print('path:', sys.path[:3])
try:
    import main
    print('imported main successfully')
except Exception as e:
    print('import error:', type(e).__name__, str(e))
    import traceback
    traceback.print_exc()
