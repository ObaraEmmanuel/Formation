from hoverset.platform import PLATFORM, WINDOWS
import threading
import time
import os

if PLATFORM == WINDOWS:
    import win32api
    import win32con
    import win32gui


# noinspection PyBroadException
class WindowsNotification:
    # Inspired by Jithu R Jacob windows10Toast library

    def __init__(self):
        self. _thread = None

    def _push(self, title, msg, icon_path, duration, threaded):
        if self._thread and threaded:
            self._thread.join()
        message_map = {win32con.WM_DESTROY: self.on_destroy}

        # register the window class
        self.wc = win32gui.WNDCLASS()
        self.hinst = self.wc.hInstance = win32api.GetModuleHandle(None)
        self.wc.lpszClassName = str("PythonTaskbar")  # Must be a string
        self.wc.lpfnWndProc = message_map
        try:
            self.classAtom = win32gui.RegisterClass(self.wc)
        except Exception:
            pass

        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(self.classAtom, "Taskbar", style,
                                          0, 0, win32con.CW_USEDEFAULT,
                                          win32con.CW_USEDEFAULT,
                                          0, 0, self.hinst, None)
        win32gui.UpdateWindow(self.hwnd)

        if icon_path is not None:
            icon_path = os.path.realpath(icon_path)
        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE

        try:
            hicon = win32gui.LoadImage(self.hinst, icon_path, win32gui.IMAGE_ICON, 0, 0, icon_flags)
        except Exception:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        # Taskbar icon
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, hicon, "Tooltip")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, (self.hwnd, 0, win32gui.NIF_INFO,
                                                        win32con.WM_USER + 20,
                                                        hicon, "Balloon Tooltip", msg, 200, title))
        time.sleep(duration)
        win32gui.DestroyWindow(self.hwnd)
        win32gui.UnregisterClass(self.wc.lpszClassName, None)
        return None

    def push(self, title="Notification", msg="This is a sample message", icon_path=None, duration=5, threaded=True):
        # Assuming this will be called within the GUI frameworks's mainloop we want to avoid blocking the mainloop
        # Therefore the threaded argument should preferably be True
        if not threaded:
            self._push(title, msg, icon_path, duration, threaded)
        else:
            thread = threading.Thread(target=self._push, args=(title, msg, icon_path, duration, threaded))
            thread.start()
            self._thread = thread
        return True

    def on_destroy(self, *_):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32api.PostQuitMessage(0)


# noinspection PyPep8Naming
def Notification():
    if PLATFORM == WINDOWS:
        return WindowsNotification()
    else:
        raise NotImplementedError


if __name__ == "__main__":
    n = Notification()
    n.push()
    n.push()
