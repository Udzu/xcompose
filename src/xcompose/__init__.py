import argparse
import os
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

from pygtrie import Trie  # type: ignore[import-untyped]

LOCALE_DIR = Path("/usr/share/X11/locale/")
KEYSYM_DEF = Path("/usr/include/X11/keysymdef.h")
CONFLICT_MARKERS = ["conflict", "override"]

CHAR_TO_KEYWORD: dict[str, str] = {}
KEYWORD_TO_CHAR: dict[str, str] = {}
KEYSYMS: set[str] = set()

with KEYSYM_DEF.open() as f:
    for line in f:
        if m := re.match(r"#define XK_([^ ]+)\s.*U[+]([0-9A-Fa-f]{4,6})", line):
            key, code = m.groups()
            char = chr(int(code, base=16))
            CHAR_TO_KEYWORD.setdefault(char, key)
            KEYWORD_TO_CHAR.setdefault(key, char)
        if m := re.match(r"#define XK_([^ ]+)\s", line):
            KEYSYMS.add(m.group(1))


def get_system_xcompose_name(lang: str | None = None) -> str:
    """Get system compose file name for current LANG"""
    lang = os.environ["LANG"] if lang is None else lang
    for line in (LOCALE_DIR / "compose.dir").read_text().splitlines():
        if (m := re.match(r"([^#]*):\s*(.*)", line)) is not None:
            file, locale = m.groups()
            if locale.strip() == lang:
                return file
    raise RuntimeError(f"Not found system compose file for {lang}")


def get_xcompose_path(system: bool = False) -> Path:
    """Get compose file path"""
    if not system:
        if (xc_env := os.environ.get("XCOMPOSEFILE")) is not None:
            return Path(xc_env)
        if (xc_local := Path.home() / ".XCompose").exists():
            return xc_local
    return LOCALE_DIR / get_system_xcompose_name()


def get_include_path(include: str) -> Path:
    """Expand substitution in an included compose file"""
    if "%H" in include:
        path = include.replace("%H", str(Path.home()))
    elif "%L" in include:
        path = include.replace(
            "%L",
            str(LOCALE_DIR / get_system_xcompose_name()),
        )
    elif "%S" in include:
        path = include.replace("%S", str(LOCALE_DIR))
    else:
        path = include
    return Path(path)


def to_code_point(c: str) -> str:
    """Default Unicode code point formatting for a given character."""
    return f"U{ord(c):04X}"


def from_code_point(code: str) -> str | None:
    """Unicode character represented by a given code point or keysym.
    Supported formats: U#### U+#### 0x#### (with 2 to 6 digits)"""
    if m := re.match(r"(?:U[+]?|0x)([0-9a-fA-F]{2,6})$", code):
        return chr(int(m.group(1), base=16))
    return KEYWORD_TO_CHAR.get(code)


def is_keysym(code: str) -> bool:
    """Whether the given keysym is recognised."""
    return code in KEYSYMS or from_code_point(code) is not None


COMPOSE_KEY = "Multi_key"
ANY_KEY = "ANY"


@dataclass
class Definition:
    # parsed
    keys: Sequence[str]
    value: str
    keysym: str | None
    comment: str | None
    # original
    line: str
    file: Path
    line_no: int


def get_definitions(
    file: Path | None = None,
    ignore_includes: bool = False,
    modifier_key: str | None = COMPOSE_KEY,
    ignore_errors: bool = True,
) -> Iterable[Definition]:
    file = file or get_xcompose_path()
    with file.open() as f:
        for i, line in enumerate(f, 1):
            if re.match(r"^\s*(#.*)?$", line):
                continue
            elif line.startswith("include "):
                if ignore_includes:
                    continue
                include_path = get_include_path(line[8:].strip().strip('"'))
                yield from get_definitions(include_path, modifier_key=modifier_key)
            elif m := re.match(
                r"^\s*(?P<events>(?:<[^>]+>\s*)+):"
                r'\s*"(?P<string>(?:\\"|[^"])+)"'
                r"\s*(?P<keysym>[^#]*[^\s#])?"
                r"\s*(?:#\s*(?P<comment>.+\S)?)?\s*$",
                line,
            ):
                events, string, keysym, comment = m.groups()
                string = string.encode("raw_unicode_escape").decode("unicode_escape")
                keys = tuple(re.findall(r"<([^>]+)>", events))
                if modifier_key is None or keys[0] == modifier_key:
                    yield Definition(
                        keys, string, keysym, comment, line.rstrip("\n"), file, i
                    )
            elif not ignore_errors:
                print(f"[{file}#{i}] Invalid definition:\n{line}")


# Commands


