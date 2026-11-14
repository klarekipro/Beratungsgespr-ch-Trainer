# Videoproduktion und Wiederverwendung

Status: Originalmaterial vollständig erhalten, **öffentliche Freigabe gesperrt**. Die bisherige Erlaubnis galt für PRIVATE Release. Die folgenden Schritte sind Anleitungen; bei dieser Vorbereitung wurde kein Film neu gerendert, transkodiert oder verändert.

## Unveränderte Originale

| Datei | Dauer | SHA-256 |
|---|---|---|
| `beratungstrainer_final_sergi2_fix1.mp4` | 05:08.23 | `acf507361f1e18da0698fa6676cd1d7a6cdd8fa44d7e1396541317064095e9d9` |
| `beratungstrainer_preview_rev01g.mp4` | 05:01.37 | `dc1b812f075cc13a808f43a0d4d344404e5427c58c3151b66a6fb7e3b5149084` |
| `BERATUNGSTRAINER_FINAL_ARCHIVE.zip` | 93 Dateien | `ccf0900314ae6e5f688fe75bb84151ab4cd77e21367975acca30893bfd34b7f9` |

Download: [Release v0.15.3](https://github.com/klarekipro/Beratungsgespr-ch-Trainer/releases/tag/v0.15.3). Derzeit nur mit Repository-Berechtigung. MP4-Assets werden als Attachment ausgeliefert; das ist kein geprüfter Inline-Player. Die Dateien gehören nicht in Git history.

## Wiederherstellen

ZIP und [SHA256SUMS](docs/releases/v0.15.3-SHA256SUMS.txt) aus dem Release herunterladen. Auf einem eigenen Arbeitsverzeichnis prüfen:

```sh
shasum -a 256 -c v0.15.3-SHA256SUMS.txt
unzip -t BERATUNGSTRAINER_FINAL_ARCHIVE.zip
unzip BERATUNGSTRAINER_FINAL_ARCHIVE.zip -d reedit
cd reedit/BERATUNGSTRAINER_FINAL_ARCHIVE
shasum -a 256 -c SHA256SUMS.txt
```

Der erste Check erwartet auch beide MP4 neben der Summendatei. Alle 90 Einträge des inneren Manifests wurden geprüft. Zusätzlich enthält das ZIP README, ARCHIVE_MANIFEST und SHA256SUMS selbst: insgesamt 93 Dateien. Die alten Archivtexte nennen stellenweise 75; tatsächlich sind es 90 Hash-Einträge. Originaltexte und Dateien bleiben als historische Produktionsunterlagen unverändert.

## Struktur

| Ordner | Inhalt |
|---|---|
| `01_FINAL_FILM/` | finaler Sergi-2-Master und Fix-/Montageberichte |
| `02_FIRST_VERSION/` | rev01g-Master, sechs ältere Chirp-MP3 und Block-Videos |
| `03_VIDEO_RAW/original/` | sechs Originalaufnahmen, `.steps.json`, Zertifikat-PDF und Abbildung |
| `03_VIDEO_RAW/final-recordings/` | sechs an die finale Erzählung angepasste stumme Videos, QA-Unterlagen |
| `04_VIDEO_WITH_AUDIO/` | sechs Block-Muxe mit Sergi-2-Audio; Block 3 ist ausdrücklich pre-fix1 |
| `05_AUDIO_FINAL/` | sechs unveränderte finale Sergi-2-MP3 |
| `06_SCRIPT/` | deutscher Sprechertext rev03 |
| `07_PRODUCTION/` | Aufzeichnung, Schnitt-/Fix-Skripte, Manifeste, Grafiken, ältere Montagepläne |

Blockreihenfolge: `01_mentor_overview`, `02_company_scenarios`, `03_learner_training`, `04_ai_review`, `05_mentor_review`, `06_certificate`.

## Einen Block ersetzen

1. Nur in einer **Arbeitskopie** arbeiten; Original-ZIP und Master unverändert behalten. Änderungen erzeugen neue Dateien und neue Prüfsummen.
2. Den passenden stummen Clip und das gleichnamige `.de.mp3` aus `05_AUDIO_FINAL/` auswählen. Mit lokalem FFmpeg/ffprobe Dauer, Bildformat und Bildrate prüfen. Die bestehenden finalen Clips sind 1920×1080 / 30 fps; der Master verwendet H.264 und AAC.
3. Eine neue Aufnahme oder einen geänderten Clip auf dieselben Sprecher-Cues abstimmen. Ein vorhandenes MP3 kann unverändert wiederverwendet werden; neue TTS-Aufrufe sind dafür nicht erforderlich. Neue Sprachsynthese wäre ein gesonderter, möglicherweise kostenpflichtiger Arbeitsschritt.
4. Video und MP3 mit FFmpeg oder einer Schnittsoftware in einen neuen Block muxen. Bei unterschiedlichen Längen nicht blind abschneiden: Cue-Übergänge und Audioende prüfen. Die Umwandlung von MP3 nach AAC verändert die Audio-Dateibytes und ist keine bitidentische Rekonstruktion.
5. Den neuen Block an derselben Stelle in eine neue Timeline setzen. Vor Stream-Copy-Verkettung müssen Codecparameter, Timebase und Tonspuren kompatibel sein; andernfalls wäre eine ausdrücklich freigegebene Neukodierung erforderlich.
6. Nach der Montage Gesamtdauer, alle sechs Blockgrenzen, Sprachwechsel, Hervorhebungen, Tonpegel, Sync und Zertifikat prüfen. Neue SHA-256 erstellen und als neue Fassung dokumentieren. Nicht die v0.15.3-Originalassets überschreiben.

## Vorhandene Skripte und Grenzen

`build_clips_v2.py` unterstützt `BLOCKS=3` für einen einzelnen Block sowie `RAW_DIR`, `AUDIO_DIR`, `CLIPS_DIR` und `V2_DIR`. Eingaben sind Originalaufnahme plus `.steps.json`; Ausgaben sind neue stumme Clips. Grafiken werden zusätzlich relativ zum Skript unter `assets/` erwartet; im Archiv liegen sie unter `07_PRODUCTION/graphics/`. Pfade müssen in einer Arbeitskopie passend eingerichtet werden. Das Skript nicht ungeprüft gegen den Archivordner ausführen.

`fix.py` erwartet ein Input-Verzeichnis als Argument und insbesondere `03_learner_training.muxed.mp4`, `04_ai_review.muxed.mp4` sowie `box_result.png` im Arbeitsverzeichnis. Im Archiv heißt Block 3 **`03_learner_training.muxed.pre-fix1.mp4`**; ein bloßes Concatenieren der sechs archivierten Muxe reproduziert daher nicht den finalen fix1-Master. Die Korrekturen des Sprachwechsels sind im finalen Master enthalten. Block 4 im Archiv ist bereits fix1; die Korrektur nicht blind doppelt anwenden. Fix-Evidence und Berichte beachten.

Die rev01g-Buildskripte verweisen auf historische Verzeichnisse, Assets und Narrations-Caches außerhalb ihrer jetzigen Archivposition. Die vorhandenen Block-Videos und MP3 erlauben manuelle Weiterverwendung; ein Start des alten Skripts ohne Pfadanpassung ist keine zugesicherte saubere Rekonstruktion. Eine vollständige Neuassemblierung auf einer leeren Maschine wurde **nicht durchgeführt**. Bitidentische Wiederherstellung wird nur für die gespeicherten Originaldateien anhand der SHA-256 bestätigt, nicht für neue Encoder-Ausgaben.

Die Aufzeichnungsskripte benötigen eine gesonderte Testinstallation und Zugangsdaten. Sie dürfen für einen Re-Edit nicht gegen die laufende Benutzerinstallation ausgeführt werden. Eine erneute Aufnahme könnte neue Daten und kostenpflichtige KI-Aufrufe auslösen; sie ist für die Wiederverwendung der vorhandenen Clips nicht erforderlich.

## Freigabe vor Veröffentlichung

Die Filme und das ZIP zeigen Konten, Gespräche, Bewertungen sowie Namen und Nummer eines Zertifikats. Auch Rohaufnahmen, QA-Bilder, PDF, Audio und historische Dokumente müssen in die Freigabe einbezogen werden. Die öffentliche Prüfung ist offen; die Zustimmung zum früheren PRIVATE Release ersetzt sie nicht. Eine Anonymisierung würde neue Medien und neue SHA-256 ergeben und ist derzeit nicht beauftragt.
