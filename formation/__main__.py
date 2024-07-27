import sys
import os
from formation.loader import AppBuilder

if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]

        if len(sys.argv) > 2:
            working_dir = sys.argv[2]
            if os.path.exists(working_dir):
                os.chdir(working_dir)

        app = AppBuilder(path=path)
        app.mainloop()
