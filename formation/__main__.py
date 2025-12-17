import pathlib
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

        # Add custom widget paths to system paths
        # This is usually provided by the studio
        if len(sys.argv) > 3:
            custom_paths = sys.argv[3:]
            for c_path in custom_paths:
                c_path = pathlib.Path(c_path).resolve()
                if str(c_path.parent) not in sys.path:
                    sys.path.append(str(c_path.parent))

        app = AppBuilder(path=path)
        app.mainloop()
