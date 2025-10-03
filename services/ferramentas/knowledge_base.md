# Documentação de Poetry

## Fonte: https://python-poetry.org/docs/

Poetry is a tool for and in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you. Poetry offers a lockfile to ensure repeatable installs, and can build your project for distribution.
Poetry requires . It is multi-platform and the goal is to make it work equally well on Linux, macOS and Windows.
If you are viewing documentation for the development branch, you may wish to install a preview or development version of Poetry. See the installation instructions to use a preview or alternate version of Poetry.
is used to install Python CLI applications globally while still isolating them in virtual environments. will manage upgrades and uninstalls when used to install Poetry.
  1. If is not already installed, you can follow any of the options in the . Any non-ancient version of will do.
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, having multiple versions installed at the same time etc.
can also install versions of Poetry in parallel, which allows for easy testing of alternate or prerelease versions. Each version is given a unique, user-specified suffix, which will be used to create a unique binary name:
Finally, can install any valid , which allows for installations of the development version from , or even for local testing of pull requests:


We provide a custom installer that will install Poetry in a new virtual environment and allows Poetry to manage its own environment.
  1. The installer script is available directly at , and is developed in . The script can be executed directly (i.e. ‘curl python’) or downloaded and then executed from disk (e.g. in a CI environment).
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, using a pre-release build, configuring a different installation location etc.
If you want to install prerelease versions, you can do so by passing the option to the installation script or by using the environment variable:
If you want to install different versions of Poetry in parallel, a good approach is the installation with pipx and suffix.
  3.   4.   5.   6. If you decide Poetry isn’t your thing, you can completely remove it from your system by running the installer again with the option or by setting the environment variable before executing the installer.


Poetry can be installed manually using and the module. By doing so you will essentially perform the steps carried out by the official installer. As this is an advanced installation method, these instructions are Unix-only and omit specific examples such as installing from .
Unlike development environments, where making use of the latest tools is desirable, in a CI environment reproducibility should be made the priority. Here are some suggestions for installing Poetry in such an environment.
Whatever method you use, it is highly recommended to explicitly control the version of Poetry used, so that you are able to upgrade after performing your own validation. Each install method has a different syntax for setting the version that is used in the following examples.
Just as is a powerful tool for development use, it is equally useful in a CI environment and should be one of your top choices for use of Poetry in CI.
The official installer script () offers a streamlined and simplified installation of Poetry, sufficient for developer use or for simple pipelines. However, in a CI environment the other two supported installation methods (pipx and manual) should be seriously considered.
Downloading a copy of the installer script to a place accessible by your CI pipelines (or maintaining a copy of the ) is strongly suggested, to ensure your pipeline’s stability and to maintain control over what code is executed.
By default, the installer will install to a user-specific directory. In more complex pipelines that may make accessing Poetry difficult (especially in cases like multi-stage container builds). It is highly suggested to make use of when using the official installer in CI, as that way the exact paths can be controlled.
For maximum control in your CI environment, installation with is fully supported and something you should consider. While this requires more explicit commands and knowledge of Python packaging from you, it in return offers the best debugging experience, and leaves you subject to the fewest external tools.
If you install Poetry via , ensure you have Poetry installed into an isolated environment that is as the target environment managed by Poetry. If Poetry and your project are installed into the same environment, Poetry is likely to upgrade or uninstall its own dependencies (causing hard-to-debug and understand errors).
Poetry should always be installed in a dedicated virtual environment to isolate it from the rest of your system. Each of the above described installation methods ensures that. It should in no case be installed in the environment of the project that is to be managed by Poetry. This ensures that Poetry’s own dependencies will not be accidentally upgraded or uninstalled. In addition, the isolated virtual environment in which poetry is installed should not be activated for running poetry commands.


---

## Fonte: https://install.python-poetry.org

```
#!/usr/bin/env python3
r"""
This script will install Poetry and its dependencies in an isolated fashion.

It will perform the following steps:
    * Create a new virtual environment using the built-in venv module, or the virtualenv zipapp if venv is unavailable.
      This will be created at a platform-specific path (or `$POETRY_HOME` if `$POETRY_HOME` is set:
        - `~/Library/Application Support/pypoetry` on macOS
        - `$XDG_DATA_HOME/pypoetry` on Linux/Unix (`$XDG_DATA_HOME` is `~/.local/share` if unset)
        - `%APPDATA%\pypoetry` on Windows
    * Update pip inside the virtual environment to avoid bugs in older versions.
    * Install the latest (or a given) version of Poetry inside this virtual environment using pip.
    * Install a `poetry` script into a platform-specific path (or `$POETRY_HOME/bin` if `$POETRY_HOME` is set):
        - `~/.local/bin` on Unix
        - `%APPDATA%\Python\Scripts` on Windows
    * Attempt to inform the user if they need to add this bin directory to their `$PATH`, as well as how to do so.
    * Upon failure, write an error log to `poetry-installer-error-<hash>.log and restore any previous environment.

This script performs minimal magic, and should be relatively stable. However, it is optimized for interactive developer
use and trivial pipelines. If you are considering using this script in production, you should consider manually-managed
installs, or use of pipx as alternatives to executing arbitrary, unversioned code from the internet. If you prefer this
script to alternatives, consider maintaining a local copy as part of your infrastructure.

For full documentation, visit https://python-poetry.org/docs/#installation.
"""
import sys


# Eager version check so we fail nicely before possible syntax errors
if sys.version_info < (3, 6):  # noqa: UP036
    sys.stdout.write("Poetry installer requires Python 3.6 or newer to run!\n")
    sys.exit(1)


import argparse
import json
import os
import re
import shutil
import subprocess
import sysconfig
import tempfile

from contextlib import closing
from contextlib import contextmanager
from functools import cmp_to_key
from io import UnsupportedOperation
from pathlib import Path
from typing import Optional
from urllib.request import Request
from urllib.request import urlopen


SHELL = os.getenv("SHELL", "")
WINDOWS = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
MINGW = sysconfig.get_platform().startswith("mingw")
MACOS = sys.platform == "darwin"

FOREGROUND_COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
}

BACKGROUND_COLORS = {
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "magenta": 45,
    "cyan": 46,
    "white": 47,
}

OPTIONS = {"bold": 1, "underscore": 4, "blink": 5, "reverse": 7, "conceal": 8}


def style(fg, bg, options):
    codes = []

    if fg:
        codes.append(FOREGROUND_COLORS[fg])

    if bg:
        codes.append(BACKGROUND_COLORS[bg])

    if options:
        if not isinstance(options, (list, tuple)):
            options = [options]

        for option in options:
            codes.append(OPTIONS[option])

    return "\033[{}m".format(";".join(map(str, codes)))


STYLES = {
    "info": style("cyan", None, None),
    "comment": style("yellow", None, None),
    "success": style("green", None, None),
    "error": style("red", None, None),
    "warning": style("yellow", None, None),
    "b": style(None, None, ("bold",)),
}


def is_decorated():
    if WINDOWS:
        return (
            os.getenv("ANSICON") is not None
            or os.getenv("ConEmuANSI") == "ON"  # noqa: SIM112
            or os.getenv("Term") == "xterm"  # noqa: SIM112
        )

    if not hasattr(sys.stdout, "fileno"):
        return False

    try:
        return os.isatty(sys.stdout.fileno())
    except UnsupportedOperation:
        return False


def is_interactive():
    if not hasattr(sys.stdin, "fileno"):
        return False

    try:
        return os.isatty(sys.stdin.fileno())
    except UnsupportedOperation:
        return False


def colorize(style, text):
    if not is_decorated():
        return text

    return f"{STYLES[style]}{text}\033[0m"


def string_to_bool(value):
    value = value.lower()

    return value in {"true", "1", "y", "yes"}


def data_dir() -> Path:
    if os.getenv("POETRY_HOME"):
        return Path(os.getenv("POETRY_HOME")).expanduser()

    if WINDOWS:
        base_dir = Path(_get_win_folder("CSIDL_APPDATA"))
    elif MACOS:
        base_dir = Path("~/Library/Application Support").expanduser()
    else:
        base_dir = Path(os.getenv("XDG_DATA_HOME", "~/.local/share")).expanduser()

    base_dir = base_dir.resolve()
    return base_dir / "pypoetry"


def bin_dir() -> Path:
    if os.getenv("POETRY_HOME"):
        return Path(os.getenv("POETRY_HOME")).expanduser() / "bin"

    if WINDOWS and not MINGW:
        return Path(_get_win_folder("CSIDL_APPDATA")) / "Python/Scripts"
    else:
        return Path("~/.local/bin").expanduser()


def _get_win_folder_from_registry(csidl_name):
    import winreg as _winreg

    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(
        _winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    )
    path, _ = _winreg.QueryValueEx(key, shell_folder_name)

    return path


def _get_win_folder_with_ctypes(csidl_name):
    import ctypes

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value


if WINDOWS:
    try:
        from ctypes import windll  # noqa: F401

        _get_win_folder = _get_win_folder_with_ctypes
    except ImportError:
        _get_win_folder = _get_win_folder_from_registry


PRE_MESSAGE = """# Welcome to {poetry}!

This will download and install the latest version of {poetry},
a dependency and package manager for Python.

It will add the `poetry` command to {poetry}'s bin directory, located at:

{poetry_home_bin}

You can uninstall at any time by executing this script with the --uninstall option,
and these changes will be reverted.
"""

POST_MESSAGE = """{poetry} ({version}) is installed now. Great!

You can test that everything is set up by executing:

`{test_command}`
"""

POST_MESSAGE_NOT_IN_PATH = """{poetry} ({version}) is installed now. Great!

To get started you need {poetry}'s bin directory ({poetry_home_bin}) in your `PATH`
environment variable.
{configure_message}
Alternatively, you can call {poetry} explicitly with `{poetry_executable}`.

You can test that everything is set up by executing:

`{test_command}`
"""

POST_MESSAGE_CONFIGURE_UNIX = """
Add `export PATH="{poetry_home_bin}:$PATH"` to your shell configuration file.
"""

POST_MESSAGE_CONFIGURE_FISH = """
You can execute `set -U fish_user_paths {poetry_home_bin} $fish_user_paths`
"""

POST_MESSAGE_CONFIGURE_WINDOWS = """
You can choose and execute one of the following commands in PowerShell:

A. Append the bin directory to your user environment variable `PATH`:

```
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";{poetry_home_bin}", "User")
```

B. Try to append the bin directory to PATH every when you run PowerShell (>=6 recommended):

