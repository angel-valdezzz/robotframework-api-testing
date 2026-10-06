"""Publish only processed demo outputs; keep generated reports out of Git history."""

import argparse
import html
import json
import os
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["api", "selenium"], required=True)
    parser.add_argument("--outcome", default="local")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    site = root / "report-site"
    sources = ["results", "results-ddt"] if args.kind == "api" else ["results"]
    case_pattern = "cases/*.html" if args.kind == "api" else "business-reports/*.html"
    cases = [(folder, p) for folder in sources for p in (root / folder).glob(case_pattern)]
    if not cases:
        raise SystemExit("No case reports generated; preserve the previously published site.")
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()
    for folder in sources:
        source = root / folder
        if source.is_dir():
            shutil.copytree(source, site / folder)
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": os.getenv("GITHUB_SHA", "local"),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "repository": os.getenv("GITHUB_REPOSITORY", ""),
        "validation": args.outcome,
        "cases": len(cases),
    }
    (site / "execution.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    escape = html.escape
    title = "API Testing" if args.kind == "api" else "ParaBank · Selenium"
    rows = []
    for folder, path in sorted(cases):
        relative = Path(folder) / path.relative_to(root / folder)
        links = [
            f'<a href="{escape(relative.as_posix(), quote=True)}" target="_blank" '
            'rel="noopener">HTML ↗</a>'
        ]
        for extension in ["pdf", "docx"]:
            alternate = path.with_suffix("." + extension)
            if alternate.is_file():
                target = Path(folder) / alternate.relative_to(root / folder)
                links.append(
                    f'<a href="{escape(target.as_posix(), quote=True)}">{extension.upper()}</a>'
                )
        rows.append(f"<tr><td>{escape(path.stem)}</td><td>{' · '.join(links)}</td></tr>")
    robot_links = []
    for folder in sources:
        for filename, label in [
            ("report.html", "Reporte Robot"),
            ("log.html", "Log Robot"),
            ("console.log", "Consola"),
        ]:
            if (site / folder / filename).is_file():
                robot_links.append(
                    f'<a href="{folder}/{filename}" target="_blank" '
                    f'rel="noopener">{label} · {folder} ↗</a>'
                )
    run_url = ""
    if metadata["repository"] and metadata["run_id"] != "local":
        run_url = f"https://github.com/{metadata['repository']}/actions/runs/{metadata['run_id']}"
    workflow_link = (
        f'<a href="{escape(run_url, quote=True)}">Ver ejecución en Actions ↗</a>' if run_url else ""
    )
    description = (
        "Incluye un fallo intencional y un caso omitido; "
        "el runner verifica los resultados esperados."
        if args.kind == "api"
        else "Evidencias con highlights, dots y anotaciones de Marka. "
        "Datos ficticios del demo público de ParaBank."
    )
    accent = "#1765aa" if args.kind == "api" else "#6554c0"
    document = (
        Path(__file__)
        .with_name("latest.html")
        .read_text(encoding="utf-8")
        .format(
            title=title,
            accent=accent,
            description=description,
            metadata={key: escape(str(value)) for key, value in metadata.items()},
            outcome=escape(args.outcome),
            rows="".join(rows),
            robot_links="".join(robot_links),
            workflow_link=workflow_link,
            count=len(cases),
        )
    )
    (site / "index.html").write_text(document, encoding="utf-8")
    (site / ".nojekyll").touch()
    with zipfile.ZipFile(site / "reports.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(site.rglob("*")):
            if path.is_file() and path.name != "reports.zip":
                archive.write(path, path.relative_to(site))
    print(f"Prepared {len(cases)} case reports, index and ZIP in {site}")


if __name__ == "__main__":
    main()
