import argparse

from sqlvalidator import file_formatter

__version__ = "0.0.8"


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="SQL formatting and basic schemaless validation"
    )
    parser.add_argument("SRC", help="input. Either a file or a folder.")
    parser.add_argument(
        "--version", action="version", version="sqlvalidator " + __version__
    )

    format_group = parser.add_mutually_exclusive_group(required=True)
    format_group.add_argument(
        "--check-format",
        action="store_true",
        help=(
            "don't overwrite the files. "
            "Return code 0 means nothing would change. "
            "Return code 1 means some files would be reformatted."
        ),
    )
    format_group.add_argument(
        "--format",
        action="store_true",
        help="format marked SQL queries by overwriting specified files.",
    )

    args = parser.parse_args()
    src_input = args.SRC

    file_formatter.handle_input(
        src_input, format_input=args.format, check_input=args.check_format
    )


if __name__ == "__main__":
    _main()
