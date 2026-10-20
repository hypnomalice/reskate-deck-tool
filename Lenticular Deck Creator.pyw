import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--install-update':
        try:
            from updates import apply_update
            apply_update(sys.argv[2])
        except Exception as exc:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(exc),'Update could not be installed',16)
    elif len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from build_check import check
        check(sys.argv[2])
    else:
        if len(sys.argv)==3 and sys.argv[1]=='--cleanup-update':
            import threading
            from updates import cleanup_update
            threading.Thread(target=cleanup_update,args=(sys.argv[2],),daemon=True).start()
        from qt_ui import main
        main()
