import sys
from formation.loader import AppBuilder

if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]

        app = AppBuilder(path=path)
        app.mainloop()
