"""Build the portable HTML account of the verified local benchmark runs, including before/after optimization."""

from collections import Counter
import csv
from datetime import date
import html
import io
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
RUN_IDS = (
    "33fface4-afbf-4f3e-b7f0-a5e01c4d924e",
    "72e35711-6375-45c6-af71-df03d301f4f3",
    "05a69d08-12e5-4b0c-ac2c-eb0f161f6957",
    "before-quiet/72a82c23-9820-47e7-b0d2-42111d865a09",
    "after-quiet/dac69290-2cbe-4b30-b484-4fedd4201269",
)
RUN_LABELS = (
    "Iniziale · file piccoli",
    "Iniziale · trasferimenti",
    "Iniziale · oggetti versionati",
    "Baseline · prima ottimizzazione",
    "Aggiornato · dopo ottimizzazione",
)
CLIENTS = {
    "legacy": "Genropy legacy",
    "genro": "Genro Storage",
    "genro-unversioned": "Genro · versioni disattivate",
    "backend": "FsspecBackend",
    "s3fs": "s3fs diretto",
    "boto3": "boto3 diretto",
    "smart-open": "smart_open diretto",
}
OPS = {
    "exists": "Esistenza",
    "missing": "File assente",
    "attrs": "Attributi del file",
    "listing": "Elenco directory",
    "tree_attrs": "Albero con attributi",
    "read": "Lettura completa",
    "write": "Scrittura completa",
    "copy": "Copia",
    "move": "Spostamento",
    "local_path": "File temporaneo locale",
    "client_start_and_exists": "Avvio client + esistenza",
}


def esc(value):
    return html.escape(str(value), quote=True)


def number(value, digits=2):
    if value is None:
        return "—"
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def size_label(size):
    if size >= 2**20:
        return f"{size // 2**20} MiB"
    return f"{size // 1024} KiB"