```
echo 'if (-not (Get-Command poetry -ErrorAction Ignore)) {{ $env:Path += ";{poetry_home_bin}" }}' | Out-File -Append $PROFILE
```
"""


class PoetryInstallationError(RuntimeError):
    def __init__(self, return_code: int = 0, log: Optional[str] = None):
        super().__init__()
        self.return_code = return_code
        self.log = log


class VirtualEnvironment:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._bin_path = self._path.joinpath(
            "Scripts" if WINDOWS and not MINGW else "bin"
        )
        # str is for compatibility with subprocess.run on CPython <= 3.7 on Windows
        self._python = str(
            self._path.joinpath(self._bin_path, "python.exe" if WINDOWS else "python")
        )

    @property
    def path(self):
        return self._path

    @property
    def bin_path(self):
        return self._bin_path

    @classmethod
    def make(cls, target: Path) -> "VirtualEnvironment":
        if not sys.executable:
            raise ValueError(
                "Unable to determine sys.executable. Set PATH to a sane value or set it"
                " explicitly with PYTHONEXECUTABLE."
            )

        try:
            # on some linux distributions (eg: debian), the distribution provided python
            # installation might not include ensurepip, causing the venv module to
            # fail when attempting to create a virtual environment
            # we import ensurepip but do not use it explicitly here
            import ensurepip  # noqa: F401
            import venv

            builder = venv.EnvBuilder(clear=True, with_pip=True, symlinks=False)
            context = builder.ensure_directories(target)

            if (
                WINDOWS
                and hasattr(context, "env_exec_cmd")
                and context.env_exe != context.env_exec_cmd
            ):
                target = target.resolve()

            builder.create(target)
        except ImportError:
            # fallback to using virtualenv package if venv is not available, eg: ubuntu
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            virtualenv_bootstrap_url = (
                f"https://bootstrap.pypa.io/virtualenv/{python_version}/virtualenv.pyz"
            )

            with tempfile.TemporaryDirectory(prefix="poetry-installer") as temp_dir:
                virtualenv_pyz = Path(temp_dir) / "virtualenv.pyz"
                request = Request(
                    virtualenv_bootstrap_url, headers={"User-Agent": "Python Poetry"}
                )
                virtualenv_pyz.write_bytes(urlopen(request).read())
                cls.run(
                    sys.executable, virtualenv_pyz, "--clear", "--always-copy", target
                )

        # We add a special file so that Poetry can detect
        # its own virtual environment
        target.joinpath("poetry_env").touch()

        env = cls(target)

        # this ensures that outdated system default pip does not trigger older bugs
        env.pip("install", "--disable-pip-version-check", "--upgrade", "pip")

        return env

    @staticmethod
    def run(*args, **kwargs) -> subprocess.CompletedProcess:
        completed_process = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        if completed_process.returncode != 0:
            raise PoetryInstallationError(
                return_code=completed_process.returncode,
                log=completed_process.stdout.decode(),
            )
        return completed_process

    def python(self, *args, **kwargs) -> subprocess.CompletedProcess:
        return self.run(self._python, *args, **kwargs)

    def pip(self, *args, **kwargs) -> subprocess.CompletedProcess:
        return self.python("-m", "pip", *args, **kwargs)


class Cursor:
    def __init__(self) -> None:
        self._output = sys.stdout

    def move_up(self, lines: int = 1) -> "Cursor":
        self._output.write(f"\x1b[{lines}A")

        return self

    def move_down(self, lines: int = 1) -> "Cursor":
        self._output.write(f"\x1b[{lines}B")

        return self

    def move_right(self, columns: int = 1) -> "Cursor":
        self._output.write(f"\x1b[{columns}C")

        return self

    def move_left(self, columns: int = 1) -> "Cursor":
        self._output.write(f"\x1b[{columns}D")

        return self

    def move_to_column(self, column: int) -> "Cursor":
        self._output.write(f"\x1b[{column}G")

        return self

    def move_to_position(self, column: int, row: int) -> "Cursor":
        self._output.write(f"\x1b[{row + 1};{column}H")

        return self

    def save_position(self) -> "Cursor":
        self._output.write("\x1b7")

        return self

    def restore_position(self) -> "Cursor":
        self._output.write("\x1b8")

        return self

    def hide(self) -> "Cursor":
        self._output.write("\x1b[?25l")

        return self

    def show(self) -> "Cursor":
        self._output.write("\x1b[?25h\x1b[?0c")

        return self

    def clear_line(self) -> "Cursor":
        """
        Clears all the output from the current line.
        """
        self._output.write("\x1b[2K")

        return self

    def clear_line_after(self) -> "Cursor":
        """
        Clears all the output from the current line after the current position.
        """
        self._output.write("\x1b[K")

        return self

    def clear_output(self) -> "Cursor":
        """
        Clears all the output from the cursors' current position
        to the end of the screen.
        """
        self._output.write("\x1b[0J")

        return self

    def clear_screen(self) -> "Cursor":
        """
        Clears the entire screen.
        """
        self._output.write("\x1b[2J")

        return self


class Installer:
    METADATA_URL = "https://pypi.org/pypi/poetry/json"
    VERSION_REGEX = re.compile(
        r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
        "("
        "[._-]?"
        r"(?:(stable|beta|b|rc|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
        "([.-]?dev)?"
        ")?"
        r"(?:\+[^\s]+)?"
    )

    def __init__(
        self,
        version: Optional[str] = None,
        preview: bool = False,
        force: bool = False,
        accept_all: bool = False,
        git: Optional[str] = None,
        path: Optional[str] = None,
    ) -> None:
        self._version = version
        self._preview = preview
        self._force = force
        self._accept_all = accept_all
        self._git = git
        self._path = path

        self._cursor = Cursor()
        self._bin_dir = None
        self._data_dir = None

    @property
    def bin_dir(self) -> Path:
        if not self._bin_dir:
            self._bin_dir = bin_dir()
        return self._bin_dir

    @property
    def data_dir(self) -> Path:
        if not self._data_dir:
            self._data_dir = data_dir()
        return self._data_dir

    @property
    def version_file(self) -> Path:
        return self.data_dir.joinpath("VERSION")

    def allows_prereleases(self) -> bool:
        return self._preview

    def run(self) -> int:
        if self._git:
            version = self._git
        elif self._path:
            version = self._path
        else:
            try:
                version, current_version = self.get_version()
            except ValueError:
                return 1

        if version is None:
            return 0

        self.display_pre_message()
        self.ensure_directories()

        def _is_self_upgrade_supported(x):
            mx = self.VERSION_REGEX.match(x)

            if mx is None:
                # the version is not semver, perhaps scm or file
                # we assume upgrade is supported
                return True

            vx = (*tuple(int(p) for p in mx.groups()[:3]), mx.group(5))
            return vx >= (1, 1, 7)

        if version and not _is_self_upgrade_supported(version):
            self._write(
                colorize(
                    "warning",
                    f"You are installing {version}. When using the current installer, "
                    "this version does not support updating using the 'self update' "
                    "command. Please use 1.1.7 or later.",
                )
            )
            if not self._accept_all:
                continue_install = input("Do you want to continue? ([y]/n) ") or "y"
                if continue_install.lower() in {"n", "no"}:
                    return 0

        try:
            self.install(version)
        except subprocess.CalledProcessError as e:
            raise PoetryInstallationError(
                return_code=e.returncode, log=e.output.decode()
            ) from e

        self._write("")
        self.display_post_message(version)

        return 0

    def install(self, version):
        """
        Installs Poetry in $POETRY_HOME.
        """
        self._write(
            "Installing {} ({})".format(
                colorize("info", "Poetry"), colorize("info", version)
            )
        )

        with self.make_env(version) as env:
            self.install_poetry(version, env)
            self.make_bin(version, env)
            self.version_file.write_text(version)
            self._install_comment(version, "Done")

            return 0

    def uninstall(self) -> int:
        if not self.data_dir.exists():
            self._write(
                "{} is not currently installed.".format(colorize("info", "Poetry"))
            )

            return 1

        version = None
        if self.version_file.exists():
            version = self.version_file.read_text().strip()

        if version:
            self._write(
                "Removing {} ({})".format(
                    colorize("info", "Poetry"), colorize("b", version)
                )
            )
        else:
            self._write("Removing {}".format(colorize("info", "Poetry")))

        shutil.rmtree(str(self.data_dir))
        for script in ["poetry", "poetry.bat", "poetry.exe"]:
            if self.bin_dir.joinpath(script).exists():
                self.bin_dir.joinpath(script).unlink()

        return 0

    def _install_comment(self, version: str, message: str):
        self._overwrite(
            "Installing {} ({}): {}".format(
                colorize("info", "Poetry"),
                colorize("b", version),
                colorize("comment", message),
            )
        )

    @contextmanager
    def make_env(self, version: str) -> VirtualEnvironment:
        env_path = self.data_dir.joinpath("venv")
        env_path_saved = env_path.with_suffix(".save")

        if env_path.exists():
            self._install_comment(version, "Saving existing environment")
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved)
            shutil.move(env_path, env_path_saved)

        try:
            self._install_comment(version, "Creating environment")
            yield VirtualEnvironment.make(env_path)
        except Exception as e:
            if env_path.exists():
                self._install_comment(
                    version, "An error occurred. Removing partial environment."
                )
                shutil.rmtree(env_path)

            if env_path_saved.exists():
                self._install_comment(
                    version, "Restoring previously saved environment."
                )
                shutil.move(env_path_saved, env_path)

            raise e
        else:
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved, ignore_errors=True)

    def make_bin(self, version: str, env: VirtualEnvironment) -> None:
        self._install_comment(version, "Creating script")
        self.bin_dir.mkdir(parents=True, exist_ok=True)

        script = "poetry.exe" if WINDOWS else "poetry"
        target_script = env.bin_path.joinpath(script)

        if self.bin_dir.joinpath(script).exists():
            self.bin_dir.joinpath(script).unlink()

        try:
            self.bin_dir.joinpath(script).symlink_to(target_script)
        except OSError:
            # This can happen if the user
            # does not have the correct permission on Windows
            shutil.copy(target_script, self.bin_dir.joinpath(script))

    def install_poetry(self, version: str, env: VirtualEnvironment) -> None:
        self._install_comment(version, "Installing Poetry")

        if self._git:
            specification = "git+" + version
        elif self._path:
            specification = version
        else:
            specification = f"poetry=={version}"

        env.pip("install", specification)

    def display_pre_message(self) -> None:
        kwargs = {
            "poetry": colorize("info", "Poetry"),
            "poetry_home_bin": colorize("comment", self.bin_dir),
        }
        self._write(PRE_MESSAGE.format(**kwargs))

    def display_post_message(self, version: str) -> None:
        if WINDOWS:
            return self.display_post_message_windows(version)

        if SHELL == "fish":
            return self.display_post_message_fish(version)

        return self.display_post_message_unix(version)

    def display_post_message_windows(self, version: str) -> None:
        path = self.get_windows_path_var()

        message = POST_MESSAGE_NOT_IN_PATH
        if path and str(self.bin_dir) in path:
            message = POST_MESSAGE

        self._write(
            message.format(
                poetry=colorize("info", "Poetry"),
                version=colorize("b", version),
                poetry_home_bin=colorize("comment", self.bin_dir),
                poetry_executable=colorize("b", self.bin_dir.joinpath("poetry")),
                configure_message=POST_MESSAGE_CONFIGURE_WINDOWS.format(
                    poetry_home_bin=colorize("comment", self.bin_dir)
                ),
                test_command=colorize("b", "poetry --version"),
            )
        )

    def get_windows_path_var(self) -> Optional[str]:
        import winreg

        with winreg.ConnectRegistry(
            None, winreg.HKEY_CURRENT_USER
        ) as root, winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
            path, _ = winreg.QueryValueEx(key, "PATH")

            return path

    def display_post_message_fish(self, version: str) -> None:
        fish_user_paths = subprocess.check_output(
            ["fish", "-c", "echo $fish_user_paths"]
        ).decode("utf-8")

        message = POST_MESSAGE_NOT_IN_PATH
        if fish_user_paths and str(self.bin_dir) in fish_user_paths:
            message = POST_MESSAGE

        self._write(
            message.format(
                poetry=colorize("info", "Poetry"),
                version=colorize("b", version),
                poetry_home_bin=colorize("comment", self.bin_dir),
                poetry_executable=colorize("b", self.bin_dir.joinpath("poetry")),
                configure_message=POST_MESSAGE_CONFIGURE_FISH.format(
                    poetry_home_bin=colorize("comment", self.bin_dir)
                ),
                test_command=colorize("b", "poetry --version"),
            )
        )

    def display_post_message_unix(self, version: str) -> None:
        paths = os.getenv("PATH", "").split(":")

        message = POST_MESSAGE_NOT_IN_PATH
        if paths and str(self.bin_dir) in paths:
            message = POST_MESSAGE

        self._write(
            message.format(
                poetry=colorize("info", "Poetry"),
                version=colorize("b", version),
                poetry_home_bin=colorize("comment", self.bin_dir),
                poetry_executable=colorize("b", self.bin_dir.joinpath("poetry")),
                configure_message=POST_MESSAGE_CONFIGURE_UNIX.format(
                    poetry_home_bin=colorize("comment", self.bin_dir)
                ),
                test_command=colorize("b", "poetry --version"),
            )
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)

    def get_version(self):
        current_version = None
        if self.version_file.exists():
            current_version = self.version_file.read_text().strip()

        self._write(colorize("info", "Retrieving Poetry metadata"))

        metadata = json.loads(self._get(self.METADATA_URL).decode())

        def _compare_versions(x, y):
            mx = self.VERSION_REGEX.match(x)
            my = self.VERSION_REGEX.match(y)

            vx = (*tuple(int(p) for p in mx.groups()[:3]), mx.group(5))
            vy = (*tuple(int(p) for p in my.groups()[:3]), my.group(5))

            if vx < vy:
                return -1
            elif vx > vy:
                return 1

            return 0

        self._write("")
        releases = sorted(
            metadata["releases"].keys(), key=cmp_to_key(_compare_versions)
        )

        if self._version and self._version not in releases:
            msg = f"Version {self._version} does not exist."
            self._write(colorize("error", msg))

            raise ValueError(msg)

        version = self._version
        if not version:
            for release in reversed(releases):
                m = self.VERSION_REGEX.match(release)
                if m.group(5) and not self.allows_prereleases():
                    continue

                version = release

                break

        if current_version == version and not self._force:
            self._write(
                f'The latest version ({colorize("b", version)}) is already installed.'
            )

            return None, current_version

        return version, current_version

    def _write(self, line) -> None:
        sys.stdout.write(line + "\n")

    def _overwrite(self, line) -> None:
        if not is_decorated():
            return self._write(line)

        self._cursor.move_up()
        self._cursor.clear_line()
        self._write(line)

    def _get(self, url):
        request = Request(url, headers={"User-Agent": "Python Poetry"})

        with closing(urlopen(request)) as r:
            return r.read()


def main():
    parser = argparse.ArgumentParser(
        description="Installs the latest (or given) version of poetry"
    )
    parser.add_argument(
        "-p",
        "--preview",
        help="install preview version",
        dest="preview",
        action="store_true",
        default=False,
    )
    parser.add_argument("--version", help="install named version", dest="version")
    parser.add_argument(
        "-f",
        "--force",
        help="install on top of existing version",
        dest="force",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-y",
        "--yes",
        help="accept all prompts",
        dest="accept_all",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--uninstall",
        help="uninstall poetry",
        dest="uninstall",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--path",
        dest="path",
        action="store",
        help=(
            "Install from a given path (file or directory) instead of "
            "fetching the latest version of Poetry available online."
        ),
    )
    parser.add_argument(
        "--git",
        dest="git",
        action="store",
        help=(
            "Install from a git repository instead of fetching the latest version "
            "of Poetry available online."
        ),
    )

    args = parser.parse_args()

    installer = Installer(
        version=args.version or os.getenv("POETRY_VERSION"),
        preview=args.preview or string_to_bool(os.getenv("POETRY_PREVIEW", "0")),
        force=args.force,
        accept_all=args.accept_all
        or string_to_bool(os.getenv("POETRY_ACCEPT", "0"))
        or not is_interactive(),
        path=args.path,
        git=args.git,
    )

    if args.uninstall or string_to_bool(os.getenv("POETRY_UNINSTALL", "0")):
        return installer.uninstall()

    try:
        return installer.run()
    except PoetryInstallationError as e:
        installer._write(colorize("error", "Poetry installation failed."))

        if e.log is not None:
            import traceback

            _, path = tempfile.mkstemp(
                suffix=".log",
                prefix="poetry-installer-error-",
                dir=str(Path.cwd()),
                text=True,
            )
            installer._write(colorize("error", f"See {path} for error logs."))
            tb = "".join(traceback.format_tb(e.__traceback__))
            text = f"{e.log}\nTraceback:\n\n{tb}"
            Path(path).write_text(text)

        return e.return_code


if __name__ == "__main__":
    sys.exit(main())

```



---

## Fonte: https://python-poetry.org

```
  show --tree
 0.8.0 A utility belt for advanced users...
└──  <3.0.0,>=2.0.1
    ├──  >=2017.4.17
    ├──  >=3.0.2,<3.1.0
    ├──  >=2.5,<2.7
    └──  <1.23,>=1.21.1

  show --latest
     Python datetimes made easy.
     A high-level Python Web framework ...
    Python HTTP for Humans.

```



---

## Fonte: https://python-poetry.org/docs/libraries

While Poetry does not enforce any release convention, it used to encourage the use of within the scope of and supports that are especially suitable for semver.
For your library, you may commit the file if you want to. This can help your team to always test against the same dependency versions. However, this lock file will not have any effect on other projects that depend on it. It only has an effect on the main project.
Poetry will automatically include some license-related files when building a package - in the directory when building a , and in the root folder when building an :
The command will then use the specified build backend to build your package in an isolated environment. Ensure you have specified any additional settings according to the documentation of the build backend you are using.
Poetry will publish to by default. Anything that is published to PyPI is available automatically through Poetry. Since is on PyPI we can depend on it without having to specify any additional repositories.
This will package and publish the library to PyPI, on the condition that you are a registered user and you have properly.
In order to publish to a private repository, you will need to add it to your global list of repositories. See for more information.


---

## Fonte: https://python-poetry.org/docs/1.8

Poetry is a tool for and in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you. Poetry offers a lockfile to ensure repeatable installs, and can build your project for distribution.
Poetry requires . It is multi-platform and the goal is to make it work equally well on Linux, macOS and Windows.
Poetry should always be installed in a dedicated virtual environment to isolate it from the rest of your system. It should in no case be installed in the environment of the project that is to be managed by Poetry. This ensures that Poetry’s own dependencies will not be accidentally upgraded or uninstalled. (Each of the following installation methods ensures that Poetry is installed into an isolated environment.) In addition, the isolated virtual environment in which poetry is installed should not be activated for running poetry commands.
If you are viewing documentation for the development branch, you may wish to install a preview or development version of Poetry. See the installation instructions to use a preview or alternate version of Poetry.
is used to install Python CLI applications globally while still isolating them in virtual environments. will manage upgrades and uninstalls when used to install Poetry.
  1. If is not already installed, you can follow any of the options in the . Any non-ancient version of will do.
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, having multiple versions installed at the same time etc.
can also install versions of Poetry in parallel, which allows for easy testing of alternate or prerelease versions. Each version is given a unique, user-specified suffix, which will be used to create a unique binary name:
Finally, can install any valid , which allows for installations of the development version from , or even for local testing of pull requests:


We provide a custom installer that will install Poetry in a new virtual environment and allows Poetry to manage its own environment.
  1. The installer script is available directly at , and is developed in . The script can be executed directly (i.e. ‘curl python’) or downloaded and then executed from disk (e.g. in a CI environment).
The installer has been deprecated and removed from the Poetry repository. Please migrate from the in-tree version to the standalone version described above.
Note: On some systems, may still refer to Python 2 instead of Python 3. We always suggest the binary to avoid ambiguity.
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, using a pre-release build, configuring a different installation location etc.
If you want to install prerelease versions, you can do so by passing the option to the installation script or by using the environment variable:
If you want to install different versions of Poetry in parallel, a good approach is the installation with pipx and suffix.
  3.   4.   5. Poetry series releases are not able to update in-place to or newer series releases. To migrate to newer releases, uninstall using your original install method, and then reinstall using the .
  6. If you decide Poetry isn’t your thing, you can completely remove it from your system by running the installer again with the option or by setting the environment variable before executing the installer.


Poetry can be installed manually using and the module. By doing so you will essentially perform the steps carried out by the official installer. As this is an advanced installation method, these instructions are Unix-only and omit specific examples such as installing from .
Unlike development environments, where making use of the latest tools is desirable, in a CI environment reproducibility should be made the priority. Here are some suggestions for installing Poetry in such an environment.
Whatever method you use, it is highly recommended to explicitly control the version of Poetry used, so that you are able to upgrade after performing your own validation. Each install method has a different syntax for setting the version that is used in the following examples.
Just as is a powerful tool for development use, it is equally useful in a CI environment and should be one of your top choices for use of Poetry in CI.
The official installer script () offers a streamlined and simplified installation of Poetry, sufficient for developer use or for simple pipelines. However, in a CI environment the other two supported installation methods (pipx and manual) should be seriously considered.
Downloading a copy of the installer script to a place accessible by your CI pipelines (or maintaining a copy of the ) is strongly suggested, to ensure your pipeline’s stability and to maintain control over what code is executed.
By default, the installer will install to a user-specific directory. In more complex pipelines that may make accessing Poetry difficult (especially in cases like multi-stage container builds). It is highly suggested to make use of when using the official installer in CI, as that way the exact paths can be controlled.
For maximum control in your CI environment, installation with is fully supported and something you should consider. While this requires more explicit commands and knowledge of Python packaging from you, it in return offers the best debugging experience, and leaves you subject to the fewest external tools.
If you install Poetry via , ensure you have Poetry installed into an isolated environment that is as the target environment managed by Poetry. If Poetry and your project are installed into the same environment, Poetry is likely to upgrade or uninstall its own dependencies (causing hard-to-debug and understand errors).
supports generating completion scripts for Bash, Fish, and Zsh. See for full details, but the gist is as simple as using one of the following:


---

## Fonte: https://python-poetry.org/docs/repositories

By default, Poetry discovers and installs packages from . But, you want to install a dependency to your project for a ? Let’s do it.
Depending on your system configuration, credentials might be saved in your command line history. Many shells do not save commands to history when they are prefixed by a space character. For more information, please refer to your shell’s documentation.
If you would like to provide the password interactively, you can simply omit in your command. And Poetry will prompt you to enter the credential manually.
Great, now all that is left is to publish your package. Assuming you’d want to share it privately with your team, you can configure the endpoint for your .
If you need to use a different credential for your , then it is recommended to use a different name for your publishing repository.
By default, if you have not configured any primary source, Poetry is configured to use the Python ecosystem’s canonical package index . You can alter this behavior and exclusively look up packages only from the configured package sources by adding at least one primary source.
Except for the implicitly configured source for named , package sources are local to a project and must be configured within the project’s file. This is the same configuration used when publishing a package.
Consequently, when a Poetry project is e.g., installed using Pip (as a normal package or in editable mode), package sources will be ignored and the dependencies in question downloaded from PyPI by default.
If is undefined, the source is considered a primary source, which disables the implicit PyPI source and takes precedence over supplemental sources.
All primary package sources are searched for each dependency without a . If you configure at least one primary source, the implicit PyPI source is disabled.
The implicit PyPI source is disabled automatically if at least one primary source is configured. If you want to use PyPI in addition to a primary source, configure it explicitly with a certain priority, e.g.
Because PyPI is internally configured with Poetry, the PyPI repository cannot be configured with a given URL. Remember, you can always use to ensure the validity of the file.
Package sources configured as supplemental are only searched if no other (higher-priority) source yields a compatible package distribution. This is particularly convenient if the response time of the source is high and relatively few package distributions are to be fetched from this source.
Take into account that someone could publish a new package to a primary source which matches a package in your supplemental source. They could coincidentally or intentionally replace your dependency with something you did not expect.
If package sources are configured as explicit, these sources are only searched when a package configuration that it should be found on this package source.
All package sources (including possibly supplemental sources) will be searched during the package lookup process. These network requests will occur for all primary sources, regardless of if the package is found at one or more sources, and all supplemental sources until the package is found.
In order to limit the search for a specific package to a particular package repository, you can specify the source explicitly.
A repository that is configured to be the only source for retrieving a certain package can itself have any priority. In particular, it does not need to have priority . If a repository is configured to be the source of a package, it will be the only source that is considered for that package and the repository priority will have no effect on the resolution.
Package keys are not inherited by their dependencies. In particular, if is configured to be found in , and depends on that is also to be found on , then needs to be configured as such in . The easiest way to achieve this is to add with a wildcard constraint:
Package source constraints are strongly suggested for all packages that are expected to be provided only by one specific source to avoid dependency confusion attacks.
If the package’s published metadata is invalid, Poetry will download the available bdist/sdist to inspect it locally to identify the relevant metadata.
Poetry can fetch and install package dependencies from public or private custom repositories that implement the simple repository API as described in .
When using sources that distribute large wheels without providing file checksum in file URLs, Poetry will download each candidate wheel at least once in order to generate the checksum. This can manifest as long dependency resolution times when adding packages from this source.
In addition to , Poetry can also handle simple API repositories that implement (). This is helpful in reducing dependency resolution time for packages from these sources as Poetry can avoid having to download each candidate distribution, in order to determine associated metadata.
The need for this stems from the fact that Poetry’s lock file is platform-agnostic. This means, in order to resolve dependencies for a project, Poetry needs metadata for all platform-specific distributions. And when this metadata is not readily available, downloading the distribution and inspecting it locally is the only remaining option.
Some projects choose to release their binary distributions via a single page link source that partially follows the structure of a package page in .
Poetry treats repositories to which you publish packages as user-specific and not project-specific configuration unlike . Poetry, today, only supports the when publishing your project.
URLs are typically different to the same one provided by the repository for the simple API. You’ll note that in the example of , both the host () as well as the path () are different to its simple API ().
Note that it is recommended to use when uploading packages to PyPI. Once you have created a new token, you can tell Poetry to use it:
If a system keyring is available and supported, the password is stored to and retrieved from the keyring. In the above example, the credential will be stored using the name . If access to keyring fails or is unsupported, this will fall back to writing the password to the file along with the username.
If you do not want to use the keyring, you can tell Poetry to disable it and store the credentials in plaintext config files:
Poetry will fall back to Pip style use of keyring so that backends like Microsoft’s get a chance to retrieve valid credentials. It will need to be properly installed into Poetry’s virtualenv, preferably by installing a plugin.
where is the name of the repository in uppercase (e.g. ). See for more information on how to configure Poetry with environment variables.
If your password starts with a dash (e.g., randomly generated tokens in a CI environment), it will be parsed as a command line option instead of a password. You can prevent this by adding double dashes to prevent any following argument from being parsed as an option.
Empty usernames are discouraged. However, Poetry will honor them if a password is configured without it. This is unfortunately commonplace practice, while not best practice, for private indices that use tokens. When a password is stored into the system keyring with an empty username, Poetry will use a literal as the username to circumvent .
Poetry supports repositories that are secured by a custom certificate authority as well as those that require certificate-based client authentication. The following will configure the “foo” repository to validate the repository’s certificate using a custom certificate authority and use a client certificate (note that these config variables do not both need to be set):
The value of can be set to if certificate verification is required to be skipped. This is useful for cases where a package source with self-signed certificates is used.
Further, every HTTP backed package source caches metadata associated with a package once it is fetched or generated. Additionally, downloaded files (package distributions) are also cached.
If you encounter issues with package sources, one of the simplest steps you might take to debug an issue is rerunning your command with the flag.


---

## Fonte: https://python-poetry.org/docs/faq

While the dependency resolver at the heart of Poetry is highly optimized and should be fast enough for most cases, with certain sets of dependencies, it can take time to find a valid solution.
This is due to the fact that not all libraries on PyPI have properly declared their metadata and, as such, they are not available via the PyPI JSON API. At this point, Poetry has no choice but to download the packages and inspect them to get the necessary information. This is an expensive operation, both in bandwidth and time, which is why it seems this is a long process.
At the moment, there is no way around it. However, if you notice that Poetry is downloading many versions of a single package, you can lessen the workload by constraining that one package in your pyproject.toml more narrowly. That way, Poetry does not have to sift through so many versions of it, which may speed up the locking process considerably in some cases.
  * A major version bump (incrementing the first number) is only done for breaking changes if a deprecation cycle is not possible, and many users have to perform some manual steps to migrate from one version to the next one.
  * A minor version bump (incrementing the second number) may include new features as well as new deprecations and drop features deprecated in an earlier minor release.
  * A micro version bump (incrementing the third number) usually only includes bug fixes. Deprecated features will not be dropped in a micro release.


Because of its large user base, even small changes not considered relevant by most users can turn out to be a breaking change for some users in hindsight. Sticking to strict and (almost) always bumping the major version instead of the minor version does not seem desirable since the minor version will not carry any meaning anymore.
A version constraint without an upper bound such as or will allow updates to any future version of the dependency. This includes major versions breaking backward compatibility.
Once a release of your package is published, you cannot tweak its dependencies anymore in case a dependency breaks BC – you have to do a new release but the previous one stays broken. (Users can still work around the broken dependency by restricting it by themselves.)
To avoid such issues, you can define an upper bound on your constraints, which you can increase in a new release after testing that your package is compatible with the new major version of your dependency.
However, when defining an upper bound, users of your package are not able to update a dependency beyond the upper bound even if it does not break anything and is fully compatible with your package. You have to release a new version of your package with an increased upper-bound first.
If your package is used as a library in other packages, it might be better to avoid upper bounds and thus unnecessary dependency conflicts (unless you already know for sure that the next release of the dependency will break your package). If your package is used as an application, it might be worth defining an upper bound.
. Provided that you are using >= 4, you can use it in combination with the PEP 517 compliant build system provided by Poetry. (With tox 3, you have to set the option.)
can be configured in multiple ways. It depends on what should be the code under test and which dependencies should be installed.
will create an package of the project and uses to install it in a fresh environment. Thus, dependencies are resolved by in the first place. But afterward, we run Poetry, which will install the locked dependencies into the environment.
will not do any install. Poetry installs all the dependencies and the current package in editable mode. Thus, tests are running against the local files and not the built and installed package.
Note that does not forward the environment variables of your current shell session by default. This may cause Poetry to not be able to install dependencies in the environments if you have configured credentials using the system keyring on Linux systems or using environment variables in general. You can use the to forward the required variables explicitly or to forward all of them. Linux systems may require forwarding the variable to allow access to the system keyring, though this may vary between desktop environments.
Be aware that this will cause Poetry to write passwords to plaintext config files. You will need to set the credentials again after changing this setting.
While Poetry automatically creates virtual environments to always work isolated from the global Python installation, there are rare scenarios where the use of a Poetry managed virtual environment is not possible or preferred.
The recommended best practice, including when installing an application within a container, is to make use of a virtual environment. This can also be managed by another tool.
### Why is Poetry telling me that the current project’s supported Python range is not compatible with one or more packages’ Python requirements? 
Unlike , Poetry doesn’t resolve for just the Python in the current environment. Instead, it makes sure that a dependency is resolvable within the given Python version range in .
This means your project aims to be compatible with any Python version >=3.7,<4.0. Whenever you try to add a dependency whose Python requirement doesn’t match the whole range, Poetry will tell you this, e.g.:
```
The current project's supported Python range (>=3.7.0,<4.0.0) is not compatible with some of the required packages Python requirement:
    - scipy requires Python >=3.7,<3.11, so it will not be installable for Python >=3.11,<4.0.0

```

Usually you will want to match the supported Python range of your project with the upper bound of the failing dependency. Alternatively, you can tell Poetry to install this dependency , if you know that it’s not needed in all versions.
If you do not want to set an upper bound in the metadata when building your project, you can omit it in the section and only set it in :
For example, if Poetry builds a distribution for a project that uses a version that is not valid, according to , third party tools will be unable to parse the version correctly.
### Poetry busts my Docker cache because it requires me to COPY my source files in before installing 3rd party dependencies 
By default, running requires you to have your source files present (both the “root” package and any directory path dependencies you might have). This interacts poorly with Docker’s caching mechanisms because any change to a source file will make any layers (subsequent commands in your Dockerfile) re-run. For example, you might have a Dockerfile that looks something like this:
As soon as source file changes, the cache for the layer will be invalidated, which forces all 3rd party dependencies (likely the slowest step out of these) to be installed again if you changed any files in .
```

```

The two key options we are using here are (skips installing the project source) and (skips installing any local directory path dependencies, you can omit this if you don’t have any). .
Poetry’s default HTTP request timeout is 15 seconds, the same as . Similar to , the environment variable can be set to alter this value.
Poetry should seamlessly support both section only configuration as well using the section. This lets you decide when and if you would like to migrate to using the section as .
Due to the nature of this change some manual changes to your file is unavoidable in order start using the section. The following tabs show a transition example. If you wish to retain Poetry’s richer syntax it is recommended that you use dynamic dependencies as described in the second tab below.
```

```

```

```

  * The dependency, in this example was replaced with . However, note that if you need an upper bound on supported Python versions refer to the documentation .




---

## Fonte: https://python-poetry.org/docs/basic-usage

For the basic usage introduction we will be installing , a datetime library. If you have not yet installed Poetry, refer to the chapter.
The file is what is the most important here. This will orchestrate your project and its dependencies. For now, it looks like this:
Poetry assumes your package contains a package with the same name as located in the root of your project. If this is not the case, populate to specify your packages and their locations.
Similarly, the traditional file is replaced by the , , and sections. is additionally implicitly populated by your . For full documentation on the project format, see the of the documentation.
Unlike with other packages, Poetry will not automatically install a python interpreter for you. If you want to run Python files in your package like a script or application, you must python interpreter to run them.
Poetry will require you to explicitly specify what versions of Python you intend to support, and its universal locking will guarantee that your project is installable (and all dependencies claim support for) all supported Python versions. Again, it’s important to remember that – unlike other dependencies – setting a Python version is merely specifying which versions of Python you intend to support.
When you run , you must have access to some version of a Python interpreter that satisfies this constraint available on your system. Poetry will not install a Python interpreter for you.
Instead of creating a new project, Poetry can be used to ‘initialize’ a pre-populated directory. To interactively create a file in directory :
Poetry can be operated in two different modes. The default mode is the , which is the right mode if you want to package your project into an sdist or a wheel and perhaps publish it to a package index. In this mode, some metadata such as and , which are required for packaging, are mandatory. Further, the project itself will be installed in editable mode when running .
In this mode, metadata such as and are optional. Therefore, it is not possible to build a distribution or publish the project to a package index. Further, when running , Poetry does not try to install the project itself, but only its dependencies (same as ).
Poetry uses this information to search for the right set of files in package “repositories” that you register in the section, or on by default.
By default, Poetry creates a virtual environment in . You can change the value by editing the Poetry configuration. Additionally, you can use the configuration variable to create virtual environments within your project directory.
Poetry will detect and respect an existing virtual environment that has been externally activated. This is a powerful mechanism that is intended to be an alternative to Poetry’s built-in, simplified environment management.
To take advantage of this, simply activate a virtual environment using your preferred method or tooling, before running any Poetry commands that expect to manipulate an environment.
To run your script simply use . Likewise if you have command line tools such as or you can run them using .
If managing your own virtual environment externally, you do not need to use since you will, presumably, already have activated that virtual environment and made available the correct python instance. For example, these commands should output the same python path:
In our example, we are requesting the package with the version constraint . This means any version greater or equal to 2.1.0 and less than 3.0.0.
Please read for more in-depth information on versions, how versions relate to each other, and on the different ways you can specify dependencies.
When you specify a dependency in , Poetry first takes the name of the package that you have requested and searches for it in any repository you have registered using the key. If you have not registered any extra repositories, or it does not find a package with that name in the repositories you have specified, it falls back to PyPI.
When Poetry finds the right package, it then attempts to find the best match for the version constraint you have specified.
If you have never run the command before and there is also no file present, Poetry simply resolves all dependencies listed in your file and downloads the latest version of their files.
When Poetry has finished installing, it writes all the packages and their exact versions that it downloaded to the file, locking the project to those specific versions. You should commit the file to your project repo so that all people working on the project are locked to the same versions of dependencies (more below).
This brings us to the second scenario. If there is already a file as well as a file when you run , it means either you ran the command before, or someone else on the project ran the command and committed the file to the project (which is good).
Either way, running when a file is present resolves and installs all dependencies that you listed in , but Poetry uses the exact versions listed in to ensure that the package versions are consistent for everyone working on your project. As a result you will have all dependencies requested by your file, but they may not all be at the very latest available versions (some dependencies listed in the file may have released newer versions since the file was created). This is by design, it ensures that your project does not break because of unexpected changes in dependencies.
Committing this file to VC is important because it will cause anyone who sets up the project to use the exact same versions of the dependencies that you are using. Your CI server, production machines, other developers in your team, everything and everyone runs on the same dependencies, which mitigates the potential for bugs affecting only some parts of the deployments. Even if you develop alone, in six months when reinstalling the project you can feel confident the dependencies installed are still working even if your dependencies released many new versions since then. (See note below about using the update command.)
If you have added the recommended section to your project’s pyproject.toml then you successfully install your project and its dependencies into a virtual environment using a command like . However, pip will not use the lock file to determine dependency versions as the poetry-core build system is intended for library developers (see next section).
Library developers have more to consider. Your users are application developers, and your library will run in a Python environment you don’t control.
The application ignores your library’s lock file. It can use whatever dependency version meets the constraints in your . The application will probably use the latest compatible dependency version. If your library’s falls behind some new dependency version that breaks things for your users, you’re likely to be the last to find out about it.
A simple way to avoid such a scenario is to omit the file. However, by doing so, you sacrifice reproducibility and performance to a certain extent. Without a lockfile, it can be difficult to find the reason for failing tests, because in addition to obvious code changes an unnoticed library update might be the culprit. Further, Poetry will have to lock before installing a dependency if has been omitted. Depending on the number of dependencies, locking may take a significant amount of time.
If you do not want to give up the reproducibility and performance benefits, consider a regular refresh of to stay up-to-date and reduce the risk of sudden breakage for users.
As mentioned above, the file prevents you from automatically getting the latest versions of your dependencies. To update to the latest versions, use the command. This will fetch the latest matching versions (according to your file) and update the lock file with the new versions. (This is equivalent to deleting the file and running again.)


---

## Fonte: https://python-poetry.org/docs/building-extension-modules

While this feature has been around since almost the beginning of the Poetry project and has needed minimal changes, it is still considered unstable. You can participate in the discussions about stabilizing this feature .
Poetry allows a project developer to introduce support for, build and distribute native extensions within their project. In order to achieve this, at the highest level, the following steps are required.
  1. The build dependencies, in this context, refer to those Python packages that are required in order to successfully execute your build script. Common examples include , , , etc., depending on how your extension is built.
You must assume that only Python built-ins are available by default in a build environment. This means, if you need even packages like , it must be explicitly declared.
It is recommended that you consider specifying version constraints to all entries in in order to avoid surprises if one of the packages introduce a breaking change. For example, you can set to to ensure no major version upgrades are used.
If you wish to develop the build script within your project’s virtual environment, then you must also add the dependencies to your project explicitly to a dependency group - the name of which is not important.
  2. The build script can be a free-form Python script that uses any dependency specified in the previous step. This can be named as needed, but be located within the project root directory (or a subdirectory) and also be included in your source distribution. You can see the for inspiration.
The build script is always executed from the project root. And it is expected to move files around to their destinations as expected by Poetry as per your file.
The name of the build script is arbitrary. Common practice has been to name it , however, this is not mandatory. You consider if feasible.
  3. The key takeaway here should be the following. You can refer to the documentation for information on each of the relevant sections.


```

```



Prior to executing the build script, Poetry creates a temporary virtual environment with your project’s active Python version and then installs all dependencies specified under into this environment. It should be noted that no packages will be present in this environment at the time of creation.


---

## Fonte: https://python-poetry.org/docs/cli

To get help from the command-line, simply call to see the complete list of commands, then combined with any of those can give you more information.
  * : Increase the verbosity of messages: “-v” for normal output, “-vv” for more verbose output and “-vvv” for debug.
  * : The working directory for the Poetry command (defaults to the current working directory). All command-line arguments will be resolved relative to the given directory.
  * : Specify another path as the project root. All command-line arguments will be resolved relative to the current working directory or directory specified using option if used.


A package is looked up, by default, only from . You can modify the default source (PyPI); or add and use or .
```

```

If you try to add a package that is already present, you will get an error. However, if you specify a constraint, like above, the dependency will be updated by using the specified constraint.
Alternatively, you can specify it in the file. It means that changes in the local directory will be reflected directly in environment.
The attribute is a Poetry-specific feature, so it is not included in the package distribution metadata. In other words, it is only considered when using Poetry to install the project.
Some shells may treat square braces ( and ) as special characters. It is suggested to always quote arguments containing these characters to prevent unexpected shell expansion.


The command will trigger the build system defined in the file according to . If necessary the build process happens in an isolated environment.


When using , the identifier must be compliant. This is useful for adding build numbers, platform specificities, etc. for private packages.
Local version identifiers SHOULD NOT be used when publishing upstream projects to a public index server, but MAY be used to identify private builds created directly from the project source.
To only remove a specific package from a cache, you have to specify the cache entry in the following form :


The command groups subcommands that are useful for, as the name suggests, debugging issues you might have when using Poetry with your projects.
The command helps when debugging dependency resolution issues. The command attempts to resolve your dependencies and list the chosen packages and versions.
The command is useful when you want to see the supported packaging tags for your project’s active virtual environment. This is useful when Poetry cannot install any known binary distributions for a dependency.
This command does not activate the virtual environment, but only displays the activation command, for more information on how to use this command see .
The command removes virtual environments associated with the project. You can specify multiple Python executables or virtual environment names to remove all matching ones. Alternatively, you can remove all associated virtual environments using the option.
  * : The python executables associated with, or names of the virtual environments which are to be removed. Can be specified multiple times.


  * : The python executable to use. This can be a version number (if not on Windows) or a path to the python binary.


See for information on how to install a plugin. As described in , you can also define in your that the plugin is required for the development of your project:


Normally, you should prefer to to avoid untracked outdated packages. However, if you have set to install dependencies into your system environment, which is discouraged, or to make system site-packages available in your virtual environment, you should use because will normally not work well in these cases.
If there is a file in the current directory, it will use the exact versions from there instead of resolving them. This ensures that everyone using the library will get the same versions of the dependencies.
You can also specify the extras you want installed by passing the option (See for more info). Pass to install all defined extras for a project.
This is mainly useful for caching in CI or when building Docker images. See the for more information on this option.
By default does not compile Python source files to bytecode during installation. This speeds up the installation process, but the first execution may take a little more time because Python then compiles source files to bytecode automatically. If you want to compile source files to bytecode during installation, you can use the option:


By default, packages that have already been added to the lock file before will not be updated. To update all dependencies to the latest available compatible versions, use or , which normally produce the same result. This command is also available as a pre-commit hook. See for more information.
This command will help you kickstart your new Python project by creating a new Poetry project. By default, a layout is chosen.
```

```

  * : Specify the readme file extension. Default is . If you intend to publish to PyPI keep the in mind.




The command shows Python versions available in the environment. This includes both installed and discovered System managed and Poetry managed installations.



Especially on Windows, commands that update or remove packages may be problematic so that other methods for installing plugins and updating Poetry are recommended. See and for more information.
The command installs Poetry plugins and make them available at runtime. Additionally, it can also be used to upgrade Poetry’s own dependencies or inject additional packages into the runtime environment



The command behaves similar to the show command, but working within Poetry’s runtime environment. This lists all packages installed within the Poetry install environment.


```

```

  * : When showing the full list, or a for a single package, display whether they are a direct dependency or required by other packages.


You cannot use the name for a custom repository as it is reserved for use by the default PyPI source. However, you can set the priority of PyPI:
The command makes sure that the project’s environment is in sync with the file. It is similar to but it additionally removes packages that are not tracked in the lock file.
If there is a file in the current directory, it will use the exact versions from there instead of resolving them. This ensures that everyone using the library will get the same versions of the dependencies.
You can also specify the extras you want installed by passing the option (See for more info). Pass to install all defined extras for a project.
This is mainly useful for caching in CI or when building Docker images. See the for more information on this option.
By default does not compile Python source files to bytecode during installation. This speeds up the installation process, but the first execution may take a little more time because Python then compiles source files to bytecode automatically. If you want to compile source files to bytecode during installation, you can use the option:


Note that this will not update versions for dependencies outside their specified in the file. In other terms, will be a no-op if the version constraint specified for is or and is available. In order for to be updated, you must update the constraint, for example . You can do this using the command.


This command shows the current version of the project or bumps the version of the project and writes the new version back to if a valid bump rule is provided.


---

## Fonte: https://python-poetry.org/docs/configuration

Poetry can be configured via the command () or directly in the file that will be automatically created when you first run that command. This file can typically be found in one of the following directories:
Sometimes, in particular when using Poetry with CI tools, it’s easier to use environment variables and not have to execute configuration commands.
The environment variables must be prefixed by and are comprised of the uppercase name of the setting and with dots and dashes replaced by underscore, here is an example:
If Poetry renames or remove config options it might be necessary to migrate explicit set options. This is possible by running:
Set the maximum number of workers while using the parallel installer. The is determined by . If this raises a exception, is assumed to be 1.
If this configuration parameter is set to a value greater than , the number of maximum workers is still limited at .
When set, this configuration allows users to disallow the use of binary distribution format for all, none or specific packages.
As with all configurations described here, this is a user specific configuration. This means that this is not taken into consideration when a lockfile is generated or dependencies are resolved. This is applied only when selecting which distribution for dependency should be installed into a Poetry managed environment.
Unless this is required system-wide, if configured globally, you could encounter slower install times across all your projects if incorrectly set.
Configure to be passed to a package’s build backend if it has to be built from a directory or vcs source; or a source distribution during installation.
This is only used when a compatible binary distribution (wheel) is not available for a package. This can be used along with option to force a build with these configurations when a dependency of your project with the specified name is being installed.
Poetry does not offer a similar option in the file as these are, in majority of cases, not universal and vary depending on the target installation environment.
If you want to use a project specific configuration it is recommended that this configuration be set locally, in your project’s file.
Set the maximum number of retries in an unstable network. This setting has no effect if the server does not support HTTP range requests.
If the config option is set and the lock file is at least version 2.1 (created by Poetry 2.0 or above), the installer will not re-resolve dependencies but evaluate the locked markers to decide which of the locked dependencies have to be installed into the target environment.
Do not download entire wheels to extract metadata but use to only download the METADATA files of wheels. Especially with slow network connections, this setting can speed up dependency resolution significantly. If the cache has already been filled or the server does not support HTTP range requests, this setting makes no difference.
If set to , Poetry will not create a new virtual environment. If it detects an already enabled virtual environment or an existing one in or it will install dependencies into them, otherwise it will install dependencies into the systems python environment.
If Poetry detects it’s running within an activated virtual environment, it will never create a new virtual environment, regardless of the value set for .
Be aware that installing dependencies into the system environment likely upgrade or uninstall existing packages and thus break other applications. Installing additional Python packages after installing the project might break the Poetry project in return.
This is why it is recommended to always create a virtual environment. This is also true in Docker containers, as they might contain additional Python packages as well.
If set to , the virtualenv will be created and expected in a folder named within the root directory of the project.
If a virtual environment has already been created for the project under , setting this variable to will not cause to create or use a local virtual environment.
In order for this setting to take effect for a project already in that state, you must delete the virtual environment folder located in .
You can find out where the current project’s virtual environment (if there is one) is stored with the command .
If set to the parameter is passed to on creation of the virtual environment, so that all needed files are copied into it instead of symlinked.
If set to the parameter is passed to on creation of the virtual environment. This means when a new virtual environment is created, will not be installed in the environment.
Poetry, for its internal operations, uses the wheel embedded in the package installed as a dependency in Poetry’s runtime environment. If a user runs when this option is set to , the the embedded instance of is used.
You can safely set this to , if you desire a virtual environment with no additional packages. This is desirable for production environments.
This setting controls the global virtual environment storage path. It most likely will not be useful at the local level. To store virtual environments in the project root, see .
By default, Poetry will use the activated Python version to create a new virtual environment. If set to , the Python version used during Poetry installation is used.


---

## Fonte: https://python-poetry.org/docs/contributing

The following is a set of guidelines for contributing to Poetry on GitHub. These are mostly guidelines, not rules. Use your best judgement, and feel free to propose changes to this document in a pull request.
This section guides you through submitting a bug report for Poetry. Following these guidelines helps maintainers and the community understands your report, reproduces the behavior, and finds related reports.


If you find a issue that seems like it is the same thing that you’re experiencing, open a new issue and include a link to the original issue in the body of your new one.


  * . This could be an example repository, a sequence of steps run in a container, or just a pyproject.toml for very simple cases.
  * If so, provide details about how often the problem happens and under which conditions it normally happens.


  * If the problem started happening recently, What’s the most recent version in which the problem does not happen?
  * This could include use of special container images, newer CPU architectures like Apple Silicon, or corporate proxies that intercept or modify your network traffic.



To give others the best chance to understand and reproduce your issue, please be sure to put extra effort into your reproduction steps. You can both rule out local configuration issues on your end, and ensure others can cleanly reproduce your issue if attempt all reproductions in a pristine container (or VM), and provide the steps you performed inside that container/VM in your issue report.
This section guides you through submitting an enhancement suggestion for Poetry, including completely new features as well as improvements to existing functionality. Following these guidelines helps maintainers and the community understand your suggestion and find related suggestions.


One of the simplest ways to get started contributing to a project is through improving documentation. Poetry is constantly evolving, and this means that sometimes our documentation has gaps. You can help by adding missing sections, editing the existing content to be more accessible, or creating new content such as tutorials, FAQs, etc.
Issues pertaining to the documentation are usually marked with the , which will also trigger a preview of the changes as rendered by this website.
If you are a first time contributor, and are looking for an issue to take on, you might want to look for at the for candidates. We do our best to curate good issues for first-time contributors there, but do fall behind – so if you don’t see anything good, feel free to ask.
If you would like to take on an issue, feel free to comment on the issue tagging . We are more than happy to discuss solutions on the issue. If you would like help with navigating the code base, are looking for something to work on, or want feedback on a design or change, join us on our or start a .
You should first fork the Poetry repository and then clone it locally, so that you can make pull requests against the project. If you are new to Git and pull request-based development, GitHub provides a you will find helpful.
When you contribute to Poetry, automated tools will be run to make sure your code is suitable to be merged. Besides pytest, you will need to make sure your code typechecks properly using :
Finally, a great deal of linting tools are run on your code, to try and ensure consistent code style and root out common mistakes. The tool is used to install and run these tools, and requires one-time setup:
pre-commit will now run and check your code every time you make a commit. By default, it will only run on changed files, but you can run it on all files manually (this may be useful if you altered the pre-commit config):
  * Fill out the pull request body completely and describe your changes as accurately as possible. The pull request body should be kept up to date as it will usually form the base for the final merge commit and the changelog entry.
  * Be sure that your pull request contains tests that cover the changed or added code. Tests are generally required for code be to be considered mergeable, and code without passing tests will not be merged.
  * Ensure your pull request passes the mypy and pre-commit checks. Remember that you can run these tools locally instead of relying on remote CI.
  * If your changes warrant a documentation change, the pull request must also update the documentation. Make sure to review the documentation preview generated by CI for any rendering issues.


Make sure your branch is against the latest base branch. A maintainer might ask you to ensure the branch is up-to-date prior to merging your pull request (especially if there have been CI changes on the base branch), and will also ask you to fix any conflicts.
All pull requests, unless otherwise instructed, need to be first accepted into the branch. Maintainers will generally decide if any backports to other branches are required, and carry them out as needed.
If you have an issue that hasn’t had any attention, you can ping us on the issue. Please give us reasonable time to get to your issue first, and avoid pinging any individuals directly, especially if they are not part of the Poetry team.
If you are helping with the triage of reported issues, this section provides some useful information to assist you in your contribution.
  1. Determine what area and versions of Poetry the issue is related to, and set the appropriate labels (e.g. , , ), and remove the label.
  2. If requested information (such as debug logs, pyproject.toml, etc.) is not provided and is relevant, request it from the author. 
  3. Ensure the issue is not already resolved. Try reproducing it on the latest stable release, the latest prerelease (if present), and the development branch.
  4. If the issue cannot be reproduced, 
  5. If the issue can be reproduced, 


When trying to reproduce issues, you often want to use multiple versions of Poetry at the same time. makes this easy to do:
```

```



---

## Fonte: https://python-poetry.org/docs/pyproject

In package mode, the only required fields are and (either in the section or in the section). Other fields are optional. In non-package mode, the and fields are required if using the section.
If you want to set the version dynamically via or you are using a plugin, which sets the version dynamically, you should add to dynamic and define the base version in the section, for example:
Specifying license as a table, e.g. is deprecated. If you used to specify a license file, e.g. , use instead.
A list of glob patterns that match the license files of the package relative to the root of the project source tree.
If you need an upper bound for locking, but do not want to define an upper bound in your package metadata, you can omit the upper bound in the field and add it in the section.
Poetry supports arbitrary plugins, which are exposed as the ecosystem-standard and discoverable using . This is similar to (and compatible with) the entry points feature of . The syntax for registering a plugin is:


If you do not want to set the version dynamically via and you are not using a plugin, which sets the version dynamically, prefer over this setting.
This is a list of authors and should contain at least one author. Authors must be in the form .
This is a list of maintainers and should be distinct from authors. Maintainers may contain an email and be in the form .
The file(s) can be of any format, but if you intend to publish to PyPI keep the in mind. README paths are implicitly relative to .
To be specific, you can set for on macOS and Windows, but Linux users can’t after cloning your repo. This is because macOS and Windows are case-insensitive and case-preserving.
The contents of the README file(s) are used to populate the of your distribution’s metadata (similar to in setuptools). When multiple files are specified they are concatenated with newlines.
If your project structure differs from the standard one supported by , you can specify the packages you want to include in the final distribution.
The parameter is designed to specify the relative destination path where the package will be located upon installation. This allows for greater control over the organization of packages within your project’s structure.
For instance, if you have a package named and you want to also include another package named , you will need to specify explicitly:
You can explicitly specify to Poetry that a set of globs should be ignored or included for the purposes of packaging. The globs specified in the exclude field identify a set of files that are not included when a package is built. has priority over .
When a wheel is installed, its includes are unpacked straight into the directory. Pay attention to include top level files and directories with common names like , , or only in sdists and in wheels.
If a VCS is being used for a package, the exclude field will be seeded with the VCS’ ignore settings ( for git, for example).
Poetry is configured to look for dependencies on by default. Only the name and a version string are required in this case.
If you specify the compatible python versions in both and in , then Poetry will use the information in for locking, but the python versions must be a subset of those allowed by .
For example, the following is invalid and will result in an error, because versions and greater are allowed by , but not by .
See for a more in-depth look at how to manage dependency groups and for more information on other keys and specifying version ranges.
This tells Poetry to include the specified file, relative to your project directory, in distribution builds. It will then be copied to the appropriate installation directory for your operating system when your package is installed.
In its table form, the value of each script can contain a and . The supported types are and . When the value is a string, it is inferred to be a script.
```

```

Any extras you don’t specify will be removed. Note this behavior is different from not selected for installation, e.g., those not specified via .
Note that and the variations mentioned above (, , etc.) only work on dependencies defined in the current project. If you want to install extras defined by dependencies, you’ll have to express that in the dependency itself:
Poetry supports arbitrary plugins, which are exposed as the ecosystem-standard and discoverable using . This is similar to (and compatible with) the entry points feature of . The syntax for registering a plugin is:


A constraint for the Poetry version that is required for this project. If you are using a Poetry version that is not allowed by this constraint, an error will be raised.
Poetry is compliant with PEP-517, by providing a lightweight core library, so if you use Poetry to manage your Python project, you should reference it in the section of the file like so:


---

## Fonte: https://python-poetry.org/docs/pre-commit-hooks

If you specify the for a hook in your , the defaults are overwritten. You must fully specify all arguments for your hook if you make use of .
The hook calls the command to make sure all locked packages are installed. In order to install this hook, you either need to specify , or you have to install it via .
Poetry follows a branching strategy where the default branch is the active development branch, and fixes get backported to stable branches. New tags are assigned in these stable branches.
does not support such a branching strategy and has decided to not implement an option, either on the or the , to define a branch for looking up the latest available tag.
You can avoid changing the to an unexpected value by using the parameter (may be specified multiple times), to explicitly list repositories that should be updated. An option to explicitly exclude repositories into .
Since can be used as a pre-commit hook itself, the easiest way to make use of it would be to include it inside :


---

## Fonte: https://python-poetry.org/docs/managing-dependencies

Poetry supports specifying main dependencies in the section of your according to PEP 621. For legacy reasons and to define additional information that are only used by Poetry the sections can be used.
To declare a new dependency group, use a section according to PEP 735 or a section where is the name of your dependency group (for instance, ):
All dependencies across groups since they will be resolved regardless of whether they are required for installation or not (see ).
Think of dependency groups as associated with your dependencies: they don’t have any bearings on whether their dependencies will be resolved and installed , they are simply a way to organize the dependencies logically.
Dependency groups, other than the implicit group, must only contain dependencies you need in your development process. To declare a set of dependencies, which add additional functionality to the project during runtime, use instead.
A dependency group can be declared as optional. This makes sense when you have a group of dependencies that are only required in a particular environment or for a specific purpose.
Optional group dependencies will be resolved alongside other dependencies, so special care should be taken to ensure they are compatible with each other.
You can include dependencies from one group in another group. This is useful when you want to aggregate dependencies from multiple groups into a single group.
The default set of dependencies for a project includes the implicit group as well as all groups that are not explicitly marked as an .
Finally, in some case you might want to install of dependencies without installing the default set of dependencies. For that purpose, you can use the option.
Poetry supports what’s called dependency synchronization. Dependency synchronization ensures that the locked dependencies in the file are the only ones present in the environment, removing anything that’s not necessary.
The command can be combined with any related options to synchronize the environment with specific groups. Note that extras are separate. Any extras not selected for install are always removed.
When using the command without the option, you can install any subset of optional groups without removing those that are already installed. This is very useful, for example, in multi-stage Docker builds, where you run multiple times in different build stages.


---

## Fonte: https://python-poetry.org/docs/plugins

For example if your environment poses special requirements on the behaviour of Poetry which do not apply to the majority of its users or if you wish to accomplish something with Poetry in a way that is not desired by most users.
A plugin is a regular Python package which ships its code as part of the package and may also depend on further packages.
The method of the plugin is called after the plugin is loaded and receives an instance of as well as an instance of .
Using these two objects all configuration can be read and all public internal objects and state can be manipulated as desired.
However, it is recommended to register a new factory in the command loader to defer the loading of the command when it’s actually called.


Let’s see how to implement an application event handler. For this example we will see how to load environment variables from a file before executing a command.
The binary in Poetry’s virtual environment can also be used to install and remove plugins. The environment variable here is used to represent the path to the virtual environment. The can be referenced if you are not sure where Poetry has been installed.
The command will ensure that the plugin is compatible with the current version of Poetry and install the needed packages for the plugin to work.
If the plugin is not installed in Poetry’s own environment when running , it will be installed only for the current project under in the project’s directory.
You can even overwrite a plugin in Poetry’s own environment with another version. However, if a plugin’s dependencies are not compatible with packages in Poetry’s own environment, installation will fail.
When writing a plugin, you will probably access internals of Poetry, since there is no stable public API. Although we try our best to deprecate methods first, before removing them, sometimes the signature of an internal method has to be changed.
As the author of a plugin, you are probably testing your plugin against the latest release of Poetry. Additionally, you should consider testing against the latest release branch and the main branch of Poetry and schedule a CI job that runs regularly even if you did not make any changes to your plugin. This way, you will notice internal changes that break your plugin immediately and can prepare for the next Poetry release.


---

## Fonte: https://python-poetry.org/docs/managing-environments

What this means is that it will always work isolated from your global Python installation. To achieve this, it will first check if it’s currently running inside a virtual environment. If it is, it will use it directly without creating a new one. But if it’s not, it will use one that it has already created or create a brand new one for you.
By default, Poetry will try to use the Python version used during Poetry’s installation to create the virtual environment for the current project.
However, for various reasons, this Python version might not be compatible with the range supported by the project. In this case, Poetry will try to find one that is and use it. If it’s unable to do so then you will be prompted to activate one explicitly, see .
If you use a tool like to manage different Python versions, you can switch the current of your shell and Poetry will use it to create the new environment.
Sometimes this might not be feasible for your system, especially Windows where is not available, or you simply prefer to have a more explicit control over your environment. For this specific purpose, you can use the command to tell Poetry which Python version to use for the current project.
If you want to disable the explicitly activated virtual environment, you can use the special Python version to retrieve the default behavior:
The command prints the activate command of the virtual environment to the console. You can run the output command manually or feed it to the eval command of your shell to activate the environment. This way you won’t leave the current shell.
```

```

If you only want to know the path to the python executable (useful for running mypy from a global environment without installing it in the virtual environment), you can pass the option to :


---

## Fonte: https://python-poetry.org/docs/dependency-specification

Dependencies for a project can be specified in various forms, which depend on the type of the dependency and on the optional constraints that might be needed for it to be installed.
In many cases, can be replaced with . However, there are some cases where you might still need to use . For example, if you want to define additional information that is not required for building but only for locking (for example, an explicit source), you can enrich dependency information in the section.
Alternatively, you can add to and define your dependencies completely in the section. Using only the section might make sense in non-package mode when you will not build an sdist or a wheel.
specify a minimal version with the ability to update to later versions of the same level. For example, if you specify a major, minor, and patch version, only patch-level changes are allowed. If you only specify a major, and minor version, then minor- and patch-level changes are allowed.
This will tell Poetry to install this version and this version only. If other dependencies require a different version, the solver will ultimately fail and abort any installation or update procedures.
allow compatible updates to a specified version. An update is allowed if the new version number does not modify the left-most non-zero digit in the major, minor, patch grouping. For instance, if we previously ran and wanted to update the library and ran , poetry would update us to version if it was available, but would not update us to . If instead, we had specified the version string as , poetry would update to but not . is not considered compatible with any other version.
specify a minimal version with some ability to update. If you specify a major, minor, and patch version or only a major and minor version, only patch-level changes are allowed. If you only specify a major version, then minor- and patch-level changes are allowed.
When adding dependencies via , you can use the operator. This is understood similarly to the syntax, but also allows prefixing any specifiers that are valid in . For example:
To depend on a library located in a repository, the minimum information you need to specify is the location of the repository:
Since we haven’t specified any other information, Poetry assumes that we intend to use the latest commit on the branch to build our project.
```

```

We fall back to legacy system git client implementation in cases where is used. This fallback will be removed in a future release where helpers can be better supported natively.
In cases where you encounter issues with the default implementation, you may wish to explicitly configure the use of the system git client via a shell subprocess call.
Keep in mind that all combinations of possible extras available in your project need to be compatible with each other. This means that in order to use differing or incompatible versions across different combinations, you need to make your extra markers . For example, the following installs PyTorch from one source repository with CPU versions when the extra is specified, while the other installs from another repository with a separate version set for GPUs when the extra specified:
For the CPU case, we have to specify because the version specified is not compatible with the GPU () version.
Let’s say you have a dependency on the package which is only compatible with Python 3.6–3.7 up to version 1.9, and compatible with Python 3.8+ from version 2.0: you would declare it like so:
Direct origin (/ / ) dependencies can satisfy the requirement of a dependency that doesn’t explicitly specify a source, even when mutually exclusive markers are used. For instance, in the following example, the url package will also be a valid solution for the second requirement:
Sometimes you may instead want to use a direct origin dependency for specific conditions (i.e., a compiled package that is not available on PyPI for a certain platform/architecture) while falling back on source repositories in other cases. In this case you should explicitly ask for your dependency to be satisfied by another . For example:
In the case of more complex dependency specifications, you may find that you end up with lines which are very long and difficult to read. In these cases, you can shift from using “inline table” syntax to the “standard table” syntax.
As a single line, this is a lot to digest. To make this a bit easier to work with, you can do the following:
The same information is still present, and ends up providing the exact same specification. It’s simply split into multiple, slightly more readable, lines.
Per default, Poetry will prefer stable releases and only choose a pre-release if no stable release satisfies a version constraint. In some cases, this may result in a solution containing pre-releases even if another solution without pre-releases exists.
If you want to disallow pre-releases for a specific dependency, you can set to . In this case, dependency resolution will fail if there is no solution without choosing a pre-release.
If you want to prefer the latest version of a dependency even if it is a pre-release, you can set to so that Poetry makes no distinction between stable and pre-release versions during dependency resolution.


---

## Fonte: https://python-poetry.org/docs/main

Poetry is a tool for and in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you. Poetry offers a lockfile to ensure repeatable installs, and can build your project for distribution.
Poetry requires . It is multi-platform and the goal is to make it work equally well on Linux, macOS and Windows.
If you are viewing documentation for the development branch, you may wish to install a preview or development version of Poetry. See the installation instructions to use a preview or alternate version of Poetry.
is used to install Python CLI applications globally while still isolating them in virtual environments. will manage upgrades and uninstalls when used to install Poetry.
  1. If is not already installed, you can follow any of the options in the . Any non-ancient version of will do.
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, having multiple versions installed at the same time etc.
can also install versions of Poetry in parallel, which allows for easy testing of alternate or prerelease versions. Each version is given a unique, user-specified suffix, which will be used to create a unique binary name:
Finally, can install any valid , which allows for installations of the development version from , or even for local testing of pull requests:


We provide a custom installer that will install Poetry in a new virtual environment and allows Poetry to manage its own environment.
  1. The installer script is available directly at , and is developed in . The script can be executed directly (i.e. ‘curl python’) or downloaded and then executed from disk (e.g. in a CI environment).
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, using a pre-release build, configuring a different installation location etc.
If you want to install prerelease versions, you can do so by passing the option to the installation script or by using the environment variable:
If you want to install different versions of Poetry in parallel, a good approach is the installation with pipx and suffix.
  3.   4.   5.   6. If you decide Poetry isn’t your thing, you can completely remove it from your system by running the installer again with the option or by setting the environment variable before executing the installer.


Poetry can be installed manually using and the module. By doing so you will essentially perform the steps carried out by the official installer. As this is an advanced installation method, these instructions are Unix-only and omit specific examples such as installing from .
Unlike development environments, where making use of the latest tools is desirable, in a CI environment reproducibility should be made the priority. Here are some suggestions for installing Poetry in such an environment.
Whatever method you use, it is highly recommended to explicitly control the version of Poetry used, so that you are able to upgrade after performing your own validation. Each install method has a different syntax for setting the version that is used in the following examples.
Just as is a powerful tool for development use, it is equally useful in a CI environment and should be one of your top choices for use of Poetry in CI.
The official installer script () offers a streamlined and simplified installation of Poetry, sufficient for developer use or for simple pipelines. However, in a CI environment the other two supported installation methods (pipx and manual) should be seriously considered.
Downloading a copy of the installer script to a place accessible by your CI pipelines (or maintaining a copy of the ) is strongly suggested, to ensure your pipeline’s stability and to maintain control over what code is executed.
By default, the installer will install to a user-specific directory. In more complex pipelines that may make accessing Poetry difficult (especially in cases like multi-stage container builds). It is highly suggested to make use of when using the official installer in CI, as that way the exact paths can be controlled.
For maximum control in your CI environment, installation with is fully supported and something you should consider. While this requires more explicit commands and knowledge of Python packaging from you, it in return offers the best debugging experience, and leaves you subject to the fewest external tools.
If you install Poetry via , ensure you have Poetry installed into an isolated environment that is as the target environment managed by Poetry. If Poetry and your project are installed into the same environment, Poetry is likely to upgrade or uninstall its own dependencies (causing hard-to-debug and understand errors).
Poetry should always be installed in a dedicated virtual environment to isolate it from the rest of your system. Each of the above described installation methods ensures that. It should in no case be installed in the environment of the project that is to be managed by Poetry. This ensures that Poetry’s own dependencies will not be accidentally upgraded or uninstalled. In addition, the isolated virtual environment in which poetry is installed should not be activated for running poetry commands.


---

## Fonte: https://python-poetry.org/docs

Poetry is a tool for and in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you. Poetry offers a lockfile to ensure repeatable installs, and can build your project for distribution.
Poetry requires . It is multi-platform and the goal is to make it work equally well on Linux, macOS and Windows.
If you are viewing documentation for the development branch, you may wish to install a preview or development version of Poetry. See the installation instructions to use a preview or alternate version of Poetry.
is used to install Python CLI applications globally while still isolating them in virtual environments. will manage upgrades and uninstalls when used to install Poetry.
  1. If is not already installed, you can follow any of the options in the . Any non-ancient version of will do.
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, having multiple versions installed at the same time etc.
can also install versions of Poetry in parallel, which allows for easy testing of alternate or prerelease versions. Each version is given a unique, user-specified suffix, which will be used to create a unique binary name:
Finally, can install any valid , which allows for installations of the development version from , or even for local testing of pull requests:


We provide a custom installer that will install Poetry in a new virtual environment and allows Poetry to manage its own environment.
  1. The installer script is available directly at , and is developed in . The script can be executed directly (i.e. ‘curl python’) or downloaded and then executed from disk (e.g. in a CI environment).
  2. You can skip this step, if you simply want the latest version and already installed Poetry as described in the previous step. This step details advanced usages of this installation method. For example, installing Poetry from source, using a pre-release build, configuring a different installation location etc.
If you want to install prerelease versions, you can do so by passing the option to the installation script or by using the environment variable:
If you want to install different versions of Poetry in parallel, a good approach is the installation with pipx and suffix.
  3.   4.   5.   6. If you decide Poetry isn’t your thing, you can completely remove it from your system by running the installer again with the option or by setting the environment variable before executing the installer.


Poetry can be installed manually using and the module. By doing so you will essentially perform the steps carried out by the official installer. As this is an advanced installation method, these instructions are Unix-only and omit specific examples such as installing from .
Unlike development environments, where making use of the latest tools is desirable, in a CI environment reproducibility should be made the priority. Here are some suggestions for installing Poetry in such an environment.
Whatever method you use, it is highly recommended to explicitly control the version of Poetry used, so that you are able to upgrade after performing your own validation. Each install method has a different syntax for setting the version that is used in the following examples.
Just as is a powerful tool for development use, it is equally useful in a CI environment and should be one of your top choices for use of Poetry in CI.
The official installer script () offers a streamlined and simplified installation of Poetry, sufficient for developer use or for simple pipelines. However, in a CI environment the other two supported installation methods (pipx and manual) should be seriously considered.
Downloading a copy of the installer script to a place accessible by your CI pipelines (or maintaining a copy of the ) is strongly suggested, to ensure your pipeline’s stability and to maintain control over what code is executed.
By default, the installer will install to a user-specific directory. In more complex pipelines that may make accessing Poetry difficult (especially in cases like multi-stage container builds). It is highly suggested to make use of when using the official installer in CI, as that way the exact paths can be controlled.
For maximum control in your CI environment, installation with is fully supported and something you should consider. While this requires more explicit commands and knowledge of Python packaging from you, it in return offers the best debugging experience, and leaves you subject to the fewest external tools.
If you install Poetry via , ensure you have Poetry installed into an isolated environment that is as the target environment managed by Poetry. If Poetry and your project are installed into the same environment, Poetry is likely to upgrade or uninstall its own dependencies (causing hard-to-debug and understand errors).
Poetry should always be installed in a dedicated virtual environment to isolate it from the rest of your system. Each of the above described installation methods ensures that. It should in no case be installed in the environment of the project that is to be managed by Poetry. This ensures that Poetry’s own dependencies will not be accidentally upgraded or uninstalled. In addition, the isolated virtual environment in which poetry is installed should not be activated for running poetry commands.


---

## Fonte: https://python-poetry.org/history




  * Fix an issue where a dependency that was required for a specific Python version was not installed into an environment of a pre-release Python version ().






  * Fix an issue where the option did not work if a plugin, which accesses the poetry instance during its activation, was installed ().
  * Fix an issue where printed additional information to stdout instead of stderr so that the output could not be used as designed ().


  * Fix an issue where optional dependencies defined in the section were treated as non-optional when a source was defined for them in the section ().





  * Fix an issue where building a dependency from source failed because of a conflict between build-system dependencies that were not required for the target environment ().
  * Fix an issue where installation failed with a permission error when using the system environment as a user without write access to system site packages ().
  * Fix an issue where a version of a dependency that is not compatible with the project’s python constraint was locked. ().
  * Fix an issue where Poetry wrongly reported that the current project’s supported Python range is not compatible with some of the required packages Python requirement ().
  * Fix an issue where the requested extras of a dependency were ignored if the same dependency (with same extras) was specified in multiple groups ().



  * Fix an issue where optional dependencies that are not part of an extra were included in the wheel metadata ().







  * Fix an issue where locking packages with a digit at the end of the name and non-standard sdist names failed ().
  * Fix an issue where installing multiple dependencies from the same git repository failed sporadically due to a race condition ().
  * Fix an issue where the wrong environment was used for checking if an installed package is from system site packages ().
  * Fix an issue where tried to uninstall system site packages if the virtual environment was created with ().







  * Fix an issue where the hash of a metadata file could not be calculated correctly due to an encoding issue ().
  * Fix an issue where a hint to non-package mode was not compliant with the final name of the setting ().





  * Fix an issue where metadata of sdists that call CLI tools of their build requirements could not be determined ().



  * Fix an issue where the project’s directory was not recognized as git repository on Windows due to an encoding issue ().





  * Fix an issue where a cryptic error message is printed if there is no metadata entry in the lockfile ().







  * Fix an issue where did not respect the source if the same version of a package has been locked from different sources ().








  * Fix an issue where an unclear error message is printed if the project name is the same as one of its dependencies ().




  * When trying to install wheels with invalid files, Poetry does not fail anymore but only prints a warning. This mitigates an unintended change introduced in Poetry 1.4.1 ().


  * Fix an issue where Poetry could freeze when building a project with a build script if it generated enough output to fill the OS pipe buffer ().





  * Fix an issue where a pre-release of a dependency was chosen even if a stable release fulfilled the constraint (, ).
  * Fix an issue where poetry commands failed due to special characters in the path of the project or virtual environment ().







  * Fix an issue where a package from the wrong source was installed for a multiple-constraints dependency with different sources ().


  * is now raised on version and constraint parsing errors, and includes information on the package that caused the error ().
  * Fix an issue where relative paths were encoded into package requirements, instead of a file:// URL as required by PEP 508 ().



  * Fix an issue where the deprecated JSON API was used to query PyPI for available versions of a package ().
  * Fix an issue where the installation of dependencies failed if pip is a dependency and is updated in parallel to other dependencies ().
  * Fix an issue where invalid constraints, which are ignored, were only reported in a debug message instead of a warning ().



  * Fix an issue where caret constraints of pre-releases with a major version of 0 resulted in an empty version range ().









  * Fixed an issue where neither Python nor a managed venv can be found, when using Python from MS Store ()



: This release fixes a critical issue that prevented hashes from being retrieved when locking dependencies, due to a breaking change on PyPI JSON API (see and for more details).


  * Fixed an issue where dependencies hashes could not be retrieved when locking due to a breaking change on PyPI JSON API ()
  * Fixed an issue where a dependency with non-requested extras could not be installed if it is requested with extras by another dependency ()



  * Fixed an issue where dependencies hashes could not be retrieved when locking due to a breaking change on PyPI JSON API ()




  * Fixed an issue where dependency resolution takes a while because Poetry checks all possible combinations even markers are mutually exclusive ()





  * Poetry now raises an error if the python version in the project environment is no longer compatible with the project ().









: Lock files might need to be regenerated for the first fix below to take effect. You can use to do so the option.






  * Fixed an error in the command when no lock file existed and a verbose flag was passed to the command. ()


  * When using system environments as an unprivileged user, user site and bin directories are created if they do not already exist. ()


  * Fixed locking of nested extra activations. If you were affected by this issue, you will need to regenerate the lock file using . ()




  * Fixed incorrect selection of configured source url when a publish repository url configuration with the same name already exists. ()





  * When running under Python 2.7 on Windows, install command will be limited to one worker to mitigate threading issue ().






  * The lock files are now versioned to ease transitions for lock file format changes, with warnings being displayed on incompatibility detection ().













  * Fixed an error where invalid virtual environments would be silently used. They will not be recreated and a warning will be displayed ().































  * Poetry now attempts to find not only in the directory it was invoked in, but in all its parents up to the root. This allows to run Poetry commands in project subdirectories.















---

