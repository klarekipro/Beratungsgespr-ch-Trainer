# Videoproduktion und Wiederverwendung

Status: Originalmaterial vollständig erhalten. Der Projekteigentümer hat Filme, Archiv und enthaltene Demonstrationsdaten am 14.11.2026 ausdrücklich zur öffentlichen Veröffentlichung freigegeben. Die folgenden Schritte sind Anleitungen; bei dieser Vorbereitung wurde kein v0.15.3-Film neu gerendert, transkodiert oder verändert. Für die v0.16.0-Musik-Fassung siehe den eigenen Abschnitt unten.

## Unveränderte Originale

| Datei | Release | Dauer | SHA-256 |
|---|---|---|---|
| `beratungstrainer_final_sergi2_music_v2.mp4` | v0.16.0 | 05:11.20 | `8709cdb2eef7f66e868f2f740e05e4b2db6dc4fda685adc2c88f09a1b387fce2` |
| `beratungstrainer_final_sergi2_fix1.mp4` | v0.15.3 | 05:08.23 | `acf507361f1e18da0698fa6676cd1d7a6cdd8fa44d7e1396541317064095e9d9` |
| `beratungstrainer_preview_rev01g.mp4` | v0.15.3 | 05:01.37 | `dc1b812f075cc13a808f43a0d4d344404e5427c58c3151b66a6fb7e3b5149084` |
| `BERATUNGSTRAINER_FINAL_ARCHIVE.zip` | v0.15.3 | 93 Dateien | `ccf0900314ae6e5f688fe75bb84151ab4cd77e21367975acca30893bfd34b7f9` |

