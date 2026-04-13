"""CLI entrypoint for the additive RAG retrieval evaluation toolkit."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from rag_eval.dataset import (  # noqa: E402
    EvalDataset,
    build_template_dataset,
    load_questions,
    normalize_k_values,
    write_json,
)
from rag_eval.evaluator import RetrievalEvaluator, resolve_collection_names  # noqa: E402
from rag_eval.generator import (  # noqa: E402
    add_generate_samples_subparser,
    run_generate_samples_command,
)
from rag_eval.local_eval import run_local_evaluation  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone RAG Recall@K evaluation toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list-targets",
        help="List knowledge bases and custom models that can be evaluated",
    )
    list_parser.add_argument(
        "--config-name",
        default="development",
        help="Flask config name, defaults to development",
    )

    template_parser = subparsers.add_parser(
        "build-template",
        help="Build an empty annotation template from a .txt or .json question list",
    )
    template_parser.add_argument("--questions", required=True, help="Path to .txt or .json questions")
    template_parser.add_argument("--output", required=True, help="Where to write the template dataset JSON")
    template_parser.add_argument("--name", default="", help="Dataset name")
    template_parser.add_argument("--description", default="", help="Dataset description")
    template_parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=[1, 3, 5, 10],
        help="K values for Recall@K style evaluation",
    )

    add_generate_samples_subparser(subparsers)

    local_eval_parser = subparsers.add_parser(
        "evaluate-local",
        help="Run offline local-corpus retrieval evaluation without Flask/Chroma",
    )
    local_eval_parser.add_argument("--dataset", required=True, help="Path to labeled evaluation dataset JSON")
    local_eval_parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Input file or directory for the local corpus. Can be repeated",
    )
    local_eval_parser.add_argument(
        "--output",
        default="",
        help="Optional result JSON path. Defaults to <dataset>.local.results.json",
    )
    local_eval_parser.add_argument("--chunk-size", type=int, default=1000)
    local_eval_parser.add_argument("--chunk-overlap", type=int, default=200)
    local_eval_parser.add_argument("--min-chunk-size", type=int, default=200)
    local_eval_parser.add_argument("--min-chars", type=int, default=80)
    local_eval_parser.add_argument(
        "--disable-markdown-splitter",
        action="store_true",
        help="Disable markdown header splitting",
    )
    local_eval_parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=None,
        help="Optional K overrides. If omitted, use dataset default_k_values",
    )
    local_eval_parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.0,
        help="Included for compatibility. Local lexical retrieval usually uses 0.0",
    )

    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Run retrieval evaluation using a labeled dataset",
    )
    eval_parser.add_argument("--dataset", required=True, help="Path to the labeled evaluation dataset JSON")
    eval_parser.add_argument(
        "--output",
        default="",
        help="Optional output path. Defaults to <dataset>.results.json",
    )
    eval_parser.add_argument(
        "--config-name",
        default="development",
        help="Flask config name, defaults to development",
    )
    eval_parser.add_argument(
        "--kb-id",
        action="append",
        default=[],
        help="Knowledge base id to evaluate. Can be provided multiple times",
    )
    eval_parser.add_argument(
        "--collection",
        action="append",
        default=[],
        help="Direct Chroma collection name. Can be provided multiple times",
    )
    eval_parser.add_argument(
        "--custom-model-id",
        default="",
        help="Custom model id. All bound knowledge bases will be evaluated together",
    )
    eval_parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=None,
        help="Optional K overrides. If omitted, use dataset default_k_values",
    )
    eval_parser.add_argument(
        "--disable-rerank",
        action="store_true",
        help="Disable cosine reranking during evaluation",
    )
    eval_parser.add_argument(
        "--disable-hybrid",
        action="store_true",
        help="Disable BM25 hybrid retrieval during evaluation",
    )
    eval_parser.add_argument(
        "--disable-multi-source",
        action="store_true",
        help="Disable multi-source diversity filtering during evaluation",
    )
    eval_parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=None,
        help="Override RELEVANCE_THRESHOLD. For pure recall testing, you may want 0.0",
    )
    eval_parser.add_argument(
        "--preview-chars",
        type=int,
        default=180,
        help="Preview character limit stored in the result JSON",
    )

    return parser


def _create_app(config_name: str):
    from app import create_app

    return create_app(config_name)


def _command_list_targets(args: argparse.Namespace) -> int:
    from app.models import CustomModel, KnowledgeBase

    app = _create_app(args.config_name)
    with app.app_context():
        knowledge_bases = KnowledgeBase.query.order_by(KnowledgeBase.created_at.desc()).all()
        custom_models = CustomModel.query.order_by(CustomModel.created_at.desc()).all()

        print("Knowledge Bases")
        print("-" * 80)
        if not knowledge_bases:
            print("  (none)")
        for kb in knowledge_bases:
            print(
                f"- id={kb.id} | name={kb.name} | collection={kb.collection_name} | files={kb.files.count()}"
            )

        print()
        print("Custom Models")
        print("-" * 80)
        if not custom_models:
            print("  (none)")
        for model in custom_models:
            bound_kbs = [
                binding.knowledge_base.name
                for binding in model.knowledge_bindings.all()
                if binding.knowledge_base is not None
            ]
            kb_summary = ", ".join(bound_kbs) if bound_kbs else "(no bound knowledge bases)"
            print(
                f"- id={model.id} | name={model.name} | base_model={model.base_model} | kbs={kb_summary}"
            )

    return 0


def _command_build_template(args: argparse.Namespace) -> int:
    questions = load_questions(args.questions)
    dataset = build_template_dataset(
        questions=questions,
        k_values=normalize_k_values(args.k),
        name=args.name,
        description=args.description,
    )
    output_path = dataset.save(args.output)

    print(f"Template written to: {output_path}")
    print(f"Questions: {len(dataset.queries)}")
    print(f"K values: {dataset.k_values}")
    return 0


def _default_output_path(dataset_path: str) -> Path:
    source = Path(dataset_path)
    if source.suffix.lower() == ".json":
        return source.with_suffix(".results.json")
    return source.parent / f"{source.name}.results.json"


def _command_evaluate(args: argparse.Namespace) -> int:
    if not args.kb_id and not args.collection and not args.custom_model_id:
        raise ValueError("Provide at least one of --kb-id, --collection, or --custom-model-id")

    dataset = EvalDataset.load(args.dataset)
    app = _create_app(args.config_name)

    with app.app_context():
        resolved = resolve_collection_names(
            kb_ids=args.kb_id,
            collection_names=args.collection,
            custom_model_id=(args.custom_model_id or None),
        )
        evaluator = RetrievalEvaluator()
        result = evaluator.evaluate_dataset(
            app=app,
            dataset=dataset,
            collection_names=resolved["collection_names"],
            k_values=args.k,
            enable_rerank=not args.disable_rerank,
            enable_hybrid=False if args.disable_hybrid else None,
            enable_multi_source=False if args.disable_multi_source else None,
            relevance_threshold=args.relevance_threshold,
            preview_chars=args.preview_chars,
        )

    result["resolved_targets"] = resolved

    output_path = Path(args.output) if args.output else _default_output_path(args.dataset)
    write_json(output_path, result)

    print(f"Evaluation written to: {output_path}")
    print(f"Collections: {', '.join(result['retrieval_settings']['collection_names'])}")
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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-targets":
        return _command_list_targets(args)
    if args.command == "build-template":
        return _command_build_template(args)
    if args.command == "generate-samples":
        return run_generate_samples_command(args)
    if args.command == "evaluate-local":
        return run_local_evaluation(args)
    if args.command == "evaluate":
        return _command_evaluate(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
