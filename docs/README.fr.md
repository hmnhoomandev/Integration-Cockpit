# Integrations-Cockpit Bern

[English](../README.md) · [Deutsch](README.de.md)

Prototype de hackathon pour le service social de l’asile de la Ville de Berne. Le cockpit lit les onze exports Excel mensuels et répond à trois questions :

- Qui contacter cette semaine, et pourquoi ?
- Combien de personnes atteignent les objectifs à temps, par gestionnaire et par année d’arrivée ?
- Que rapportent les objectifs atteints, et que change 2027 ?

Tout fonctionne sur un seul ordinateur. Les données restent dans un fichier local, et le navigateur ne charge rien depuis d’autres adresses.

## Démarrer

Il faut Python 3.12 ou plus récent, sans paquet supplémentaire.

```sh
python3 -m cockpit.server serve --demo
```

Ouvrez ensuite <http://127.0.0.1:8000>. Au premier démarrage, l’identifiant et le mot de passe s’affichent une seule fois dans le terminal.

1. **Suivi des dossiers → Cette semaine :** environ 170 contacts, classés par effet.
2. **Ouvrir DEMO-00001.** En septembre, l’A1 est dû le 16.10.2026. Après le chargement d’octobre, une attestation fide du 12.10.2026 est arrivée, mais la saisie officielle manque encore.
3. **Vue d’ensemble :**
   - objectif et réalisé par gestionnaire et par année d’arrivée ;
   - analyse de groupes avec intervalles : cours de langue dans les six premiers mois 73 %, plus tard 28 %.
4. **Planification :**
   - paiements ;
   - scénario 2027 ;
   - contrôle ZEMIS.
5. **Rôle de démo** (en bas de la barre latérale) : les gestionnaires voient leurs dossiers, la direction seulement des totaux.
6. **Télécharger Excel :** vraies dates au format suisse, avec les couleurs des feux.

Le **!** jaune à côté de chaque commande explique son rôle. **Aide** et **Protection des données** se trouvent dans la navigation.

Tests : `python3 -m unittest discover -s tests -v`

[Sources et règles](SOURCES.md) · [Sécurité](../SECURITY.md) · [Pitch](PITCH.md)
