"""Put on disk the parts git has to find there.

A wheel lands in a venv, but git looks for hooks in `init.templateDir`,
and every hook it has ever copied addresses the relocator by one
absolute path outside any venv. Installation is therefore a step of its
own: write the template, and point that one public path at whichever
venv this package landed in. Re-run after an upgrade, or after moving
the venv.

Usage: git-localhost-store-install
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .paths import relocator_link, repos_root, template_dir

HOOK = Path(__file__).parent / "hook.sh"

# Quiescent points -- each fires after its operation's own ref-transaction has
# landed, never mid-operation. See CLAUDE.md for why nothing earlier is safe.
TRIGGERS = ("post-index-change", "post-commit", "post-checkout")


def installed_relocator() -> Path:
    """This venv's `git-localhost-store` console script."""
    return Path(sys.executable).parent / "git-localhost-store"


def write_template(hooks: Path) -> None:
    """Install the hook body once, and every trigger as a link to it."""
    hooks.mkdir(parents=True, exist_ok=True)
    shared = hooks / "shared"
    shutil.copyfile(HOOK, shared)
    shared.chmod(0o755)
    for trigger in TRIGGERS:
        link = hooks / trigger
        link.unlink(missing_ok=True)
        link.symlink_to(shared.name)


def write_relocator_link() -> Path:
    """Aim the public path at this venv, replacing any older aim."""
    link = relocator_link()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.unlink(missing_ok=True)
    link.symlink_to(installed_relocator())
    return link


def read_config(name: str) -> str:
    """A global git config value, or empty when unset."""
    return subprocess.run(
        ("git", "config", "--global", "--get", name),
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def write_template_dir(template: Path) -> str:
    """Point `init.templateDir` at our hooks unless it names someone else's.

    git allows exactly one template directory, so a foreign setting is a
    real conflict rather than something to overwrite: the other system's
    hooks would simply stop being installed, silently and everywhere.
    """
    current = read_config("init.templateDir")
    if current and Path(current).expanduser() != template:
        return (
            f"! init.templateDir is {current} -- left alone.\n"
            f"  Merge {template}/hooks/ into it, or repoint it here."
        )
    else:
        subprocess.run(
            ("git", "config", "--global", "init.templateDir", str(template)),
            check=True,
        )
        return f"✓ init.templateDir  {template}"


def main() -> int:
    repos = repos_root()
    repos.mkdir(parents=True, exist_ok=True)
    repos.chmod(0o700)

    template = template_dir()
    write_template(template / "hooks")
    link = write_relocator_link()

    print(f"✓ stores           {repos}")
    print(f"✓ template         {template}")
    print(f"✓ relocator        {link} -> {link.readlink()}")
    print(write_template_dir(template))
    return 0
