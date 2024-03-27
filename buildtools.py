import sys
import pathlib
import logging
import subprocess
import shlex
import os
import shutil
import polib

logging.basicConfig(level=logging.INFO)

locales = (
    "zh_CN",
)

ROOT_DIR = pathlib.Path(__file__).parent
HOVERSET_DIR = ROOT_DIR / "hoverset"
HOVERSET_LOCALE_DIR = HOVERSET_DIR / "data" / "locale"
HOVERSET_PO = HOVERSET_LOCALE_DIR / "hoverset.po"

STUDIO_DIR = ROOT_DIR / "studio"
STUDIO_LOCALE_DIR = STUDIO_DIR / "resources" / "locale"
STUDIO_PO = STUDIO_LOCALE_DIR / "studio.po"


def extract_locale_po(pot_path, locale_dir, source_dir, appname):
    logging.info(f"Extracting locales for {appname}")
    files = " ".join(sorted([str(f.relative_to(ROOT_DIR).as_posix()) for f in source_dir.glob("**/*.py")]))
    base_po = pot_path.relative_to(ROOT_DIR).as_posix()
    cmd = (
        f"xgettext --package-name {appname} -L Python {'--join-existing' if pot_path.exists() else ''} "
        f"--from-code=UTF-8 --keyword=_ --output={base_po} {files}"
    )
    subprocess.run(shlex.split(cmd))

    for locale in locales:
        logging.info(f"Updating locale {locale}")
        po_file = (locale_dir / locale / "LC_MESSAGES" / f"{appname}.po").relative_to(ROOT_DIR).as_posix()

        # Create the po file if it does not exist
        os.makedirs(os.path.dirname(po_file), exist_ok=True)
        if not os.path.exists(po_file):
            # copy the template file
            shutil.copy(base_po, po_file)

        cmd = f"msgmerge --update --verbose {po_file} {base_po}"
        subprocess.run(shlex.split(cmd))


def extract_locales():
    logging.info("Extracting hoverset locales")
    extract_locale_po(
        HOVERSET_PO,
        HOVERSET_LOCALE_DIR,
        HOVERSET_DIR,
        "hoverset"
    )
    logging.info("Extracting studio locales")
    extract_locale_po(
        STUDIO_PO,
        STUDIO_LOCALE_DIR,
        STUDIO_DIR,
        "studio"
    )


def _compile_locales(locale_dir, appname):
    for locale in locales:
        po_file = (locale_dir / locale / "LC_MESSAGES" / f"{appname}.po").relative_to(ROOT_DIR).as_posix()
        mo_file = (locale_dir / locale / "LC_MESSAGES" / f"{appname}.mo").relative_to(ROOT_DIR).as_posix()
        logging.info(f"Compiling {po_file} to {mo_file}")
        cmd = f"msgfmt --verbose -o {mo_file} {po_file}"
        subprocess.run(shlex.split(cmd))


def compile_locales():
    logging.info("Compiling hoverset locales")
    _compile_locales(HOVERSET_LOCALE_DIR, "hoverset")
    logging.info("Compiling studio locales")
    _compile_locales(STUDIO_LOCALE_DIR, "studio")


def decompose_po():
    po = polib.pofile(STUDIO_PO)
    with open("studio-trans.txt", "w") as out:
        for entry in po:
            out.write(f"{entry.msgid}\n\n")

    with open("hoverset-trans.txt", "w") as out:
        po = polib.pofile(HOVERSET_PO)
        for entry in po:
            out.write(f"{entry.msgid}\n\n")


def merge_po():
    pass


if __name__ == "__main__":
    command_map = {
        "extract_locales": extract_locales,
        "extract_lc": extract_locales,
        "compile_locales": compile_locales,
        "compile_lc": compile_locales,
        "decompose_po": decompose_po,
        "merge_po": merge_po,
    }

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            command = command_map.get(arg)
            if command:
                command()
            else:
                print("Unknown command")
