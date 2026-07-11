import os
import sys
import shutil
import platform as _pyplatform


LINUX = "linux"
MACOS = "macos"
WINDOWS = "windows"


def normalize_os(system):
    s = system.lower()
    if s.startswith("linux"):
        return LINUX
    if s in ("darwin", "macos", "mac", "osx"):
        return MACOS
    if (s.startswith("win") or s.startswith("mingw") or s.startswith("msys")
            or s.startswith("cygwin")):
        return WINDOWS
    return s


def normalize_arch(machine):
    m = machine.lower()
    if m in ("x86_64", "amd64", "x64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "aarch64"
    if m in ("i386", "i686", "x86"):
        return "x86"
    if m.startswith("arm"):
        return "arm"
    return m


class Platform:
    def __init__(self, os_name, arch, exe_ext, obj_ext, dll_ext, path_sep,
                 line_sep, lib_names):
        self.os = os_name
        self.arch = arch
        self.exe_ext = exe_ext
        self.obj_ext = obj_ext
        self.dll_ext = dll_ext
        self.path_sep = path_sep
        self.line_sep = line_sep
        self._lib_names = lib_names

    def executable_name(self, base):
        if self.exe_ext and not base.endswith(self.exe_ext):
            return base + self.exe_ext
        return base

    def shared_library_name(self, base):
        if self.os == WINDOWS:
            return base + ".dll"
        if self.os == MACOS:
            return "lib" + base + ".dylib"
        return "lib" + base + ".so"

    def library_candidates(self, name):
        if name in self._lib_names:
            return list(self._lib_names[name])
        return [name, self.shared_library_name(name)]

    def is_windows(self):
        return self.os == WINDOWS

    def as_dict(self):
        return {
            "os": self.os,
            "arch": self.arch,
            "exe_ext": self.exe_ext,
            "obj_ext": self.obj_ext,
            "dll_ext": self.dll_ext,
            "path_sep": self.path_sep,
            "line_sep": "\\n" if self.line_sep == "\n" else "\\r\\n",
        }


_LINUX_LIBS = {
    "c": ["libc.so.6", "libc.so"],
    "libc": ["libc.so.6", "libc.so"],
    "m": ["libm.so.6", "libm.so"],
    "libm": ["libm.so.6", "libm.so"],
    "math": ["libm.so.6", "libm.so"],
}

_MACOS_LIBS = {
    "c": ["libc.dylib", "libSystem.dylib", "/usr/lib/libSystem.dylib"],
    "libc": ["libSystem.dylib", "/usr/lib/libSystem.dylib"],
    "m": ["libm.dylib", "libSystem.dylib", "/usr/lib/libSystem.dylib"],
    "libm": ["libm.dylib", "libSystem.dylib"],
    "math": ["libm.dylib", "libSystem.dylib"],
}

_WINDOWS_LIBS = {
    "c": ["msvcrt.dll", "ucrtbase.dll"],
    "libc": ["msvcrt.dll", "ucrtbase.dll"],
    "m": ["msvcrt.dll", "ucrtbase.dll"],
    "libm": ["msvcrt.dll", "ucrtbase.dll"],
    "math": ["msvcrt.dll", "ucrtbase.dll"],
}


def make_platform(system, machine):
    os_name = normalize_os(system)
    arch = normalize_arch(machine)
    if os_name == WINDOWS:
        return Platform(os_name, arch, ".exe", ".obj", ".dll", ";", "\r\n", _WINDOWS_LIBS)
    if os_name == MACOS:
        return Platform(os_name, arch, "", ".o", ".dylib", ":", "\n", _MACOS_LIBS)
    return Platform(os_name, arch, "", ".o", ".so", ":", "\n", _LINUX_LIBS)


def host_platform():
    return make_platform(_pyplatform.system(), _pyplatform.machine())


_C_COMPILERS = ["cc", "gcc", "clang"]
_WINDOWS_C_COMPILERS = ["gcc", "clang", "cc"]


def find_c_compiler(plat=None):
    plat = plat or host_platform()
    env = os.environ.get("ULANG_CC")
    if env:
        return env
    order = _WINDOWS_C_COMPILERS if plat.is_windows() else _C_COMPILERS
    for candidate in order:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def reloc_model(plat=None):
    plat = plat or host_platform()
    if plat.is_windows():
        return "default"
    return "pic"


HOST = host_platform()
