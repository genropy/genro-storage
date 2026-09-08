"""Build the first optimization comparison from recorded before/after runs."""

import html
import json
from pathlib import Path

from .html_report import number, table

ROOT = Path(__file__).resolve().parent
BEFORE = "before-quiet/72a82c23-9820-47e7-b0d2-42111d865a09"
AFTER = "after-quiet/dac69290-2cbe-4b30-b484-4fedd4201269"


def build():
    runs = []
    for key in (BEFORE, AFTER):
        data = json.loads((ROOT / "results" / key / "results.json").read_text())
        assert data["metadata"]["status"] == data["metadata"]["cleanup"] == "complete"
        assert not any(s["errors"] for s in data["samples"])
        data["metadata"] = {
            k: v
            for k, v in data["metadata"].items()
            if k not in ("genro_source", "endpoint_host", "bucket", "prefix")
        }
        runs.append(data)

    def row(run, op, size, client):
        return next(
            r
            for r in runs[run]["summary"]
            if r["operation"] == op
            and r["size_bytes"] == size
            and r["adapter"] == client
            and r["workers"] == 1
            and r["cache"] == "cold"
        )

    labels = {
        "attrs": "Attributi",
        "read": "Lettura",
        "write": "Scrittura",
        "copy": "Copia",
        "move": "Spostamento",
        "tree_attrs": "Albero con attributi",
        "exists": "Esistenza",
        "listing": "Listing",
        "local_path": "File temporaneo",
    }
    sections = []
    for size, ops in [
        (1024, list(labels)),
        (33554432, ["read", "write", "copy", "move", "local_path"]),
    ]:
        rows = []
        for op in ops:
            before, after, legacy = (
                row(0, op, size, "genro"),
                row(1, op, size, "genro"),
                row(1, op, size, "legacy"),
            )
            rows.append(
                [
                    labels[op],
                    number(before["median_ms"]),
                    number(after["median_ms"]),
                    number(legacy["median_ms"]),
                    f"{before['http_per_op']:g} → {after['http_per_op']:g} / {legacy['http_per_op']:g}",
                ]
            )
        sections.append(
            table(
                [
                    "Operazione",
                    "Nuovo prima · ms",
                    "Nuovo dopo · ms",
                    "Legacy dopo · ms",
                    "HTTP prima → dopo / legacy",
                ],
                rows,
                "1 KiB; directory di 8 file" if size == 1024 else "32 MiB",
            )
        )
    style = (
        (ROOT / "report_assets" / "template.html")
        .read_text()
        .split("<style>")[1]
        .split("</style>")[0]
    )
    provenance = "".join(
        f"<p><strong>{label}</strong><br>Run <code>{d['metadata']['run_id']}</code><br>"
        f"Hash sorgente <code>{html.escape(str(d['metadata'].get('genro_source_sha256')))}</code></p>"
        for label, d in zip(["Prima", "Dopo"], runs)
    )
    snapshot = {
        "runs": runs,
        "verification": {
            "original_contract": {"passed": 10, "failed": 4},
            "final_suite": {"passed": 584, "skipped": 14},
            "scope": "S3 basic operations, versioned and unversioned; not full legacy API parity",
        },
    }
    output = ROOT / "reports"
    output.mkdir(exist_ok=True)
    (output / "optimization-round-1.json").write_text(json.dumps(snapshot, indent=2))
    document = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Genro Storage — prima ottimizzazione verificata</title><style>{style}</style></head>
