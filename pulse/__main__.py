from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pulse.config import AppConfig, ConfigError, load_config
from pulse.env import load_dotenv
from pulse.logging_config import configure_logging, get_logger
from pulse.run_id import RunIdError, resolve_run_id

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_INVALID_ARGS = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pulse",
        description="Groww Weekly Review Pulse — Play Store insights to Google Docs + Gmail",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the full weekly pipeline")
    _add_common_run_args(run_parser)
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run through render; MCP delivery steps are health-check/preview only",
    )
    run_parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Deliver Google Doc only; skip Gmail teaser",
    )
    run_parser.add_argument(
        "--email-mode",
        choices=["draft", "send"],
        help="Override groww.email.default_mode for deliver-email",
    )

    ingest_parser = subparsers.add_parser("ingest", help="Ingest and preprocess Play Store reviews")
    _add_common_run_args(ingest_parser)

    analyze_parser = subparsers.add_parser("analyze", help="Cluster reviews and generate themes")
    _add_common_run_args(analyze_parser)

    render_parser = subparsers.add_parser("render", help="Render Doc and email payloads")
    _add_common_run_args(render_parser)

    deliver_docs_parser = subparsers.add_parser(
        "deliver-docs",
        help="Append rendered report to Google Doc via hosted MCP",
    )
    _add_common_run_args(deliver_docs_parser)
    deliver_docs_parser.add_argument(
        "--force",
        action="store_true",
        help="Append even if this run was already delivered locally",
    )
    deliver_docs_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Health-check MCP only; do not append to Google Doc",
    )

    deliver_email_parser = subparsers.add_parser(
        "deliver-email",
        help="Create Gmail teaser draft via hosted MCP",
    )
    _add_common_run_args(deliver_email_parser)
    deliver_email_parser.add_argument(
        "--force",
        action="store_true",
        help="Create draft even if this run was already delivered locally",
    )
    deliver_email_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Health-check MCP and preview email; do not create draft",
    )
    deliver_email_parser.add_argument(
        "--email-mode",
        choices=["draft", "send"],
        help="Override groww.email.default_mode (hosted MCP supports draft only)",
    )

    config_parser = subparsers.add_parser("config", help="Validate and print loaded configuration")
    config_parser.add_argument(
        "--product",
        default="groww",
        choices=["groww"],
        help="Product configuration to load (v1: groww only)",
    )

    return parser


def _add_common_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--product",
        default="groww",
        choices=["groww"],
        help="Product to run (v1: groww only)",
    )
    parser.add_argument(
        "--week",
        metavar="YYYY-Www",
        help="ISO week to run (default: current week in Asia/Kolkata)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-fetch Play Store reviews instead of using cached raw data",
    )


def _preprocess_settings(config: AppConfig):
    from pulse.preprocess.normalize import PreprocessSettings

    return PreprocessSettings(
        min_words=config.pulse.preprocess.min_words,
        reject_non_latin_script=config.pulse.preprocess.reject_non_latin_script,
        reject_emoji=config.pulse.preprocess.reject_emoji,
    )


def _pii_settings(config: AppConfig):
    from pulse.preprocess.pii import PiiSettings

    return PiiSettings(url_mode=config.pulse.preprocess.pii_url_mode)


