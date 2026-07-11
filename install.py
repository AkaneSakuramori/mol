import os
import sys
import stat
import shutil


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(REPO_ROOT, "src", "ulang.py")


def default_bin_dir():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "Programs", "ulang")
    return os.path.join(os.path.expanduser("~"), ".local", "bin")


def install_unix(bin_dir):
    os.makedirs(bin_dir, exist_ok=True)
    launcher = os.path.join(bin_dir, "ulang")
    python = sys.executable
    with open(launcher, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\n")
        f.write(f'exec "{python}" "{SRC}" "$@"\n')
    mode = os.stat(launcher).st_mode
    os.chmod(launcher, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return launcher


def install_windows(bin_dir):
    os.makedirs(bin_dir, exist_ok=True)
    launcher = os.path.join(bin_dir, "ulang.cmd")
    python = sys.executable
    with open(launcher, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("@echo off\r\n")
        f.write(f'"{python}" "{SRC}" %*\r\n')
    return launcher


def main(argv):
    bin_dir = argv[1] if len(argv) > 1 else default_bin_dir()
    if not os.path.exists(SRC):
        print(f"error: cannot find {SRC}", file=sys.stderr)
        return 1
    if os.name == "nt":
        launcher = install_windows(bin_dir)
    else:
        launcher = install_unix(bin_dir)
    print(f"installed ulang launcher: {launcher}")
    path = os.environ.get("PATH", "")
    if bin_dir not in path.split(os.pathsep):
        print(f"note: add {bin_dir} to your PATH to run 'ulang' directly")
    print("verify with: ulang version")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
