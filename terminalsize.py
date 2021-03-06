#!/usr/bin/env python

# Code from: https://gist.github.com/Captank/7912710 9-8-17
# Who got it from https://gist.github.com/jtriley/1108174 2011
"""
Uses a number of different methods to try and get the size of the terminal.
This supports methods to get info for
    - Windows
    - MacOS
    - Linux

This uses a cache to speed up the program and has defaults to return if all
else fails.
"""
import os
import shlex
import struct
import platform
import subprocess

__all__ = ["get_terminal_size"]
##__all__.extend(
##    ["_get_terminal_size", "_get_terminal_size_windows",
##     "_default",           "_get_terminal_size_tput",
##     "_get_terminal_size_tput", "_get_terminal_size_linux"])

__func = None

def get_terminal_size():
    if __func is None:
        return _get_terminal_size()
    else:
        return __func()

def _get_terminal_size():
    """ getTerminalSize()
     - get width and height of console
     - works on linux,os x,windows,cygwin(windows)
     originally retrieved from:
     http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    global __func
    current_os = platform.system()
    tuple_xy = None
    if current_os == 'Windows':
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
            __func = _get_terminal_size_tput
            # needed for window's python in cygwin's xterm!
        else:
            __func = _get_terminal_size_windows
    if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
#        print("default")
        tuple_xy = (80, 25)      # default value
        __func = _default
    elif __func is None:
        __func = _get_terminal_size_linux
    return tuple_xy

def _default():
    return (80, 25)

def _get_terminal_size_windows():
    try:
        if __func is None:
            global ctypes
            import ctypes
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = ctypes.windll.kernel32.GetStdHandle(-12)
        csbi = ctypes.create_string_buffer(22)
        res = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom,
             maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass


def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:# Fixed check_call -> check_output
        cols = int(subprocess.check_output(shlex.split('tput cols')))
        rows = int(subprocess.check_output(shlex.split('tput lines')))
        return (cols, rows)
    except:
        pass


def _get_terminal_size_linux():
    def ioctl_GWINSZ(fd):
        try:
            if __func is None:
                global fcntl, termios
                import fcntl
                import termios
            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except:
            pass
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)

        except OSError as err:
            if err.errno == 6:
                # For IDLE
                # [Errno 6] Device not configured: '/dev/tty'
                pass
        except Exception as err:
            print(str(err))
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])

if __name__ == "__main__":
    print('Terminal Size')
    print('Default: %r' % (_default(),))
    print('Windows: %r' % (_get_terminal_size_windows(),))
    print('Tput   : %r' % (_get_terminal_size_tput(),))
    print('Linux  : %r' % (_get_terminal_size_linux(),))
