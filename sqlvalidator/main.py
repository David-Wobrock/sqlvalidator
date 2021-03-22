import argparse

from sqlvalidator import file_handler

__version__ = "0.0.15"


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="SQL formatting and basic schemaless validation"
    )
    parser.add_argument("SRC", help="input. Either a file or a folder.", nargs="+")
    parser.add_argument(
        "--version", action="version", version="sqlvalidator " + __version__
    )

    format_group = parser.add_mutually_exclusive_group(required=False)
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

    parser.add_argument("--validate", action="store_true", help="run SQL validation.")

    args = parser.parse_args()
    src_inputs = args.SRC

    if not (args.format or args.check_format or args.validate):
        parser.error(
            "at least one argument should be specified "
            "[--format | --check-format | --validate]"
        )

    file_handler.handle_inputs(
        src_inputs,
        format_input=args.format,
        check_input_format=args.check_format,
        validate_input=args.validate,
    )


if __name__ == "__main__":
    _main()