Downloads: [Release v0.16.0](https://github.com/klarekipro/Beratungsgespr-ch-Trainer/releases/tag/v0.16.0) (Film mit Musik) · [Release v0.15.3](https://github.com/klarekipro/Beratungsgespr-ch-Trainer/releases/tag/v0.15.3) (Originalfilme, Archiv). Die Release-MP4 werden als Download ausgeliefert und spielen im Browser-Player ab. Eine zusätzliche unveränderte Kopie der v0.15.3-fix1-Fassung wurde als GitHub-Videoanhang bereitgestellt: [Browser-Video](https://github.com/user-attachments/assets/5b0ce12f-7d88-4dd9-83ae-2ece50a4428a). Die Dateien gehören nicht in die Git-Historie.

## Musik-Mix v2 (v0.16.0)

Die Musikfassung `beratungstrainer_final_sergi2_music_v2.mp4` verwendet dieselbe Sergi-2-Sprachausgabe wie `fix1.mp4` ohne jede Veränderung der Sprache selbst. Das Videoabspiel wurde um 3 Sekunden Freeze-Frame-Tail erweitert, damit die Musik am Ende ruhig ausklingen kann. Dafür wurde der Videostrom einmal mit libx264 bei CRF 20 re-enkodiert; die visuelle Qualität entspricht dem Originalfilm.

- **Musik:** MiroMaxMusic — *Technology*, Pixabay ID 629725, MP3 44.1 kHz stereo 256 kbps
- **Quellen-SHA:** `a84920928fe75d0ccdd30021dc0bb9929629a3b479eda57b6c1365a251e497e0`
- **Lizenz:** Pixabay Content License (kommerzielle Nutzung ohne Attributpflicht), vollständige Angaben in `MUSIC_LICENSING.md` im Release
- **Pegel:** Musik-Basis −22 dB, Sidechain-Ducking gegen die Stimme (Release 700 ms, kein Pumping), EQ-Notch −3 dB @ 2.5 kHz / −2 dB @ 4 kHz für bessere Sprachverständlichkeit, zusätzlicher Dip −6 dB bei 2:28–2:32 (natürlicher Musik-Swell), sanftes Outro-Swell 306–308.5 s, Fade-out 310–311.2 s
- **Keine Clippings:** True-Peak −4.3 dBFS, Integrated −23 dB mean, LRA 3.9 LU
- **Dokumentation:** `MIX_PROJECT_v2.md` im Release enthält alle Pegel und Filter-Parameter zur Reproduktion

Die Original-MP3 der drei Pixabay-Kandidaten werden als eigenständige Dateien nicht veröffentlicht. Das `fix1.mp4`-Original aus v0.15.3 bleibt unverändert.

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

## Beispiel: neue Fassung aus den vorhandenen Blöcken

Die folgenden Befehle wurden hier **nicht gerendert oder auf einer leeren Maschine getestet**. Sie erzeugen eine neue Schnittfassung, nicht den unveränderten fix1-Master. Voraussetzungen sind FFmpeg/ffprobe und die entpackten Quellen; im Stammordner `BERATUNGSTRAINER_FINAL_ARCHIVE` beginnen:

```sh
mkdir -p ../reedit-work/blocks
cp 04_VIDEO_WITH_AUDIO/*.mp4 ../reedit-work/blocks/
cp 05_AUDIO_FINAL/*.mp3 ../reedit-work/
cp 06_SCRIPT/beratungstrainer_sprechertext_rev03.md ../reedit-work/
cp -R 07_PRODUCTION/graphics ../reedit-work/
```

Die sechs Originalaufnahmen liegen weiterhin unverändert unter `03_VIDEO_RAW/original/*.raw.mp4`; die sechs stummen, bereits angepassten Clips unter `03_VIDEO_RAW/final-recordings/`. Für einen Blocktausch den passenden Clip als `replacement-silent.mp4` in `reedit-work` vorbereiten. Beispiel für Block 5 mit vorhandener Sergi-2-Vertonung, ausgeführt in `reedit-work`:

```sh
ffprobe -v error -show_entries format=duration -of csv=p=0 replacement-silent.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 05_mentor_review.de.mp3
ffmpeg -i replacement-silent.mp4 -i 05_mentor_review.de.mp3 \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
  blocks/05_mentor_review.replacement.mp4
```

Erst die Cues und Dauer prüfen; das Beispiel schneidet bewusst nicht automatisch mit `-shortest` ab. In einer neuen `blocks/concat.txt` die gewünschten sechs Dateien in dieser Reihenfolge aufführen; für Block 5 entweder Original oder geprüfte replacement-Datei auswählen:

```text
file '01_mentor_overview.muxed.mp4'
file '02_company_scenarios.muxed.mp4'
file '03_learner_training.muxed.pre-fix1.mp4'
file '04_ai_review.muxed.mp4'
file '05_mentor_review.replacement.mp4'
file '06_certificate.muxed.mp4'
```

Bei kompatiblen Streams lässt sich aus `reedit-work` eine neue Datei erstellen:

```sh
ffmpeg -f concat -safe 1 -i blocks/concat.txt -c copy beratungstrainer-reedit.mp4
shasum -a 256 beratungstrainer-reedit.mp4
```

Das verwendet **pre-fix1 Block 3**; die ursprünglichen Flash-Korrekturen des fix1-Masters fehlen in dieser einfachen Neuassemblierung. Für dieselben Korrekturen ist der unten beschriebene Fix-Workflow in einer Arbeitskopie anzupassen. Ein erfolgreicher FFmpeg-Lauf ersetzt keine Prüfung der Übergänge und Synchronität. Die Grafiken sowie der Sprechertext sind für weitere Fassungen beigefügt; alte WBS-Backup-Grafiken bleiben als historische Varianten erhalten.

## Vorhandene Skripte und Grenzen

`build_clips_v2.py` unterstützt `BLOCKS=3` für einen einzelnen Block sowie `RAW_DIR`, `AUDIO_DIR`, `CLIPS_DIR` und `V2_DIR`. Eingaben sind Originalaufnahme plus `.steps.json`; Ausgaben sind neue stumme Clips. Grafiken werden zusätzlich relativ zum Skript unter `assets/` erwartet; im Archiv liegen sie unter `07_PRODUCTION/graphics/`. Pfade müssen in einer Arbeitskopie passend eingerichtet werden. Das Skript nicht ungeprüft gegen den Archivordner ausführen.

`fix.py` erwartet ein Input-Verzeichnis als Argument und insbesondere `03_learner_training.muxed.mp4`, `04_ai_review.muxed.mp4` sowie `box_result.png` im Arbeitsverzeichnis. Im Archiv heißt Block 3 **`03_learner_training.muxed.pre-fix1.mp4`**; ein bloßes Concatenieren der sechs archivierten Muxe reproduziert daher nicht den finalen fix1-Master. Die Korrekturen des Sprachwechsels sind im finalen Master enthalten. Block 4 im Archiv ist bereits fix1; die Korrektur nicht blind doppelt anwenden. Fix-Evidence und Berichte beachten.

Die rev01g-Buildskripte verweisen auf historische Verzeichnisse, Assets und Narrations-Caches außerhalb ihrer jetzigen Archivposition. Die vorhandenen Block-Videos und MP3 erlauben manuelle Weiterverwendung; ein Start des alten Skripts ohne Pfadanpassung ist keine zugesicherte saubere Rekonstruktion. Eine vollständige Neuassemblierung auf einer leeren Maschine wurde **nicht durchgeführt**. Bitidentische Wiederherstellung wird nur für die gespeicherten Originaldateien anhand der SHA-256 bestätigt, nicht für neue Encoder-Ausgaben.

Die Aufzeichnungsskripte benötigen eine gesonderte Testinstallation und Zugangsdaten. Sie dürfen für einen Re-Edit nicht gegen die laufende Benutzerinstallation ausgeführt werden. Eine erneute Aufnahme könnte neue Daten und kostenpflichtige KI-Aufrufe auslösen; sie ist für die Wiederverwendung der vorhandenen Clips nicht erforderlich.

## Öffentliche Demonstrationsdaten

Die Filme und das ZIP zeigen Demonstrationskonten, Gespräche, Bewertungen sowie Namen und Nummer eines Zertifikats. Der Projekteigentümer hat die Veröffentlichung dieser Materialien einschließlich Rohaufnahmen, QA-Bildern, PDF, Audio, historischer Dokumente und Git-Historie ausdrücklich genehmigt. Zugangsdaten und aktive Geheimnisse sind von dieser Erlaubnis ausgenommen; sie gehören weder in das Archiv noch in Git.

Für neue Aufnahmen und neue Inhalte gilt die bisherige Freigabe nicht automatisch. Vor einer neuen Veröffentlichung müssen die tatsächlich sichtbaren Daten geprüft werden.
