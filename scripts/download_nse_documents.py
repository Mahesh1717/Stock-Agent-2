from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


WATCHLIST_PATH = Path("data/nifty_watchlist.csv")
DOCUMENTS_PATH = Path("documents")
DOWNLOAD_CACHE_PATH = Path("database/nse_downloads")
MANIFEST_PATH = Path("database/document_manifest.json")


@dataclass(frozen=True)
class ManifestEntry:
    symbol: str
    document_type: str
    title: str
    source_url: str
    local_path: str
    status: str
    error: str = ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Download financial documents from NSE")
    parser.add_argument("--symbols", help="Comma-separated symbols. Defaults to all watchlist symbols.")
    parser.add_argument("--max-stocks", type=int, help="Limit number of stocks for testing.")
    parser.add_argument("--max-annual-reports", type=int, default=3, help="Annual reports per stock.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between NSE requests.")
    parser.add_argument("--server", action="store_true", help="Use nse server/http2 mode.")
    parser.add_argument("--overwrite", action="store_true", help="Re-download existing files.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    symbols = _load_symbols(args.symbols, args.max_stocks)
    DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_CACHE_PATH.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    try:
        from nse import NSE
    except ImportError as exc:
        raise SystemExit("Install downloader dependency first: pip install \"nse[local]\"") from exc

    with NSE(download_folder=DOWNLOAD_CACHE_PATH, server=args.server, timeout=30) as nse:
        for index, symbol in enumerate(symbols, start=1):
            logging.info("[%s/%s] %s", index, len(symbols), symbol)
            folder = DOCUMENTS_PATH / symbol
            folder.mkdir(parents=True, exist_ok=True)
            (folder / ".gitkeep").touch()

            entries = _download_annual_reports(
                nse=nse,
                symbol=symbol,
                folder=folder,
                max_reports=args.max_annual_reports,
                overwrite=args.overwrite,
            )
            manifest.extend(entries)
            _save_manifest(manifest)
            time.sleep(args.sleep)

    logging.info("Done. Manifest: %s", MANIFEST_PATH)


def _load_symbols(raw_symbols: str | None, max_stocks: int | None) -> list[str]:
    if raw_symbols:
        symbols = [symbol.strip().upper() for symbol in raw_symbols.split(",") if symbol.strip()]
    else:
        with WATCHLIST_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            symbols = [row["symbol"].strip().upper() for row in csv.DictReader(file) if row.get("symbol")]
    return symbols[:max_stocks] if max_stocks else symbols


def _download_annual_reports(
    nse: Any,
    symbol: str,
    folder: Path,
    max_reports: int,
    overwrite: bool,
) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    try:
        response = nse.annual_reports(symbol=symbol)
        reports = _extract_report_records(response)[:max_reports]
        if not reports:
            return [
                ManifestEntry(
                    symbol=symbol,
                    document_type="annual_report",
                    title="No annual reports found",
                    source_url="",
                    local_path="",
                    status="missing",
                )
            ]

        for report in reports:
            source_url = str(report.get("fileName") or report.get("url") or report.get("link") or "")
            title = _report_title(symbol, report)
            target = folder / f"{title}.pdf"
            if target.exists() and not overwrite:
                entries.append(_entry(symbol, title, source_url, target, "exists"))
                continue

            downloaded = Path(nse.download_document(source_url, folder=DOWNLOAD_CACHE_PATH))
            final_path = _move_download(downloaded, target)
            entries.append(_entry(symbol, title, source_url, final_path, "downloaded"))
    except Exception as exc:
        logging.exception("Failed to download annual reports for %s", symbol)
        entries.append(
            ManifestEntry(
                symbol=symbol,
                document_type="annual_report",
                title="Download failed",
                source_url="",
                local_path="",
                status="failed",
                error=str(exc),
            )
        )
    return entries


def _extract_report_records(response: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(response, dict):
        for value in response.values():
            if isinstance(value, list):
                records.extend(item for item in value if isinstance(item, dict))
    elif isinstance(response, list):
        records.extend(item for item in response if isinstance(item, dict))

    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        url = str(record.get("fileName") or record.get("url") or record.get("link") or "")
        if url:
            unique[url] = record
    return list(unique.values())


def _report_title(symbol: str, report: dict[str, Any]) -> str:
    year = (
        report.get("year")
        or report.get("financialYear")
        or report.get("fromYr")
        or report.get("toYr")
        or "latest"
    )
    return _safe_filename(f"{symbol}_Annual_Report_{year}")


def _safe_filename(value: str) -> str:
    keep = [char if char.isalnum() or char in {"-", "_"} else "_" for char in value]
    return "_".join("".join(keep).split("_"))


def _move_download(downloaded: Path, target: Path) -> Path:
    if downloaded.suffix.lower() == ".pdf":
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(downloaded), str(target))
        return target

    target = target.with_suffix(downloaded.suffix or ".pdf")
    shutil.move(str(downloaded), str(target))
    return target


def _entry(symbol: str, title: str, source_url: str, path: Path, status: str) -> ManifestEntry:
    return ManifestEntry(
        symbol=symbol,
        document_type="annual_report",
        title=title,
        source_url=source_url,
        local_path=str(path),
        status=status,
    )


def _load_manifest() -> list[ManifestEntry]:
    if not MANIFEST_PATH.exists():
        return []
    values = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [ManifestEntry(**value) for value in values]


def _save_manifest(entries: list[ManifestEntry]) -> None:
    MANIFEST_PATH.write_text(
        json.dumps([asdict(entry) for entry in entries], indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
