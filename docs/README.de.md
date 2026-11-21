# Integrations-Cockpit Bern

[English](../README.md) · [Français](README.fr.md)

Der Hackathon-Prototyp verarbeitet elf monatliche Excel-Exporte des Asylsozialdienstes der Stadt Bern als gemeinsamen Stichtag. Er zeigt Fristen, Nachweise und nächste Prüfschritte pro autorisiertem Fall. Die Leitung erhält aggregierte Kennzahlen.

## Demo

[Temporärer HTTPS-Zugang](https://listening-brian-served-upcoming.trycloudflare.com/login). Zugangsdaten werden separat verteilt. Unter **Daten & Berichte** zuerst September 2026 wählen und Fall **DEMO-00001** öffnen. A1 ist bis 16. Oktober fällig. Nach dem Oktober-Import ist ein fide-Nachweis vom 12. Oktober sichtbar. Excel herunterladen, dann Kohorten, Regelassistent und Prognose ansehen.

## Lokal

Im Projektverzeichnis `python3 -m cockpit.server serve --demo` ausführen und http://127.0.0.1:8000 öffnen. Python 3.12+ genügt für die Kernabläufe. Die PDF-Analyse verwendet lokal Poppler oder macOS PDFKit. Tests laufen mit `python3 -m unittest discover -s tests -v`.

Sprachnachweise, Arbeit oder Ausbildung und die finanzielle Selbstständigkeit werden regelbasiert ausgewertet. Die Arbeitssicht ist auf Fälle der eigenen Zuständigkeit begrenzt. Die Prognose vergleicht rein aggregierte Monatszahlen mit einfachen Referenzmodellen. Der Assistent ruft geprüfte Quellen lokal ab. Die Demo verwendet synthetische Fallakten und zeigt öffentliche Vergleichszahlen mit separater Herkunft.

[Abnahme und offene Punkte](ACCEPTANCE.md) · [Quellen und Regeln](SOURCES.md) · [Sicherheit](../SECURITY.md)
