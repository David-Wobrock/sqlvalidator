import argparse

from sqlvalidator import file_handler

__version__ = "0.0.17"


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

    validate_group = parser.add_mutually_exclusive_group(required=False)
    validate_group.add_argument(
        "--validate", action="store_true", help="run SQL validation."
    )
    validate_group.add_argument(
        "--verbose-validate",
        action="store_true",
        help="run SQL validation and display errors.",
    )

    args = parser.parse_args()
    src_inputs = args.SRC

    if not (args.format or args.check_format or args.validate or args.verbose_validate):
        parser.error(
            "at least one argument should be specified "
            "[--format | --check-format | --validate]"
        )

    file_handler.handle_inputs(
        src_inputs,
        format_input=args.format,
        check_input_format=args.check_format,
        validate_input=args.validate,
        verbose_validate_input=args.verbose_validate,
    )


if __name__ == "__main__":
    _main()