def _run_ingest(config: AppConfig, run_id: str, force_refresh: bool) -> int:
    from pulse.ingestion.errors import IngestionError
    from pulse.ingestion.playstore import fetch_reviews_for_run
    from pulse.preprocess.pipeline import preprocess_reviews_for_run

    logger = get_logger(__name__, run_id)
    try:
        raw_reviews = fetch_reviews_for_run(
            run_id=run_id,
            package_id=config.groww.package_id,
            review_window_weeks=config.pulse.review_window_weeks,
            timezone=config.pulse.timezone,
            min_reviews_for_run=config.pulse.min_reviews_for_run,
            enforce_min_reviews=True,
            force_refresh=force_refresh,
        )
        cleaned, stats = preprocess_reviews_for_run(
            run_id=run_id,
            reviews=raw_reviews,
            settings=_preprocess_settings(config),
            pii_settings=_pii_settings(config),
            min_reviews_for_run=config.pulse.min_reviews_for_run,
            force_refresh=force_refresh,
        )
    except IngestionError as exc:
        logger.error("Ingestion failed: %s", exc)
        print(f"Ingestion error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    print(f"raw_reviews={len(raw_reviews)}")
    print(f"processed_reviews={len(cleaned)}")
    print("raw_file=data/reviews_raw.json")
    print("normalized_file=data/reviews_normalized.json")
    if stats.input_count >= 0:
        print(
            f"dropped_short={stats.dropped_short} "
            f"dropped_emoji={stats.dropped_emoji} "
            f"dropped_script={stats.dropped_script}"
        )
    logger.info("Ingestion complete: raw=%s processed=%s", len(raw_reviews), len(cleaned))
    return EXIT_SUCCESS


def _run_analyze(config: AppConfig, run_id: str, force_refresh: bool) -> int:
    from pulse.data_paths import normalized_reviews_path, report_path
    from pulse.ingestion.errors import IngestionError
    from pulse.preprocess.cache import load_processed_reviews
    from pulse.reasoning.errors import ReasoningError
    from pulse.reasoning.pipeline import analyze_reviews_for_run, load_normalized_reviews_for_run

    logger = get_logger(__name__, run_id)
    settings = _preprocess_settings(config)
    pii_settings = _pii_settings(config)

    cached = load_processed_reviews(
        normalized_reviews_path(),
        run_id=run_id,
        settings=settings,
        pii_settings=pii_settings,
    )
    if cached is None or force_refresh:
        logger.info("Normalized reviews missing or force-refresh; running ingest first.")
        ingest_status = _run_ingest(config, run_id, force_refresh=force_refresh)
        if ingest_status != EXIT_SUCCESS:
            return ingest_status

    try:
        reviews = load_normalized_reviews_for_run(config, run_id)
        report = analyze_reviews_for_run(
            config,
            run_id,
            reviews,
            force_refresh_embeddings=force_refresh,
        )
    except (ReasoningError, IngestionError) as exc:
        logger.error("Analyze failed: %s", exc)
        print(f"Analyze error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    out_file = report_path(run_id)
    print(f"themes={len(report.themes)}")
    print(f"review_count={report.review_count}")
    print(f"report_file={out_file}")
    for theme in report.themes:
        print(f"  {theme.rank}. {theme.title} ({theme.review_count} reviews)")
    return EXIT_SUCCESS


def _run_render(config: AppConfig, run_id: str) -> int:
    from pulse.ingestion.errors import CacheError
    from pulse.data_paths import doc_payload_path, email_payload_path, report_path
    from pulse.reasoning.report_io import load_report
    from pulse.render.errors import RenderError
    from pulse.render.pipeline import render_report_for_run

    logger = get_logger(__name__, run_id)
    report_file = report_path(run_id)
    try:
        report = load_report(report_file)
    except CacheError as exc:
        logger.error("Render failed: report not found (%s)", exc)
        print(f"Render error: {exc}", file=sys.stderr)
        print(f"Run analyze first: python -m pulse analyze --week {run_id.split(':', 1)[1]}", file=sys.stderr)
        return EXIT_FAILURE

    try:
        result = render_report_for_run(report, config)
    except RenderError as exc:
        logger.error("Render failed: %s", exc)
        print(f"Render error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    doc_file = doc_payload_path(run_id)
    email_file = email_payload_path(run_id)
    print(f"heading={result.doc_payload.heading}")
    print(f"doc_payload_file={doc_file}")
    print(f"email_payload_file={email_file}")
    print(f"email_subject={result.email_payload.subject}")
    print(f"doc_content_hash={result.doc_payload.content_hash}")
    logger.info(
        "Render complete (doc_hash=%s, email_hash=%s)",
        result.doc_payload.content_hash,
        result.email_payload.content_hash,
    )
    return EXIT_SUCCESS


def _run_deliver_docs(
    config: AppConfig,
    run_id: str,
    *,
    force: bool,
    dry_run: bool,
) -> int:
    from pulse.data_paths import doc_payload_path
    from pulse.delivery.docs_delivery import build_client, check_mcp_health, deliver_doc_payload
    from pulse.delivery.errors import DeliveryError, McpAuthError
    from pulse.render.errors import RenderError
    from pulse.render.payload_io import load_doc_payload

    logger = get_logger(__name__, run_id)
    doc_file = doc_payload_path(run_id)

    try:
        payload = load_doc_payload(doc_file)
    except RenderError as exc:
        logger.error("Deliver-docs failed: doc payload not found (%s)", exc)
        print(f"Deliver-docs error: {exc}", file=sys.stderr)
        print(
            f"Run render first: python -m pulse render --week {run_id.split(':', 1)[1]}",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    try:
        client = build_client(config)
        health = check_mcp_health(client)
        print(f"mcp_status={health.get('status', 'unknown')}")
        print(f"mcp_server={config.pulse.mcp.server_url}")
        if dry_run:
            print(f"heading={payload.heading}")
            print(f"document_id={payload.document_id}")
            print(f"content_chars={len(payload.content)}")
            print("dry_run=true (no append performed)")
            return EXIT_SUCCESS

        result = deliver_doc_payload(
            payload,
            config,
            force=force,
            client=client,
        )
    except McpAuthError as exc:
        logger.error("Deliver-docs auth failed: %s", exc)
        print(f"Deliver-docs error: {exc}", file=sys.stderr)
        print("Set MCP_API_KEY in .env (see .env.example).", file=sys.stderr)
        return EXIT_FAILURE
    except DeliveryError as exc:
        logger.error("Deliver-docs failed: %s", exc)
        print(f"Deliver-docs error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    print(f"inserted={result.inserted}")
    print(f"section_anchor_url={result.section_anchor_url}")
    print(f"heading={result.heading}")
    logger.info(
        "Docs delivery complete (inserted=%s, url=%s)",
        result.inserted,
        result.section_anchor_url,
    )
    return EXIT_SUCCESS


def _run_deliver_email(
    config: AppConfig,
    run_id: str,
    *,
    force: bool,
    dry_run: bool,
    email_mode: str | None,
) -> int:
    from pulse.data_paths import email_payload_path
    from pulse.delivery.docs_delivery import build_client, check_mcp_health
    from pulse.delivery.errors import DeliveryError, McpAuthError
    from pulse.delivery.gmail_delivery import (
        apply_section_anchor_url,
        deliver_email_payload,
        resolve_section_anchor_url,
    )
    from pulse.render.errors import RenderError
    from pulse.render.payload_io import load_email_payload

    logger = get_logger(__name__, run_id)
    email_file = email_payload_path(run_id)

    try:
        payload = load_email_payload(email_file)
    except RenderError as exc:
        logger.error("Deliver-email failed: email payload not found (%s)", exc)
        print(f"Deliver-email error: {exc}", file=sys.stderr)
        print(
            f"Run render first: python -m pulse render --week {run_id.split(':', 1)[1]}",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    mode_override = email_mode or payload.mode
    try:
        client = build_client(config)
        health = check_mcp_health(client)
        section_url = resolve_section_anchor_url(run_id)
        prepared = apply_section_anchor_url(payload, section_url)
        print(f"mcp_status={health.get('status', 'unknown')}")
        print(f"mcp_server={config.pulse.mcp.server_url}")
        print(f"email_mode={mode_override}")
        print(f"recipients={','.join(prepared.to)}")
        print(f"subject={prepared.subject}")
        print(f"section_anchor_url={section_url}")
        if dry_run:
            print(f"text_body_chars={len(prepared.text_body)}")
            print("dry_run=true (no Gmail draft created)")
            return EXIT_SUCCESS

        result = deliver_email_payload(
            payload,
            config,
            force=force,
            mode=mode_override,  # type: ignore[arg-type]
            section_anchor_url=section_url,
            client=client,
        )
    except McpAuthError as exc:
        logger.error("Deliver-email auth failed: %s", exc)
        print(f"Deliver-email error: {exc}", file=sys.stderr)
        print("Set MCP_API_KEY in .env (see .env.example).", file=sys.stderr)
        return EXIT_FAILURE
    except DeliveryError as exc:
        logger.error("Deliver-email failed: %s", exc)
        print(f"Deliver-email error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    print(f"created={result.created}")
    print(f"draft_ids={','.join(result.draft_ids)}")
    print(f"message_ids={','.join(result.message_ids)}")
    logger.info(
        "Email delivery complete (created=%s, drafts=%s)",
        result.created,
        result.draft_ids,
    )
    return EXIT_SUCCESS


def _run_full(
    config: AppConfig,
    run_id: str,
    *,
    force_refresh: bool,
    dry_run: bool,
    skip_email: bool,
    email_mode: str | None,
) -> int:
    """Execute ingest → analyze → render → deliver-docs → deliver-email."""
    logger = get_logger(__name__, run_id)
    logger.info(
        "Full pipeline starting (dry_run=%s, skip_email=%s, email_mode=%s)",
        dry_run,
        skip_email,
        email_mode,
    )

    stages: list[tuple[str, int]] = []
    stages.append(("ingest", _run_ingest(config, run_id, force_refresh=force_refresh)))
    if stages[-1][1] != EXIT_SUCCESS:
        return stages[-1][1]

    stages.append(("analyze", _run_analyze(config, run_id, force_refresh=force_refresh)))
    if stages[-1][1] != EXIT_SUCCESS:
        return stages[-1][1]

    stages.append(("render", _run_render(config, run_id)))
    if stages[-1][1] != EXIT_SUCCESS:
        return stages[-1][1]

    stages.append(
        (
            "deliver-docs",
            _run_deliver_docs(config, run_id, force=False, dry_run=dry_run),
        )
    )
    if stages[-1][1] != EXIT_SUCCESS:
        return stages[-1][1]

    if not skip_email:
        stages.append(
            (
                "deliver-email",
                _run_deliver_email(
                    config,
                    run_id,
                    force=False,
                    dry_run=dry_run,
                    email_mode=email_mode,
                ),
            )
        )
        if stages[-1][1] != EXIT_SUCCESS:
            return stages[-1][1]

    print(f"pipeline_status=completed run_id={run_id} dry_run={dry_run}")
    logger.info("Full pipeline complete for run_id=%s", run_id)
    return EXIT_SUCCESS


def _stub_not_implemented(command: str, run_id: str) -> int:
    logger = get_logger(__name__, run_id)
    logger.warning("Command %r is not implemented yet.", command)
    return EXIT_FAILURE


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command is None:
        parser.print_help()
        return EXIT_SUCCESS

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_INVALID_ARGS

    if args.command == "config":
        print(f"product={config.groww.product}")
        print(f"package_id={config.groww.package_id}")
        print(f"doc_id={config.groww.doc_id}")
        print(f"email_recipients={','.join(config.groww.email_recipients)}")
        print(f"email_mode={config.groww.email_default_mode}")
        print(f"timezone={config.pulse.timezone}")
        print(f"review_window_weeks={config.pulse.review_window_weeks}")
        print(f"embedding_model={config.pulse.embeddings.model}")
        print(f"llm_provider={config.pulse.llm.provider}")
        print(f"llm_model={config.pulse.llm.model}")
        print(f"mcp_server_url={config.pulse.mcp.server_url}")
        return EXIT_SUCCESS

    try:
        run_id = resolve_run_id(
            product="groww",
            iso_week=getattr(args, "week", None),
            timezone=config.pulse.timezone,
        )
    except RunIdError as exc:
        print(f"Invalid week: {exc}", file=sys.stderr)
        return EXIT_INVALID_ARGS

    configure_logging(run_id=run_id)
    logger = get_logger(__name__, run_id)
    logger.info("pulse %s starting (run_id=%s)", args.command, run_id)

    if args.command == "ingest":
        return _run_ingest(config, run_id, force_refresh=args.force_refresh)

    if args.command == "analyze":
        return _run_analyze(config, run_id, force_refresh=args.force_refresh)

    if args.command == "render":
        return _run_render(config, run_id)

    if args.command == "deliver-docs":
        return _run_deliver_docs(
            config,
            run_id,
            force=args.force,
            dry_run=args.dry_run,
        )

    if args.command == "deliver-email":
        return _run_deliver_email(
            config,
            run_id,
            force=args.force,
            dry_run=args.dry_run,
            email_mode=getattr(args, "email_mode", None),
        )

    if args.command == "run":
        return _run_full(
            config,
            run_id,
            force_refresh=args.force_refresh,
            dry_run=getattr(args, "dry_run", False),
            skip_email=getattr(args, "skip_email", False),
            email_mode=getattr(args, "email_mode", None),
        )

    print(f"Unknown command: {args.command}", file=sys.stderr)
    return EXIT_INVALID_ARGS


if __name__ == "__main__":
    raise SystemExit(main())
