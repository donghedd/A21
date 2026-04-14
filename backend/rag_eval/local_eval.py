"""Offline local-corpus RAG evaluation entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Optional, Sequence


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from rag_eval.dataset import EvalDataset, write_json  # noqa: E402
from rag_eval.evaluator import RetrievalEvaluator  # noqa: E402
from rag_eval.local_retriever import LocalCorpusRAGService  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline local-corpus RAG retrieval evaluation"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to labeled evaluation dataset JSON",
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Input file or directory for the local corpus. Can be repeated",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional result JSON path. Defaults to <dataset>.local.results.json",
    )
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--min-chunk-size", type=int, default=200)
    parser.add_argument("--min-chars", type=int, default=80)
    parser.add_argument(
        "--disable-markdown-splitter",
        action="store_true",
        help="Disable markdown header splitting",
    )
    parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=None,
        help="Optional K overrides. If omitted, use dataset default_k_values",
    )
    parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.0,
        help="Included for compatibility. Local lexical retrieval usually uses 0.0",
    )
    return parser


def _default_output_path(dataset_path: str) -> Path:
    source = Path(dataset_path)
    if source.suffix.lower() == ".json":
        return source.with_suffix(".local.results.json")
    return source.parent / f"{source.name}.local.results.json"


def run_local_evaluation(args: argparse.Namespace) -> int:
    dataset = EvalDataset.load(args.dataset)
    rag_service = LocalCorpusRAGService.from_inputs(
        input_paths=args.input,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        min_chunk_size=args.min_chunk_size,
        use_markdown_splitter=not args.disable_markdown_splitter,
        min_chars=args.min_chars,
    )

    app = SimpleNamespace(
        config={
            "ENABLE_HYBRID_SEARCH": False,
            "RAG_ENABLE_MULTI_SOURCE": False,
            "RELEVANCE_THRESHOLD": args.relevance_threshold,
        }
    )

    evaluator = RetrievalEvaluator(rag_service=rag_service)
    result = evaluator.evaluate_dataset(
        app=app,
        dataset=dataset,
        collection_names=["local_corpus"],
        k_values=args.k,
        enable_rerank=False,
        enable_hybrid=False,
        enable_multi_source=False,
        relevance_threshold=args.relevance_threshold,
    )

    result["resolved_targets"] = {
        "mode": "local_corpus",
        "inputs": list(args.input),
        "chunking": {
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap,
            "min_chunk_size": args.min_chunk_size,
            "min_chars": args.min_chars,
            "use_markdown_splitter": not args.disable_markdown_splitter,
        },
    }

    output_path = Path(args.output) if args.output else _default_output_path(args.dataset)
    write_json(output_path, result)

    print(f"Local evaluation written to: {output_path}")
    print(f"Queries: {result['summary']['total_queries']}")
    for level_name, level_summary in result["summary"]["levels"].items():
        if level_summary["queries_with_labels"] <= 0:
            print(f"{level_name}: no labels")
            continue
        fragments = []
        for k in result["summary"]["k_values"]:
            averages = level_summary["averages"][str(k)]
            fragments.append(
                "R@{k}={recall:.4f} Hit@{k}={hit:.4f} MRR@{k}={mrr:.4f}".format(
                    k=k,
                    recall=averages["recall"],
                    hit=averages["hit_rate"],
                    mrr=averages["mrr"],
                )
            )
        print(f"{level_name}: " + " | ".join(fragments))

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return run_local_evaluation(args)


if __name__ == "__main__":
    raise SystemExit(main())
