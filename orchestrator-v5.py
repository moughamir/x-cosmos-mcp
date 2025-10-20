#!/usr/bin/env python3
"""
orchestrator.py (streaming orchestrator)

Runs the analyzer then the normalizer. Supports multithreading, tqdm, logs.

Examples:
  python orchestrator.py --analyze --normalize
  python orchestrator.py --analyze --normalize --workers 8 --max-files 1000
  python orchestrator.py --normalize --tag-csv path/to/tag.csv --type-csv path/to/type.csv

"""

import argparse
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Use local module imports (ensure files are in same directory)
try:
    from optimus_v4 import ProductAnalyzer
    from optimus_v4_normalizer import ProductNormalizer
except Exception as e:
    print(f"Failed to import modules: {e}")
    raise


# Basic orchestrator logger
def setup_orch_logger(log_dir: Path):
    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z"
    )
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = TimedRotatingFileHandler(
        str(log_dir / f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        when="midnight",
        backupCount=7,
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate analysis + normalization pipeline"
    )
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--normalize", action="store_true")
    parser.add_argument("--input-folder", default="data/json/products_by_id")
    parser.add_argument("--analysis-output", default="analysis_output")
    parser.add_argument("--normalized-output", default="normalized_output")
    parser.add_argument(
        "--max-files", type=int, help="Limit number of gz files to process"
    )
    parser.add_argument("--analyzer-batch-size", type=int, default=50)
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of threads for normalizer"
    )
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument(
        "--tag-csv", help="If provided, skip analyzer -> use this tag CSV"
    )
    parser.add_argument(
        "--type-csv", help="If provided, skip analyzer -> use this type CSV"
    )

    args = parser.parse_args()

    log_dir = Path("logs")
    logger = setup_orch_logger(log_dir)

    tag_csv = args.tag_csv
    type_csv = args.type_csv

    if args.analyze:
        logger.info("Starting analyzer...")
        analyzer = ProductAnalyzer(
            input_folder=args.input_folder,
            output_dir=args.analysis_output,
        )
        analyzer_res = analyzer.run_analysis(
            max_files=args.max_files, show_progress=not args.no_progress
        )
        tag_csv = analyzer_res.get("tag_csv")
        type_csv = analyzer_res.get("type_csv")
        logger.info(f"Analyzer produced: tag_csv={tag_csv}, type_csv={type_csv}")

    if args.normalize:
        if not tag_csv or not type_csv:
            # attempt to find latest in analysis_output
            ap = Path(args.analysis_output)
            if ap.exists():
                tag_matches = sorted(ap.glob("tag_analysis_*.csv"), reverse=True)
                type_matches = sorted(ap.glob("type_analysis_*.csv"), reverse=True)
                if tag_matches and not tag_csv:
                    tag_csv = str(tag_matches[0])
                if type_matches and not type_csv:
                    type_csv = str(type_matches[0])

        if not tag_csv or not type_csv:
            logger.error(
                "Missing tag/type CSVs. Run --analyze first or provide --tag-csv and --type-csv."
            )
            return

        logger.info(f"Starting normalizer with workers={args.workers}")
        normalizer = ProductNormalizer(
            output_dir=args.normalized_output,
            input_folder=args.input_folder,
        )
        norm_res = normalizer.process_all_stream(
            tag_csv=tag_csv,
            type_csv=type_csv,
            input_folder=args.input_folder,
            workers=args.workers,
            max_files=args.max_files,
            update_supabase=False,
            show_progress=not args.no_progress,
        )
        logger.info(f"Normalizer finished: {norm_res}")

    if not args.analyze and not args.normalize:
        logger.info("Nothing to run. Use --analyze and/or --normalize.")


if __name__ == "__main__":
    main()
