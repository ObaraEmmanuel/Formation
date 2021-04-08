import sys
from subprocess import Popen


def main():
    # run in new detached process to circumvent several issues presented
    # by how setuptools handles entry_points preventing certain functionality
    # from working in formation studio
    Popen([sys.executable, "-m", "studio", *sys.argv[1:]], start_new_session=True)
