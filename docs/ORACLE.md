# Constituer un grand jeu de données de combats réels (oracle du moteur)

Le seul juge de paix des règles est le serveur d'Urban Rivals. Chaque combat joué dans le client web peut devenir un
test automatique : le moteur rejoue les mêmes choix et doit retrouver exactement les valeurs officielles de chaque
round. Ce document décrit la chaîne complète, du premier combat à des centaines.

## 0. Ce qu'on capture, et pourquoi c'est fiable

Le client web (`urban-rivals.com/game/play/`, Unity WebGL) interroge `POST /api/private/v2/` (`battles.status`) en
continu. À la résolution de chaque round, la réponse contient pour les deux cartes jouées : `roundPower`,
`roundDamage`, `roundAttack`, `roundWon`, `pillzUsed` (pillz gratuite comprise), `isFury`, et pour les joueurs `life`,
`pillz`, `postRoundAbilities`. Ce sont les valeurs calculées par le serveur — pas une interprétation.

Format d'un combat enregistré : `data/ur_battles/<battle_id>.json` (voir `1181426.json`). Le test
`tests/test_ur_battles.py` rejoue tous les fichiers du dossier ; `scripts/import_ur_battles.py` les importe et signale
le premier écart avec le journal des effets du moteur.

## 1. Préparer une session de capture (une fois par onglet)

1. Se connecter sur `urban-rivals.com`, ouvrir `/game/play/` → « Jouer » (application en navigateur).
2. Ouvrir la console du navigateur (F12 → Console) et coller **tout** `UrbanPy/Backend_fastAPI/scripts/ur_capture.js`.
   Il intercepte les réponses de l'API dans `window.__urCapture` et les sauvegarde toutes les 5 s dans `localStorage`.
3. Vérifier : après quelques secondes, `window.__urCapture.length` doit augmenter.

Si la page est rechargée : recoller le script puis exécuter `urRestore()` pour récupérer ce qui a été sauvegardé.

## 2. Jouer

Enchaîner les combats normalement (n'importe quel mode). Un combat dure ~4 minutes ; une session d'une heure donne une
dizaine de combats, soit 40 rounds vérifiés.

**Pour cibler une règle précise**, le mode le plus efficace est le **duel contre un ami** (ou un second compte) : on
choisit les deux decks et les deux mains, donc le scénario exact à tester. Points encore non tranchés (voir
`docs/REGLES.md` § 5 et § 6) :

| Question | Scénario à jouer |
|---|---|
| Cycles de Stops | GHEIST ou Roots (SoA en bonus) contre Nightmare ou Piranas (SoB en bonus) ; Skeelz + ability Protection: Bonus contre un All-Stop (Glorg, Shakra) |
| Le Leader profite-t-il de son Team ? | jouer Ambre / Eyrik / Vholt lui-même |
| Tune Out et fury | Cosmohnuts avec fury contre un adversaire à une pillz de plus |
| Mindwipe vs Combust | une carte de chaque, observer les deux rounds suivants |
| Limitless | Fractal en main + allié « −X Opp Damage, Min Y » gagnant |
| Exchange contre Copy / Annul | Dominion « Damage Exchange » contre « Copy: Opp. Damage » puis contre « Cancel Opp. Damage Modif. » |
| Repair (immédiat ou différé ?) | une carte Repair gagnante, pillz au round même |
| Combust / Mindwipe : immédiats ? | idem, vie et pillz au round même |

## 3. Exporter

Dans la console, à la fin de la session :

```js
copy(urRecords())      // tous les combats de la session, un enregistrement par combat
```

Coller le contenu dans un fichier, par exemple `records.json`. Optionnel : `copy(urAbilities())` donne le modèle
`abilityData` des pouvoirs rencontrés (`docs/ur-abilitydata-modele.md`).

## 4. Importer et vérifier

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python scripts/import_ur_battles.py records.json
```

Sortie : une ligne par combat, `OK` ou `ÉCART` avec le round fautif, les valeurs attendues / obtenues et le journal
des effets du moteur pour ce round. Les fichiers sont déposés dans `data/ur_battles/`.

Puis `pytest tests/test_ur_battles.py` : chaque combat est un test ; **commiter les fichiers** — le jeu de données
grandit avec le dépôt et la CI le rejoue à chaque changement du moteur. C'est ce qui garantit que « rien ne casse ».

## 5. Traiter un écart

1. Lire le journal du round fautif (affiché par l'import) : il montre chaque effet appliqué avec avant → après.
2. Identifier la règle en cause ; consulter `docs/REGLES.md` et `docs/REGLES-glossaire-officiel.md`.
3. Corriger en TDD : d'abord un test unitaire ciblé (rouge), puis le moteur, puis `pytest` complet — le combat réel
   repasse au vert avec tous les autres.
4. Consigner la règle apprise dans `docs/REGLES.md` (§ 6) et, si la roadmap listait le point comme ouvert, le fermer.

## 6. Monter en volume

- **Sessions longues** : le script tient toute la session tant que l'onglet reste ouvert ; `localStorage` garde
  ~5 Mo, soit des dizaines de combats. Exporter et importer à chaque session.
- **Deux comptes / un ami** : couverture systématique des mécaniques (un deck par famille : Stops, persistants,
  Leaders, Oculus, Cosmohnuts…). Quatre rounds par combat, quatre cartes par main : un deck bien composé teste 4 à 8
  pouvoirs par combat.
- **Mesurer la couverture** : `scripts/capacity_coverage.py` liste les descriptions ; un script de couverture
  d'oracle (à écrire) peut croiser les cartes vues dans `data/ur_battles/` avec les 1 396 descriptions pour dire quels
  pouvoirs n'ont jamais été observés en combat réel.
- **Le modèle `abilityData`** : si un appel API renvoie ce modèle pour toutes les cartes (probablement une méthode
  `characters.*`), un scraping en session connectée donne un parseur exact par construction, et les combats réels
  n'ont plus qu'à valider l'ordre d'application. Spike à faire : observer le corps des requêtes du client pour
  connaître la convention d'appel.

## 7. Limites connues

- L'état `done` ne reflète pas la dernière perte de vie (KO) : le dernier round n'est vérifié que sur ses valeurs de
  cartes, pas sur les vies finales.
- Les modes à règles spéciales (`battleRuleId` autre que le classique, vies ≠ 12/14, bonus modifiés) doivent être
  identifiés avant d'être ajoutés : le moteur ne modélise que le gameplay classique.
- `Day:` / `Night:` dépendent de l'heure du jeu ; un combat de nuit avec des GhosTown produira des écarts attendus.