def add(args: argparse.Namespace) -> None:
    """Print line defining a new key sequence"""
    ks = tuple(CHAR_TO_KEYWORD.get(k, k) for k in args.keys)
    if args.modifier_key is not None:
        ks = (args.modifier_key, *ks)

    conflict = None
    for defn in get_definitions(
        args.file or get_xcompose_path(system=args.system),
        ignore_includes=args.ignore_include,
        modifier_key=args.modifier_key,
    ):
        n = min(len(ks), len(defn.keys))
        if ks[:n] == defn.keys[:n] and not (
            ks == defn.keys and args.value == defn.value
        ):
            conflict = defn.value
            break

    keys = " ".join(f"<{k}>" for k in ks)
    codes = " ".join(to_code_point(c) for c in args.value)
    names = " ".join(unicodedata.name(c, "???") for c in args.value)
    if len(args.value) > 1 and "VARIATION SELECTOR-16" in names:
        names = names.replace("VARIATION SELECTOR-16", "EMOJI")
    if conflict:
        names = names + f" (conflicts with {conflict})"
    print(f'{keys} : "{args.value}"  {codes}   # {names}')


def find(args: argparse.Namespace) -> None:
    """Print lines matching given output (either string, keysym or part
    of the comment)"""
    definitions: list[Definition] = []
    for defn in get_definitions(
        args.file or get_xcompose_path(system=args.system),
        ignore_includes=args.ignore_include,
        modifier_key=args.modifier_key,
    ):
        if (
            args.value == defn.value
            or args.value == defn.keysym
            or from_code_point(args.value) == defn.value
            or len(args.value) > 1
            and defn.comment is not None
            and args.value.upper() in defn.comment.upper()
        ):
            if args.sort is None:
                print(defn.line)
            else:
                definitions.append(defn)

    if args.sort is not None:
        _print_sorted(definitions, args.sort)


def get(args: argparse.Namespace) -> None:
    """Print lines matching given key sequence prefix."""
    keys = tuple(CHAR_TO_KEYWORD.get(c, c) for c in args.keys)
    definitions: list[Definition] = []
    for defn in get_definitions(
        args.file or get_xcompose_path(system=args.system),
        ignore_includes=args.ignore_include,
        modifier_key=args.modifier_key,
    ):
        if keys[: len(defn.keys) - 1] == defn.keys[1 : len(keys) + 1]:
            if args.sort is None:
                print(defn.line)
            else:
                definitions.append(defn)

    if args.sort is not None:
        _print_sorted(definitions, args.sort)


def _print_sorted(
    definitions: Sequence[Definition], sort: Literal["value", "keys", "keys_length"]
) -> None:
    if sort == "value":
        definitions = sorted(
            definitions,
            key=lambda d: (d.value, [from_code_point(k) or k for k in d.keys]),
        )
    elif sort == "keys":
        definitions = sorted(
            definitions,
            key=lambda d: ([from_code_point(k) or k for k in d.keys], d.value),
        )
    elif sort == "keys_length":
        definitions = sorted(
            definitions,
            key=lambda d: (
                len(d.keys),
                [from_code_point(k) or k for k in d.keys],
                d.value,
            ),
        )
    print("\n".join(d.line for d in definitions))


