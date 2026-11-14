# Öffentliche Portfoliofreigabe — 14.11.2026

**Abnahme: PASS.** Das bestehende Repository `klarekipro/Beratungsgespr-ch-Trainer` ist PUBLIC. Keine neue Anwendung wurde bereitgestellt; es handelt sich weiterhin um einen lokal ausführbaren MVP.

## Veröffentlichung und Historie

Portfolio-PR: [#4](https://github.com/klarekipro/Beratungsgespr-ch-Trainer/pull/4), normaler Merge-Commit [`b6c0d1488a71487cd968e8b82525c4d82663b99c`](https://github.com/klarekipro/Beratungsgespr-ch-Trainer/commit/b6c0d1488a71487cd968e8b82525c4d82663b99c). Keine Squash-/Rebase-/Force-Push-Operation und keine Löschung historischer Branches. Alle zuvor vorhandenen Branch-/Tag-Refs wurden verglichen: erhalten. Der Tag `v0.15.3` bleibt auf `a23410a84a7c38572260b0fa48411104003b5b05`; neuere main-Commits ergänzen ausschließlich Portfolio und Dokumentation.

Backend, Frontend, Skripte, Materialien und Tests sind gegenüber dem angenommenen lokalen Quellstand `28e2a66887949eb999de67066e92f1a75f1b1e2f` unverändert. Version des laufenden MVP: **0.15.3-persona-localization**. Die lokale Anwendung wurde nicht neu gestartet oder umkonfiguriert. Die sieben geschützten SQLite-Tabellen wurden read-only mit dem Backup verglichen: unverändert. Kein Keychain-Zugriff und kein kostenpflichtiger KI-Aufruf.

## Sicherheit und Freigabeumfang

Der Eigentümer hat den vorherigen Audit von 113 Commits / 1 186 Blob-Versionen angenommen und Source, Entwicklungshistorie, historische Bilder/PDF sowie Demonstrationskonten, Gespräche, Bewertungen, Zertifikatsdaten, beide Filme und ZIP ausdrücklich für PUBLIC freigegeben. Die frühere PRIVATE-only-Freigabe ist damit ersetzt. Die Erlaubnis gilt nicht für aktive Zugangsschlüssel.

Der neue PR-Diff enthält nur Markdown und fünf PNG (vier Original-UI-Ansichten plus Titel-Preview). Prüfung auf bekannte Credential-Muster und SQLite-Dateien: keine Treffer. Keine MP4/MP3/ZIP, Arbeitsdatenbank oder runtime-Dateien wurden in die neuen Git-Commits aufgenommen. Die Freigabe ist kein Versprechen, dass jede denkbare Sicherheitsklasse vollständig geprüft wurde; insbesondere wurde der frühere begrenzte visuelle Audit nicht nachträglich als vollständige Einzelprüfung aller historischen Bilder ausgegeben.

## Anonymer Zugriff

Ohne GitHub-Token, Login oder vorhandene Browser-Cookies geprüft:

- Repository, deutsche README, Architektur, Backend-Quelldatei, VIDEO_PRODUCTION, Release und PR: HTTP 200.
- Alle fünf Portfolio-PNG: HTTP 200 und SHA-256-Gleichheit mit den committed Dateien. Vier UI-Bilder zusätzlich im GitHub-README sichtbar und geladen.
- Öffentlicher Git-Lesezugriff ohne Credential Helper: erfolgreich; alte Branches und Tag erhalten.
- Beide Release-Filme und Produktions-ZIP: vollständig anonym gestreamt, Bytezahl und SHA-256 geprüft; keine vollständigen zusätzlichen Mediendateien gespeichert.
- GitHub-native Videokopie: vollständig anonym geladen und ebenfalls SHA-256-identisch mit dem finalen Release-Film.

## Browser-Video

[GitHub-Video](https://github.com/user-attachments/assets/5b0ce12f-7d88-4dd9-83ae-2ece50a4428a) ist als Player in der README eingebettet. Test in einem neuen Browserkontext mit **0 anfänglichen Cookies**: Wiedergabe gestartet, Playhead auf 1,67 Sekunden fortgeschritten, 1920×1080 erkannt, Dauer 308,225717 Sekunden, kein Media-Fehler. Der automatisierte Test war stummgeschaltet; eine erneute komplette fünfminütige Sicht-/Hörabnahme wird nicht behauptet. Der vollständige Dateidownload wurde separat per Hash geprüft.

Die ursprünglichen Release-MP4 werden weiterhin als Download ausgeliefert. README bietet daneben den Browser-Link und einen Original-Download als Fallback. Keine Drittanbieter-Videoplattform und keine Transkodierung wurden verwendet.

## Unveränderte SHA-256

| Material | SHA-256 |
|---|---|
| `beratungstrainer_final_sergi2_fix1.mp4` | `acf507361f1e18da0698fa6676cd1d7a6cdd8fa44d7e1396541317064095e9d9` |
| `beratungstrainer_preview_rev01g.mp4` | `dc1b812f075cc13a808f43a0d4d344404e5427c58c3151b66a6fb7e3b5149084` |
| `BERATUNGSTRAINER_FINAL_ARCHIVE.zip` | `ccf0900314ae6e5f688fe75bb84151ab4cd77e21367975acca30893bfd34b7f9` |

Release und seine vier vorhandenen Assets (inklusive Summendatei) bleiben erhalten. Titel/Beschreibung wurden um die öffentliche Freigabe ergänzt; die früheren privaten Übergabenotizen bleiben als Historie enthalten.

## Wiederverwendung und Grenzen

[VIDEO_PRODUCTION.md](../VIDEO_PRODUCTION.md) erklärt die sechs Originalaufnahmen, sechs Blöcke, Sergi-2-MP3, Sprechertext, Grafiken, Blocktausch und Montagebeispiele. Keine saubere Neuassemblierung auf einer leeren Maschine durchgeführt. Der archivierte Block 3 ist pre-fix1; einfaches Concatenieren reproduziert nicht den fix1-Master. Neue Encoderausgaben benötigen eigene Prüfsummen.

DATA-001 bleibt OPEN; semantische KI-Belege, Coaching, wiederholte Abschlüsse, intermittierende Auswertungsfehler sowie Browser-/Mikrofon-/Druck- und Admin-Backlogs bleiben dokumentierte MVP-Grenzen. Keine Cloud-Bereitstellung und kein Transfer nach Herman879 ausgeführt.