def table(headers, rows, caption):
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join(
        '<tr><th scope="row">'
        + esc(row[0])
        + "</th>"
        + "".join("<td>" + esc(cell) + "</td>" for cell in row[1:])
        + "</tr>"
        for row in rows
    )
    return (
        f'<div class="table-scroll" tabindex="0" role="region" aria-label="{esc(caption)}">'
        f"<table><caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def bars(title, entries, unit="ms"):
    maximum = max(value for _, value, _ in entries) * 1.12 or 1
    content = []
    for name, value, client in entries:
        content.append(
            f'<div class="bar-row"><div class="bar-label"><span>{esc(name)}</span>'
            f"<strong>{number(value)} <small>{unit}</small></strong></div>"
            f'<div class="bar-track"><div class="bar-fill {esc(client)}" '
            f'style="width:{100 * value / maximum:.5f}%"></div></div></div>'
        )
    return (
        f'<figure class="mini-chart"><figcaption>{esc(title)}</figcaption>'
        + "".join(content)
        + f'<div class="scale"><span>0 {unit}</span>'
        f"<span>{number(maximum, 1)} {unit}</span></div></figure>"
    )


def row_for(run, op, client, size, cache="cold", workers=1):
    return next(
        r
        for r in run["summary"]
        if r["operation"] == op
        and r["adapter"] == client
        and r["size_bytes"] == size
        and r["cache"] == cache
        and r["workers"] == workers
    )


def load_runs():
    runs = []
    for run_id, label in zip(RUN_IDS, RUN_LABELS):
        data = json.loads((ROOT / "results" / run_id / "results.json").read_text())
        meta = data["metadata"]
        if meta["status"] != "complete" or meta["cleanup"] != "complete":
            raise ValueError("Only completed and cleaned-up runs belong in this report")
        if any(sample["errors"] for sample in data["samples"]):
            raise ValueError("Failed samples must not be described as successful")
        # Validate the displayed medians against the original measurements.
        for row in data["summary"]:
            samples = [
                s
                for s in data["samples"]
                if not s["warmup"]
                and all(
                    s[k] == row[k]
                    for k in ("adapter", "operation", "size_bytes", "workers", "cache")
                )
            ]
            actual = statistics.median(v for s in samples for v in s["latencies_s"]) * 1000
            if abs(actual - row["median_ms"]) > 1e-8:
                raise ValueError("Summary median differs from raw measurements")
        # Portable export: retain measurement provenance without private machine paths,
        # endpoint names, bucket identifiers or object prefixes.
        portable = {
            k: v
            for k, v in meta.items()
            if k not in ("genro_source", "endpoint_host", "bucket", "prefix")
        }
        portable["genro_source_origin"] = "checkout/src/genro_storage"
        runs.append(
            dict(label=label, metadata=portable, summary=data["summary"], samples=data["samples"])
        )
    return runs


def build():
    runs = load_runs()
    measured = [
        s
        for r in runs
        for s in r["samples"]
        if not s["warmup"] and s["operation"] != "client_start_and_exists"
    ]
    warmups = sum(s["warmup"] for r in runs for s in r["samples"])
    startup = sum(s["operation"] == "client_start_and_exists" for r in runs for s in r["samples"])
    small_rows, small_bars = [], []
    for op in ("attrs", "read", "tree_attrs"):
        old, new = [row_for(runs[4], op, c, 1024) for c in ("legacy", "genro")]
        small_rows.append(
            [
                OPS[op],
                number(old["median_ms"]),
                number(new["median_ms"]),
                number(old["http_per_op"], 0),
                number(new["http_per_op"], 0),
            ]
        )
        small_bars.append(
            bars(
                OPS[op],
                [("Legacy", old["median_ms"], "legacy"), ("Nuovo", new["median_ms"], "genro")],
            )
        )
    transfer_rows = []
    for op in ("read", "write", "copy", "move", "local_path"):
        transfer_rows.append(
            [OPS[op]]
            + [number(row_for(runs[4], op, c, 33554432)["median_ms"]) for c in ("legacy", "genro")]
        )
    version_rows = []
    for op in ("attrs", "listing", "tree_attrs"):
        version_rows.append(
            [OPS[op]]
            + [
                number(row_for(runs[2], op, c, 1024)["median_ms"])
                for c in ("genro", "genro-unversioned")
            ]
        )
    comparison_rows = []
    for row in runs[4]["summary"]:
        if row["adapter"] != "genro" or row["operation"] == "client_start_and_exists":
            continue
        old = row_for(runs[3], row["operation"], "genro", row["size_bytes"])
        legacy = row_for(runs[4], row["operation"], "legacy", row["size_bytes"])
        comparison_rows.append(
            [
                OPS[row["operation"]],
                size_label(row["size_bytes"]),
                number(old["median_ms"]),
                number(row["median_ms"]),
                number(legacy["median_ms"]),
                f"{old['http_per_op']:g} → {row['http_per_op']:g} / {legacy['http_per_op']:g}",
            ]
        )
    run_cards = []
    for index, run in enumerate(runs):
        p = run["metadata"]["parameters"]
        count = sum(
            not s["warmup"] and s["operation"] != "client_start_and_exists" for s in run["samples"]
        )
        run_cards.append(f"""<article class="run-card"><span class="index">0{index + 1}</span>
<h3>{esc(run["label"])}</h3><p class="run-sizes">{" / ".join(size_label(s) for s in p["sizes"])}</p>
<dl><div><dt>Client</dt><dd>{len({s["adapter"] for s in run["summary"]})}</dd></div>
<div><dt>Concorrenza</dt><dd>{" / ".join(map(str, p["workers"]))} worker</dd></div>
<div><dt>Ripetizioni</dt><dd>{p["repeats"]}</dd></div>
<div><dt>Directory</dt><dd>{p["list_count"]} file</dd></div>
<div><dt>Versioni per chiave</dt><dd>{p["history"]}</dd></div>
<div><dt>Campioni misurati</dt><dd>{number(count, 0)}</dd></div></dl>
<small class="run-id">{run["metadata"]["run_id"]}</small></article>""")
    verification = json.loads((ROOT / "report_assets" / "verification.json").read_text())
    test_rows = [
        [group["label"], group["count"], group["kind"], "Superato"]
        for group in verification["groups"]
    ]
    if sum(g["count"] for g in verification["groups"]) != verification["passed"]:
        raise ValueError("Verification counts do not add up")
    metadata = runs[4]["metadata"]
    versions = [["Genro Storage · sorgente misurato", metadata["genro_source_version"]]]
    versions += [
        [name, version] for name, version in metadata["versions"].items() if name != "genro-storage"
    ]
    versions += [
        ["Python", metadata["python"]],
        ["Sistema del client", metadata["platform"]],
        ["MinIO · immagine Compose", "RELEASE.2025-09-07T16-13-09Z"],
    ]
    provenance = []
    for run in runs:
        m = run["metadata"]
        provenance.append(
            f"<details><summary>{esc(run['label'])} · identificazione dei sorgenti</summary>"
            + '<dl class="hashes">'
            + "".join(
                f"<div><dt>{esc(key)}</dt><dd><code>{esc(m[key])}</code></dd></div>"
                for key in (
                    "run_id",
                    "genro_revision",
                    "genro_source_sha256",
                    "legacy_revision",
                    "legacy_service_sha256",
                    "benchmark_source_sha256",
                )
            )
            + "</dl></details>"
        )
    csv_output = io.StringIO(newline="")
    fields = (
        "run",
        "adapter",
        "operation",
        "size_bytes",
        "workers",
        "cache",
        "samples",
        "failed_samples",
        "median_ms",
        "p95_ms",
        "ops_s",
        "http_per_op",
        "logical_mib_s",
    )
    writer = csv.DictWriter(csv_output, fieldnames=fields)
    writer.writeheader()
    for run in runs:
        for row in run["summary"]:
            writer.writerow(dict(run=run["label"], **row))
    payload = dict(
        runs=runs,
        verification=verification,
        clients=CLIENTS,
        operations=OPS,
        csv=csv_output.getvalue(),
    )
    request_rows = []
    for client in ("legacy", "genro"):
        samples = [
            s
            for s in runs[4]["samples"]
            if s["adapter"] == client
            and s["operation"] == "tree_attrs"
            and s["workers"] == 1
            and s["cache"] == "cold"
            and not s["warmup"]
        ]
        calls = sum(s["calls"] for s in samples)
        counts = Counter()
        for s in samples:
            counts.update(s["requests"])
        request_rows.append(
            [CLIENTS[client]]
            + [
                number(counts[k] / calls, 1)
                for k in ("HeadObject", "ListObjectsV2", "ListObjectVersions")
            ]
            + [number(sum(counts.values()) / calls, 1)]
        )
    replacements = {
        "BATCH_COUNT": number(len(measured), 0),
        "CALL_COUNT": number(sum(s["calls"] for s in measured), 0),
        "WARMUP_COUNT": str(warmups),
        "STARTUP_COUNT": str(startup),
        "TEST_COUNT": str(verification["latest"]["passed"]),
        "COMPARISON_TABLE": table(
            [
                "Operazione",
                "Dimensione",
                "Nuovo prima · ms",
                "Nuovo dopo · ms",
                "Legacy dopo · ms",
                "HTTP prima → dopo / legacy",
            ],
            comparison_rows,
            "Prima/dopo · nove ripetizioni, 1 worker, cache fredda",
        ),
        "SMALL_CHARTS": "".join(small_bars),
        "SMALL_TABLE": table(
            ["Operazione", "Legacy · ms", "Nuovo · ms", "Legacy · HTTP/op", "Nuovo · HTTP/op"],
            small_rows,
            "Dopo ottimizzazione · file da 1 KiB e directory di 8 file · 9 ripetizioni",
        ),
        "TRANSFER_TABLE": table(
            ["Operazione", "Legacy", "Nuovo ottimizzato"],
            transfer_rows,
            "Dopo ottimizzazione · 32 MiB · mediana in ms, 1 worker, cache fredda",
        ),
        "VERSION_TABLE": table(
            ["Operazione", "Version awareness attiva", "Version awareness disattiva"],
            version_rows,
            "Cinque versioni per chiave · mediana in ms, 1 worker, cache fredda",
        ),
        "REQUEST_TABLE": table(
            ["Client", "HEAD", "LIST corrente", "LIST versioni", "Totale"],
            request_rows,
            "Richieste HTTP per albero completo di 8 file · 1 worker, cache fredda",
        ),
        "RUN_CARDS": "".join(run_cards),
        "TEST_TABLE": table(
            ["Controllo", "Casi", "Tipo", "Esito"],
            test_rows,
            "Dettaglio dei 18 test originari del benchmark, inclusi nella verifica finale",
        ),
        "VERSION_INFO": table(
            ["Componente", "Versione / ambiente"], versions, "Ambiente registrato nelle prove"
        ),
        "PROVENANCE": "".join(provenance),
        "PACKAGE_META_VERSION": esc(metadata["versions"]["genro-storage"]),
        "DATA": json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
            "<", "\\u003c"
        ),
        "BUILD_DATE": date.today().isoformat(),
    }
    template = (ROOT / "report_assets" / "template.html").read_text()
    for key, value in replacements.items():
        template = template.replace("@@" + key + "@@", value)
    if "@@" in template:
        raise ValueError("Unexpanded template placeholder")
    output = ROOT / "reports" / "storage-benchmark.html"
    output.parent.mkdir(exist_ok=True)
    output.write_text(template)
    print(f"{output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
