# Cockpit d’intégration de Berne

[English](../README.md) · [Deutsch](README.de.md)

Ce prototype de hackathon rapproche onze exports Excel mensuels du service social de l’asile de la Ville de Berne. Il présente les échéances, les justificatifs et les prochaines vérifications pour les dossiers autorisés. La direction consulte des indicateurs agrégés.

## Démonstration

[Accès HTTPS temporaire](https://listening-brian-served-upcoming.trycloudflare.com/login). Les identifiants sont transmis séparément. Dans **Données et rapports**, charger septembre 2026 puis ouvrir **DEMO-00001**. Le délai A1 est le 16 octobre. Après l’importation d’octobre, un justificatif fide daté du 12 octobre apparaît. Télécharger Excel puis explorer les cohortes, les règles et les prévisions.

## Exécution locale

Dans le répertoire du projet, lancer `python3 -m cockpit.server serve --demo`, puis ouvrir http://127.0.0.1:8000. Python 3.12+ suffit pour les fonctions principales. L’analyse PDF emploie Poppler ou PDFKit sur macOS. Exécuter les tests avec `python3 -m unittest discover -s tests -v`.

Le prototype applique des règles explicites aux objectifs de langue, d’emploi ou de formation et d’autonomie financière. L’accès individuel est limité aux dossiers attribués. Les prévisions portent sur des séries mensuelles agrégées avec des modèles de référence. L’assistant consulte localement les références approuvées. Les dossiers de démonstration sont synthétiques et les comparaisons publiques indiquent leur provenance.

[Périmètre et vérification](ACCEPTANCE.md) · [Sources et règles](SOURCES.md) · [Sécurité](../SECURITY.md)
