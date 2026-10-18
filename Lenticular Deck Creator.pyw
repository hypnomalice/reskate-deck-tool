import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from build_check import check
        check(sys.argv[2])
    else:
        from studio_ui import main
        main()