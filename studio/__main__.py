import sys

if __name__ == '__main__':
    if len(sys.argv) > 1:
        from studio import cli
        cli.main()
    else:
        # only import main on demand to avoid accessing the config
        # file at the wrong time
        from studio import main
        main.main()
