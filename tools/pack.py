"""Builds the port's files from edited models: the reverse of export.py.

Usage: python tools/pack.py UW1_DIR [--force] [--variant NAME] [id ...]
UW1_DIR is your own copy of Ultima Underworld; its colours are read from it, never copied into the repo.
Only models whose files changed since the last export or pack are rebuilt, unless --force is given.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uwmodels import pack  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    force = "--force" in args
    variant = None
    if "--variant" in args:
        k = args.index("--variant")
        variant = args[k + 1]
        del args[k:k + 2]
    args = [a for a in args if a != "--force"]
    try:
        report = pack.run(Path(args[0]), Path("."), args[1:] or None, variant=variant, force=force)
    except pack.PackError as e:
        sys.exit(str(e))
    for line in report:
        print(line)
    print("done" if not report else f"done, {len(report)} notes")