def validate(args: argparse.Namespace) -> None:
    """Validate compose file, looking for syntax errors, inconsistencies
    and conflicts."""
    trie = Trie()
    file = args.file or get_xcompose_path(system=args.system)
    for defn in get_definitions(
        file,
        ignore_includes=args.ignore_include,
        modifier_key=args.modifier_key,
        ignore_errors=False,
    ):
        # don't validate the included files (but still parse them for conflicts)
        if defn.file == file:
            expected_keysym = " ".join(to_code_point(c) for c in defn.value)
            try:
                expected_comment = " ".join(unicodedata.name(c) for c in defn.value)
            except ValueError:
                expected_comment = None

            if any(not is_keysym(c) for c in defn.keys):
                keysyms = {c for c in defn.keys if not is_keysym(c)}
                print(
                    f"[{defn.file}#{defn.line_no}] Unrecognised "
                    f"keysym{'' if len(keysyms) == 1 else 's'}: "
                    f"{', '.join(keysyms)}"
                )

            if len(defn.value) == 1:
                if defn.keysym is None:
                    print(
                        f"[{defn.file}#{defn.line_no}] Missing keysym: "
                        f"expected {expected_keysym}"
                    )
                elif from_code_point(defn.keysym) != defn.value:
                    keysym = CHAR_TO_KEYWORD.get(defn.value, None)
                    expected = (
                        f"{keysym} (or {expected_keysym})"
                        if keysym
                        else expected_keysym
                    )
                    print(
                        f"[{defn.file}#{defn.line_no}] "
                        f"Incorrect keysym: {defn.keysym}, expected {expected}"
                    )
            elif defn.keysym and from_code_point(defn.keysym):
                print(
                    f"[{defn.file}#{defn.line_no}] "
                    f"Keysym for just a single character: {defn.keysym}, "
                    f"actually {expected_keysym}"
                )

            if expected_comment:
                if defn.comment is None:
                    print(
                        f"[{defn.file}#{defn.line_no}] Missing comment: "
                        f"expected {expected_comment}"
                    )
                elif len(defn.value) == 1 and expected_comment not in defn.comment:
                    print(
                        f"[{defn.file}#{defn.line_no}] Incorrect comment: "
                        f"{defn.comment}, expected {expected_comment}"
                    )
                elif (
                    len(defn.value) > 1
                    and "\ufe0f" in defn.value
                    and "EMOJI" not in defn.comment.upper()
                ):
                    print(
                        f"[{defn.file}#{defn.line_no}] Missing emoji marker: "
                        f"comment {defn.comment} for {defn.value!r} should "
                        f"include the string EMOJI"
                    )

            # check the trie for conflicts
            kv = (
                next(trie.prefixes(defn.keys), None)
                or trie.has_subtrie(defn.keys)
                and next(trie.iteritems(defn.keys), None)
            )
            if kv and not (kv[0] == defn.keys and kv[1].value == defn.value):
                k, v = kv
                if defn.file == v.file:
                    print(
                        f"[{file}#{defn.line_no}] Compose sequence "
                        f"{' + '.join(defn.keys)} for {defn.value!r} "
                        "conflicts with\n  "
                        f"[...#{v.line_no}] {' + '.join(k)} for {v.value!r}"
                    )
                elif not any(
                    defn.comment is not None and x in defn.comment
                    for x in CONFLICT_MARKERS
                ):
                    print(
                        f"[{file}#{defn.line_no}] Compose sequence "
                        f"{' + '.join(defn.keys)} for {defn.value!r} "
                        "conflicts with \n  "
                        f"[{v.file}#{v.line_no}] {' + '.join(k)} for {v.value!r}\n"
                        "    to ignore this, include the string "
                        "'conflict' or 'override' in the comment"
                    )
            elif not args.ignore_include and any(
                defn.comment is not None and x in defn.comment for x in CONFLICT_MARKERS
            ):
                print(
                    f"[{file}#{defn.line_no}] Compose sequence "
                    f"{' + '.join(defn.keys)} for {defn.value!r} "
                    f"has superfluous conflict/override comment marker"
                )

        trie[defn.keys] = defn


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("""Xcompose sequence helper utility."""),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-f",
        "--file",
        type=Path,
        help="config file to analyze (instead of user config)",
    )
    group.add_argument(
        "-S",
        "--system",
        action="store_true",
        help="analyze system config (instead of user config)",
    )
    parser.add_argument(
        "-i",
        "--ignore-include",
        action="store_true",
        help="don't follow any include declarations in the config",
    )
    parser.add_argument(
        "-k",
        "--key",
        metavar="KEY",
        dest="modifier_key",
        default=COMPOSE_KEY,
        help=f"modifier key keysym (default is {COMPOSE_KEY}; use {ANY_KEY} for all)",
    )
    parser.add_argument(
        "-s",
        "--sort",
        metavar="SORT",
        # dest="modifier_key",
        choices=["keys", "keys_length", "value"],
        default=None,
        help="sort resulting sequences (options: 'keys', 'value')",
    )

    subparsers = parser.add_subparsers(required=True, dest="command")

    parser_add = subparsers.add_parser(
        "add",
        description="Define and print a new compose sequence.",
        help="print a new compose sequence",
    )
    parser_add.add_argument("value", help="string value")
    parser_add.add_argument("keys", nargs="*", help="key sequence")
    parser_add.set_defaults(func=add)

    parser_find = subparsers.add_parser(
        "find",
        description="Find sequences matching given output.",
        help="find sequences matching given output",
    )
    parser_find.add_argument(
        "value", help="output string, keysym, code point or description"
    )
    parser_find.set_defaults(func=find)

    parser_get = subparsers.add_parser(
        "get",
        description="Get sequences matching given key inputs.",
        help="get sequences matching given key inputs",
    )
    parser_get.add_argument("keys", nargs="*", help="key sequence")
    parser_get.set_defaults(func=get)

    parser_validate = subparsers.add_parser(
        "validate",
        description="Search compose config file for inconsistencies, "
        "errors and conflicts.",
        help="validate compose config file",
    )
    parser_validate.set_defaults(func=validate)

    args = parser.parse_args()
    if args.modifier_key == ANY_KEY:
        args.modifier_key = None
    args.func(args)


if __name__ == "__main__":
    main()
