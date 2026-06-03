import argparse
import sys
from loguru import logger
from monitoring.uss_qualifier.reports.obfuscation import ObfuscatorConfig, obfuscate_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Obfuscate test artifacts by anonymizing participant IDs, hostnames, and tokens."
    )
    parser.add_argument(
        "input",
        help="Path to the input folder or .zip file containing test artifacts."
    )
    parser.add_argument(
        "output",
        help="Path where the obfuscated folder or .zip file should be written."
    )
    parser.add_argument(
        "--no-participants",
        action="store_true",
        help="Disable obfuscation of participant IDs."
    )
    parser.add_argument(
        "--no-hostnames",
        action="store_true",
        help="Disable obfuscation of server/hostnames."
    )
    parser.add_argument(
        "--no-tokens",
        action="store_true",
        help="Disable redaction of authorization bearer tokens."
    )

    args = parser.parse_args()

    config = ObfuscatorConfig(
        obfuscate_participants=not args.no_participants,
        obfuscate_hostnames=not args.no_hostnames,
        obfuscate_tokens=not args.no_tokens,
    )

    try:
        logger.info(f"Starting obfuscation of {args.input} to {args.output}")
        obfuscate_artifacts(args.input, args.output, config)
        logger.info("Obfuscation completed successfully.")
        return 0
    except Exception as e:
        logger.exception(f"Obfuscation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
