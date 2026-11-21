# Integrations-Cockpit Bern

[English](../README.md) · [Français](README.fr.md)

Ein Hackathon-Prototyp für den Asylsozialdienst der Stadt Bern. Das Cockpit liest die elf monatlichen Excel-Exporte und beantwortet drei Fragen:

- Wen kontaktiere ich diese Woche und warum?
- Wie viele Personen erreichen die Ziele fristgerecht, pro Fallführung und pro Einreisejahr?
- Was bringt das Erreichte ein, und was ändert 2027?

Alles läuft auf einem Rechner. Die Daten liegen in einer lokalen Datei, und der Browser lädt nichts von fremden Adressen.

## Starten

Benötigt wird Python 3.12 oder neuer. Zusätzliche Pakete sind nicht nötig.

```sh
python3 -m cockpit.server serve --demo
```

Danach <http://127.0.0.1:8000> öffnen. Beim ersten Start erscheinen Benutzername und Passwort einmalig im Terminal.

1. **Fallführung → Diese Woche:** rund 170 Kontakte, sortiert nach Wirkung.
2. **DEMO-00001 öffnen.** Im September ist A1 bis 16.10.2026 fällig. Nach dem Laden des Oktobers ist ein fide-Nachweis vom 12.10.2026 da, aber der offizielle Eintrag fehlt noch.
3. **Übersicht:**
   - Ist und Soll pro Fallführung und Einreisejahr.
   - Gruppenanalyse mit Unsicherheitsbereich: Sprachkurs in den ersten sechs Monaten 73 %, später 28 %.
4. **Planung:**
   - Abgeltung: 103 erreichte Ziele sind noch nicht abrechenbar.
   - Szenario 2027.
   - ZEMIS-Abgleich.
5. **Demo-Rolle** (unten in der Seitenleiste): Fallführung sieht nur eigene Fälle, Leitung nur Summen.
6. **Excel herunterladen:** echte Daten im Schweizer Format, mit Ampelfarben.

Das gelbe **!** neben jedem Bedienelement erklärt, was es tut. **Hilfe** und **Datenschutz** stehen in der Navigation.

Tests: `python3 -m unittest discover -s tests -v`

[Quellen und Regeln](SOURCES.md) · [Sicherheit](../SECURITY.md) · [Pitch](PITCH.md)
