#!/usr/bin/env python3
"""
orchestrator.py
Simple orchestrator that runs the analyzer then the normalizer.

Usage examples:
  # Run analyzer (disk) then normalizer using CSV outputs
  python orchestrator.py --analyze --normalize --input-folder data/json/products_by_id

  # Run only analyzer
  python orchestrator.py --analyze

  # Run only normalizer (provide tag/type CSVs)
  python orchestrator.py --normalize --tag-csv analysis_output/tag_analysis_...csv --type-csv analysis_output/type_analysis_...csv

Notes:
- By default analyzer will use `--source disk` and read from --input-folder.
- Normalizer will read from disk (same input-folder) unless --source api is specified.
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("orchestrator")

# Import the updated classes
try:
    from optimus_v4 import ProductAnalyzer
    from optimus_v4_normalizer import ProductNormalizer
except Exception as e:
    logger.error(f"Failed to import modules: {e}")
    logger.error(
        "Make sure optimus_v4.py and optimus_v4_normalizer.py are in the same folder as this script."
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Orchestrate analyzer and normalizer")
    parser.add_argument("--analyze", action="store_true", help="Run analyzer")
    parser.add_argument("--normalize", action="store_true", help="Run normalizer")
    parser.add_argument(
        "--input-folder",
        type=str,
        default="data/json/products_by_id",
        help="Input folder for gzipped product JSONs",
    )
    parser.add_argument(
        "--analysis-output",
        type=str,
        default="analysis_output",
        help="Folder where analyzer CSVs are written",
    )
    parser.add_argument(
        "--normalized-output",
        type=str,
        default="normalized_output",
        help="Where to save normalized products",
    )
    parser.add_argument("--limit", type=int, help="Max products to process")
    parser.add_argument(
        "--analyzer-batch-size", type=int, default=50, help="Analyzer batch size"
    )
    parser.add_argument(
        "--normalizer-batch-size", type=int, default=100, help="Normalizer batch size"
    )
    parser.add_argument(
        "--ollama-model", type=str, default="qwen2:0.5b", help="Ollama model"
    )
    parser.add_argument(
        "--ollama-url", type=str, default=None, help="Ollama URL override"
    )
    parser.add_argument(
        "--tag-csv",
        type=str,
        help="If provided, skip analyzer -> use this tag CSV for normalizer",
    )
    parser.add_argument(
        "--type-csv",
        type=str,
        help="If provided, skip analyzer -> use this type CSV for normalizer",
    )

    args = parser.parse_args()

    tag_csv = args.tag_csv
    type_csv = args.type_csv

    # Run analyzer if requested and if CSVs not provided
    if args.analyze:
        analyzer = ProductAnalyzer(
            ollama_model=args.ollama_model,
            output_dir=args.analysis_output,
            input_folder=args.input_folder,
            ollama_url=args.ollama_url,
        )
        res = analyzer.run_analysis(
            source="disk", max_products=args.limit, batch_size=args.analyzer_batch_size
        )
        tag_csv = res.get("tag_csv")
        type_csv = res.get("type_csv")
        logger.info(f"Analyzer produced: tag_csv={tag_csv}, type_csv={type_csv}")

    # If normalization requested, ensure we have CSVs
    if args.normalize:
        if not tag_csv or not type_csv:
            # try to find latest CSVs in analysis_output
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
                "Tag or Type CSV not found. Run analyzer first or provide --tag-csv and --type-csv."
            )
            return

        normalizer = ProductNormalizer(
            output_dir=args.normalized_output,
            input_folder=args.input_folder,
        )

        res = normalizer.process_all(
            tag_csv=tag_csv,
            type_csv=type_csv,
            source="disk",
            input_folder=args.input_folder,
            max_products=args.limit,
            batch_size=args.normalizer_batch_size,
            update_supabase=False,
        )
        logger.info(f"Normalizer finished: {res}")

    if not args.analyze and not args.normalize:
        logger.info("Nothing to do. Use --analyze and/or --normalize.")


if __name__ == "__main__":
    main()