<body><header class="hero"><div class="wrap"><p class="eyebrow">Benchmark S3 · prima / dopo</p>
<h1>Una richiesta.<br><em>Stesso risultato.</em></h1>
<p class="lede">Prima iterazione: test contro il legacy, correzione dei metadati e misura delle prestazioni.
StorageNode e backend fsspec/s3fs restano in uso.</p></div></header>
<main class="wrap"><section class="section"><p class="eyebrow">Risultato dimostrato</p>
<h2>Gli attributi ora superano il legacy.</h2>
<p class="lede">Nuovo prima: <strong>6,70 ms</strong>. Nuovo dopo: <strong>1,52 ms</strong>.
Legacy nello stesso run finale: <strong>3,27 ms</strong>. Le richieste per il nuovo scendono da quattro a una.</p>
<div class="note">È una conclusione sugli attributi del singolo file in questo ambiente.
Copia e spostamento rimangono più lenti. Le variazioni nelle operazioni non modificate
non sono attribuibili a questa ottimizzazione.</div></section>
<section class="section"><h2>Prima i test, poi la modifica.</h2>
<div class="grid two" style="margin-top:24px">
<article class="card"><h3>Sorgente originale</h3><p>Gli stessi test differenziali danno
<strong>10 passati e 4 falliti</strong>: due casi per la data delle directory e due per le
quattro richieste di metadati, con e senza versioning.</p></article>
<article class="card"><h3>Sorgente modificato</h3><p>Tutti i 14 test differenziali passano.
La suite finale comprende <strong>584 test passati e 14 saltati</strong>.
I salti non sono successi: comprendono servizi opzionali assenti, configurazioni mancanti e un bug preesistente di <code>S3 set_metadata</code>.</p></article></div>
<p class="lede">I contratti verificati coprono file vuoti, binari, file da 64 KiB, nomi Unicode e spazi,
letture e file temporanei, assenza, directory implicite, sovrascritture, copie,
spostamenti, cancellazioni e metadati dopo invalidazione. Ogni caso S3 usa servizi reali
e bucket isolati, versionati e non versionati.</p>
<p class="small-note">Il test preesistente dei 1.001 file continua a rifiutare il listing incompleto del legacy:
non abbiamo riprodotto quel limite nel nuovo. Questa matrice non certifica la parità dell'intera API legacy.</p>
</section><section class="section"><h2>Le modifiche in Genro Storage.</h2>
<ul><li>StorageNode richiede al backend una tupla di attributi; fsspec risponde con una sola <code>info()</code>.</li>
<li>Il contratto base conserva una implementazione di fallback per gli altri backend.
I mount relativi delegano al genitore mantenendo il prefisso.</li>
<li>Per le directory S3 gli attributi restituiscono <code>(None, None, True)</code>, come il legacy,
senza inventare una data. Il metodo separato <code>mtime()</code> conserva il comportamento precedente.</li>
<li>Non viene aggiunta una cache persistente; gli errori di permesso continuano a propagarsi.</li>
<li>Pytest importa il checkout <code>src</code>, evitando confusione con una distribuzione installata.</li></ul>
</section><section class="section"><h2>Tutti i casi confrontati.</h2>
<p class="lede">Mediane di nove ripetizioni dopo un warmup; un worker; cache dei metadati fredda.
Ogni run include entrambi i client, con ordine dei casi rimescolato. Nessun test di integrazione
è stato eseguito in contemporanea con le due raccolte qui riportate.</p>
{"".join(sections)}
<div class="note">Le due raccolte sono sequenziali: carico di sistema e stato delle cache del server possono cambiare.
I nove campioni non costituiscono una garanzia di tempi in produzione. Su Hetzner non abbiamo ancora misurato.</div>
</section><section class="section"><h2>Che cosa resta da verificare.</h2>
<p class="lede">La prima prova dimostra che intervenire soltanto su Genro Storage può eliminare
uno svantaggio rispetto al legacy. Non dimostra ancora la stessa cosa per tutte le operazioni.</p>
<p>Copia e spostamento conservano rispettivamente 6 e 10 richieste, contro 3 e 6 del legacy.
Prima di specializzarli occorre estendere i contratti a directory di destinazione esistenti,
copie ricorsive, collisioni fra chiavi e prefissi ed errori. I trasferimenti grandi richiedono
più raccolte e un profilo dei tempi: il numero di richieste da solo non spiega tutti gli scarti.</p>
</section><section class="section"><h2>Provenienza e riproducibilità.</h2>{provenance}
<p>I dati grezzi e i metadati delle due raccolte sono disponibili nel
<a href="optimization-round-1.json">JSON della prima ottimizzazione</a>.
Entrambe sono concluse senza campioni errati e con pulizia completata.
La raccolta preliminare <code>33e21eba-3441-4b80-9cfe-0aefc7a03b37</code>,
sovrapposta ai test iniziali, è esclusa dal confronto.</p>
<pre><code>BENCH_LEGACY_ROOT=/percorso/genropy python -m benchmarks \
  --adapters legacy genro --sizes 1024 33554432 \
  --workers 1 --repeats 9 --list-count 8 --caches cold

MINIO_ENDPOINT=http://127.0.0.1:29000 \
BENCH_TEST_ENDPOINT=http://127.0.0.1:29000 \
BENCH_LEGACY_ROOT=/percorso/genropy \
python -m pytest tests benchmarks/tests -q -o addopts=''</code></pre>
</section><footer class="footer"><a href="storage-benchmark.html">Report esplorativo originale</a>
<p>Documento offline · MinIO locale · prima ottimizzazione</p></footer></main></body></html>"""
    path = output / "optimization-round-1.html"
    path.write_text(document)
    print(path)


if __name__ == "__main__":
    build()
