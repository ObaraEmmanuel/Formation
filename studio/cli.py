import argparse
import sys
import appdirs
import logging
import shutil
import os

from hoverset.util.execution import elevate
from hoverset.platform import platform_is, WINDOWS

import studio
from studio.preferences import Preferences

dirs = appdirs.AppDirs(appname="formation", appauthor="hoverset")
logger = logging.getLogger('formation-cli')
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s >> %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_parser():

    parser = argparse.ArgumentParser(
        prog="formation-cli",
        description="Command line tools for formation studio"
    )

    parser.add_argument(
        "-r",
        "--remove",
        metavar="FILES",
        default=None,
        help="""
            Removes and cleans internal app files. Can be set to
            config, cache or all.
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        action="store",
        nargs="+",
        metavar=("KEY", "VALUES"),
        help="""
            Get or set studio configuration values.
        """,
    )

    parser.add_argument(
        "-u",
        "--upgrade",
        action="store_true",
        help="""
            Upgrade formation studio to latest version
        """,
    )

    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + studio.__version__
    )

    return parser


def _clear_config():
    if not os.path.exists(dirs.user_config_dir):
        sys.exit(0)
    try:
        Preferences.acquire()
    except Preferences.ConfigFileInUseError:
        logger.error(
            "Config file currently in use. Close any open formation studio "
            "windows to continue."
        )
        sys.exit(1)
    except:
        pass
    try:
        shutil.rmtree(dirs.user_config_dir)
    except:
        logger.error("Could not delete config files")


def _clear_cache():
    if not os.path.exists(dirs.user_cache_dir):
        sys.exit(0)
    try:
        shutil.rmtree(dirs.user_cache_dir)
    except:
        logger.error("Could not delete cache files")


def _parse(value):
    # try to convert to numerical type if possible
    if value.isdigit():
        value = int(value)
    else:
        try:
            value = float(value)
        except:
            pass
    return value


def remove(args):
    arg = args.remove
    if arg == 'config':
        _clear_config()
        logger.info("Removed config files")
    elif arg == 'cache':
        _clear_cache()
        logger.info("Removed cache files")
    elif arg == 'all':
        _clear_cache()
        _clear_config()
        logger.info("Removed config and cache files")
    else:
        logger.error("Unknown argument %s", arg)
        sys.exit(1)


def neat_print(value):
    if isinstance(value, list):
        for i in value:
            print(i)
    else:
        print(value)


def handle_config(args):
    try:
        pref = Preferences.acquire()
    except Preferences.ConfigFileInUseError:
        logger.error(
            "Config file currently in use. Close any open formation studio "
            "windows to continue."
        )
        sys.exit(1)
    except Exception:
        logger.error("Unable to open config files")
        sys.exit(1)

    param = args.config
    key = param[0].replace(".", "::")
    if pref.exists(key):
        if len(param) == 1:
            neat_print(pref.get(key))
        elif len(param) == 2:
            pref.set(key, _parse(param[1]))
        else:
            pref.set(key, [_parse(v) for v in param[1:]])
        sys.exit(0)
    logger.error("Key %s not found", param[0])
    sys.exit(1)


def upgrade(args):
    # elevate process to run in admin mode
    command = f"\"{sys.executable}\" -m pip install --upgrade formation-studio"
    if platform_is(WINDOWS):
        # run command directly in elevated mode
        elevate(command)
    else:
        elevate()
        sys.exit(os.system(command))


def cli(args):
    parser = get_parser()
    args = parser.parse_args(args)

    if args.upgrade:
        upgrade(args)

    if args.remove is not None:
        remove(args)

    if args.config:
        handle_config(args)


def main():
    cli(sys.argv[1:])


if __name__ == "__main__":
    main()
