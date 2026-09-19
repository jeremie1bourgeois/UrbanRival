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
| Mindwipe vs Combust | une carte de chaque, observer les deux rounds suivants |
| Limitless | Fractal en main + allié « −X Opp Damage, Min Y » gagnant |
| Exchange contre Copy / Annul | Dominion « Damage Exchange » contre « Copy: Opp. Damage » puis contre « Cancel Opp. Damage Modif. » |
| Repair (immédiat ou différé ?) | une carte Repair gagnante, pillz au round même |
| Combust / Mindwipe : immédiats ? | idem, vie et pillz au round même |

### Decks prêts à jouer (2026-09-16)

Un duel = deck A (vous) contre deck B (l'ami / le second compte), 8 cartes chacun composées autour du scénario pour que
tout tirage de 4 convienne. Les cartes sont choisies petites (2-3★) et fréquentes ; remplacer par une équivalente
(même pouvoir) si elle manque. Les stats sont celles du niveau max.

| # | Question | Deck A | Deck B | Consigne par round |
|---|---|---|---|---|
| D1 | **SoA contre SoA** (cycle pur) et SoA contre SoB en ability | 4 × SoA en ability : Angelo (Montana), Cardigan, Cesare (All Stars), Jean (Jungo) + 4 × SoB en ability : Bol, Flo Cr (All Stars), Flanagan (Junkz), Borss (Jungo) | idem, autres clans : Doggonuts (Cosmohnuts), Graff Cr (Bangers), Guiliug (Dominion), Liam (Skeelz) + Angora (Vortex), Graziella (Freaks), Hella (Paradox), Globumm Cr (Sakrohm) | jouer SoA contre SoA, puis SoA contre SoB, puis SoB contre SoB ; 1-2 pillz, noter puissance finale des deux cartes |
| D2 | **All-Stop contre Protection: Ability** (Skeelz) et chaîne GHEIST/Roots contre Nightmare/Piranas | 8 Skeelz avec pouvoirs de stats visibles (bonus Protection: Ability), ex. Liam + n'importe quels Skeelz « Power +X » / « Damage +X » | Glorg, Dieter (Nightmare), Spycee, Yaccanemba (Piranas) + Morlha, XU-Dr0ne, Leviatonn Cr (GHEIST), Nahi Cr (Roots) | chaque Skeelz contre un All-Stop : le pouvoir Skeelz doit tomber (SoB retire la Protection, puis SoA passe) ; puis GHEIST contre Piranas entre eux |
| D3 | **Le Leader profite-t-il de son Team ?** + Solomon (Tie-break) + Ashigaru (Counter-attack) | Ambre, Eyrik, Vholt, Timber, Hugo + 3 cartes quelconques d'un même clan | Solomon, Ashigaru + 6 cartes quelconques | jouer **le Leader lui-même** (Ambre avec Courage, Eyrik…) et lire sa puissance/dégâts ; provoquer une égalité d'attaque contre Solomon ; observer qui joue en premier avec Ashigaru en main |
| D4 | Consume/Combust/Mindwipe immédiats ? (Tune Out et fury : tranché par le combat 1248952) | 8 Cosmohnuts : Bobby Cornteeth (Players Combust), Colton, Cosmo Curcan, Curcan Noel, Doggonuts, Jacob, Maraval, Paw Paw | Prince Candle (Combust, Skeelz), Virtmund (Mindwipe, GHEIST), Hoffman, Wave Ld (Consume), H4rp3r (Toxin), Artax (Poison), Wilo Ld (Repair), Fletcher (Cancel Life Modif.) | faire gagner Combust / Mindwipe / Consume / Repair et lire vies et pillz **au round même** puis au suivant ; Fletcher contre un poison posé au round précédent |
| D5 | **Limitless** (Fractal) et bornes | Fractal + 7 réducteurs à minimum : Arno, Artus, Ashley, B Ball, Ella, Kit-E, Klaus | 8 cartes à gros dégâts quelconques | faire gagner un réducteur avec Fractal en main : le minimum doit tomber à 0 ; vérifier que le bonus (ex. Pussycats -2 min 1) n'est pas touché |
| D6 | **Exchange contre Copy / Annul** | Blast, Blackfin, Cerra, Fink Cr, Homy, Taki (Damage Exchange), Bruno, Calamity (Power Exchange) | Angelina, Bettisia, Darril, Dash (Copy: Opp. Damage) + Shaker, Lenora (Cancel Opp. Damage Modif.) + Zwoosh, Zombiyaki (Power Impose) | Exchange contre Copy (qui l'emporte ?), Exchange contre Annul (annulé ?), Exchange contre Impose |
| D7 | **Conditions numériques** : Perfect, Bet, Per Pillz Left, Cards | Cyloxxt, Hula, Akirale, Dr Horatio (Perfect) + Scooty, Kent, Hundun (Per Pillz Left) + Rajesh (-2 Cards Damage, Min 4) | Imbris Cr, Flotillo, Slatka, Ziwi (Zenith, Bet > N) + Giovanni, Merrick Cr (Cards) + 2 quelconques | Perfect : gagner avec exactement la pillz nécessaire, puis une de trop ; Bet : miser exactement N pillz (gratuite comprise) puis N+1 ; Per Pillz Left : lire l'attaque au round 1 |
| D8 | **Clans à condition de main** : Oculus, Tolvack (After), Unison, Xantiax/Corrupt/Corrosion | 1 Oculus (Dark Nunavik, Dark Kupanda…) + 3 cartes d'un clan qu'il infiltre + Frau Vanda, Rauta (Tolvack) + Jamtiax, Cameron | Almastine, Aquiline, Caballine, Carcharine (Unison, mono-clan impossible → tester la **non-activation**) + 4 quelconques | Oculus : main 1 Oculus + 3 clan X (bonus adopté), puis 2 + 1 (carte seule) ; After : jouer Tolvack après une carte du clan indiqué ; Xantiax/Corrosion : vies des deux joueurs en fin de round |

Ordre de rentabilité : D4 (3 questions ouvertes en un duel), D1, D3, D6, puis D5, D7, D8, D2.

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
- **Le modèle `abilityData`** s'accumule **passivement** : chaque combat capturé livre la fiche structurée des 8
  pouvoirs et 8 bonus en jeu (`urAbilities()`). Ne pas chercher à l'obtenir par des appels API directs : le spike du
  2026-09-16 a montré que `characters.get` (catalogue) ne contient pas `abilityData`, qu'aucune méthode dédiée
  connue n'existe, et que trouver son nom demanderait de fouiller le code du client — ce qui sort de la lecture
  passive et expose le compte. Le jeu de données de combats reste le juge de l'ordre d'application, ce que
  `abilityData` ne dirait de toute façon pas.

## 7. Limites connues

- L'état `done` ne reflète pas la dernière perte de vie (KO) : le dernier round n'est vérifié que sur ses valeurs de
  cartes, pas sur les vies finales.
- Les modes à règles spéciales (`battleRuleId` autre que le classique, vies ≠ 12/14, bonus modifiés) doivent être
  identifiés avant d'être ajoutés : le moteur ne modélise que le gameplay classique.
- `Day:` / `Night:` dépendent de l'heure du jeu ; un combat de nuit avec des GhosTown produira des écarts attendus.
