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

| Question | Scénario à jouer | État (2026-09-17) |
|---|---|---|
| Cycles de Stops | GHEIST ou Roots (SoA en bonus) contre Nightmare ou Piranas (SoB en bonus) ; Skeelz + ability Protection: Bonus contre un All-Stop (Glorg, Shakra) | chaîne SoA/SoB **tranchée** (`1210477`, `1211029`, `1210625`) ; reste Protection contre All-Stop (D2) |
| Le Leader profite-t-il de son Team ? | jouer Ambre / Eyrik / Vholt lui-même | ouvert (D3) |
| Tune Out et fury | Cosmohnuts avec fury contre un adversaire à une pillz de plus | **tranché** : fury exclue, puissances à 1 (`1211279`, `1211570`) |
| Mindwipe vs Combust | une carte de chaque, observer les deux rounds suivants | **tranché** : Mindwipe immédiat, Combust différé (`1211279`, `1211702`) |
| Limitless | Fractal en main + allié « −X Opp Damage, Min Y » gagnant | non réalisable (Fractal absente) |
| Exchange contre Copy / Annul | Dominion « Damage Exchange » contre « Copy: Opp. Damage » puis contre « Cancel Opp. Damage Modif. » | ouvert (D6) |
| Repair (immédiat ou différé ?) | une carte Repair gagnante, pillz au round même | **tranché** : immédiat, vie **et** pillz (`1211702`, `1211922`) |
| Combust / Mindwipe : immédiats ? | idem, vie et pillz au round même | Mindwipe oui ; Combust : aucune carte possédée |
| Consume : immédiat ? Cancel Life Modif. contre un effet posé ? | Wave Ld gagnant ; Annul face à un Repair actif | **tranchés** : Consume immédiat (`1212171`) ; Annul saute le tic de vie du round, effet conservé (`1211922`) |

### Decks de référence (2026-09-16, toutes cartes du jeu)

Un duel = deck A (vous) contre deck B (l'ami / le second compte), 8 cartes chacun composées autour du scénario pour que
tout tirage de 4 convienne. Les cartes sont choisies petites (2-3★) et fréquentes ; remplacer par une équivalente
(même pouvoir) si elle manque. Les stats sont celles du niveau max.

| # | Question | Deck A | Deck B | Consigne par round |
|---|---|---|---|---|
| D1 | **SoA contre SoA** (cycle pur) et SoA contre SoB en ability | 4 × SoA en ability : Angelo (Montana), Cardigan, Cesare (All Stars), Jean (Jungo) + 4 × SoB en ability : Bol, Flo Cr (All Stars), Flanagan (Junkz), Borss (Jungo) | idem, autres clans : Doggonuts (Cosmohnuts), Graff Cr (Bangers), Guiliug (Dominion), Liam (Skeelz) + Angora (Vortex), Graziella (Freaks), Hella (Paradox), Globumm Cr (Sakrohm) | jouer SoA contre SoA, puis SoA contre SoB, puis SoB contre SoB ; 1-2 pillz, noter puissance finale des deux cartes |
| D2 | **All-Stop contre Protection: Ability** (Skeelz) et chaîne GHEIST/Roots contre Nightmare/Piranas | 8 Skeelz avec pouvoirs de stats visibles (bonus Protection: Ability), ex. Liam + n'importe quels Skeelz « Power +X » / « Damage +X » | Glorg, Dieter (Nightmare), Spycee, Yaccanemba (Piranas) + Morlha, XU-Dr0ne, Leviatonn Cr (GHEIST), Nahi Cr (Roots) | chaque Skeelz contre un All-Stop : le pouvoir Skeelz doit tomber (SoB retire la Protection, puis SoA passe) ; puis GHEIST contre Piranas entre eux |
| D3 | **Le Leader profite-t-il de son Team ?** + Solomon (Tie-break) + Ashigaru (Counter-attack) | Ambre, Eyrik, Vholt, Timber, Hugo + 3 cartes quelconques d'un même clan | Solomon, Ashigaru + 6 cartes quelconques | jouer **le Leader lui-même** (Ambre avec Courage, Eyrik…) et lire sa puissance/dégâts ; provoquer une égalité d'attaque contre Solomon ; observer qui joue en premier avec Ashigaru en main |
| D4 | **Tune Out et fury**, Consume/Combust/Mindwipe immédiats ? | 8 Cosmohnuts : Bobby Cornteeth (Players Combust), Colton, Cosmo Curcan, Curcan Noel, Doggonuts, Jacob, Maraval, Paw Paw | Prince Candle (Combust, Skeelz), Virtmund (Mindwipe, GHEIST), Hoffman, Wave Ld (Consume), H4rp3r (Toxin), Artax (Poison), Wilo Ld (Repair), Fletcher (Cancel Life Modif.) | round 1 : Cosmohnuts avec fury contre une carte à **une pillz de plus** (fury compte-t-elle ?) ; puis faire gagner Combust / Mindwipe / Consume / Repair et lire vies et pillz **au round même** puis au suivant ; Fletcher contre un poison posé au round précédent |
| D5 | **Limitless** (Fractal) et bornes | Fractal + 7 réducteurs à minimum : Arno, Artus, Ashley, B Ball, Ella, Kit-E, Klaus | 8 cartes à gros dégâts quelconques | faire gagner un réducteur avec Fractal en main : le minimum doit tomber à 0 ; vérifier que le bonus (ex. Pussycats -2 min 1) n'est pas touché |
| D6 | **Exchange contre Copy / Annul** | Blast, Blackfin, Cerra, Fink Cr, Homy, Taki (Damage Exchange), Bruno, Calamity (Power Exchange) | Angelina, Bettisia, Darril, Dash (Copy: Opp. Damage) + Shaker, Lenora (Cancel Opp. Damage Modif.) + Zwoosh, Zombiyaki (Power Impose) | Exchange contre Copy (qui l'emporte ?), Exchange contre Annul (annulé ?), Exchange contre Impose |
| D7 | **Conditions numériques** : Perfect, Bet, Per Pillz Left, Cards | Cyloxxt, Hula, Akirale, Dr Horatio (Perfect) + Scooty, Kent, Hundun (Per Pillz Left) + Rajesh (-2 Cards Damage, Min 4) | Imbris Cr, Flotillo, Slatka, Ziwi (Zenith, Bet > N) + Giovanni, Merrick Cr (Cards) + 2 quelconques | Perfect : gagner avec exactement la pillz nécessaire, puis une de trop ; Bet : miser exactement N pillz (gratuite comprise) puis N+1 ; Per Pillz Left : lire l'attaque au round 1 |
| D8 | **Clans à condition de main** : Oculus, Tolvack (After), Unison, Xantiax/Corrupt/Corrosion | 1 Oculus (Dark Nunavik, Dark Kupanda…) + 3 cartes d'un clan qu'il infiltre + Frau Vanda, Rauta (Tolvack) + Jamtiax, Cameron | Almastine, Aquiline, Caballine, Carcharine (Unison, mono-clan impossible → tester la **non-activation**) + 4 quelconques | Oculus : main 1 Oculus + 3 clan X (bonus adopté), puis 2 + 1 (carte seule) ; After : jouer Tolvack après une carte du clan indiqué ; Xantiax/Corrosion : vies des deux joueurs en fin de round |

Ordre de rentabilité : D4 (4 questions ouvertes en un duel), D1, D3, D6, puis D5, D7, D8, D2.

### Decks jouables avec la collection du compte (relevée le 2026-09-17)

La collection (1 234 cartes distinctes) est dans `UrbanPy/Backend_fastAPI/data/collection/ma_collection.json`, relevée
**passivement** depuis la page « Ma collection » du site (filtre « Seulement possédés », lecture du DOM page par page ;
la pagination est côté client, aucun appel API n'a été émis). Pour trouver une remplaçante possédée :

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python scripts/collection_lookup.py "Copy: Opp\. Damage" --exclude Skeelz
```

Le script sépare les cartes dont le pouvoir est **actif au niveau possédé** de celles « à monter » : une carte au niveau 1
dont le pouvoir se débloque au niveau 2 n'a *pas* de pouvoir en jeu. Tous les decks ci-dessous n'utilisent que des
pouvoirs actifs, sauf mention « à monter ». Le niveau indiqué est le niveau possédé.

Deux corrections par rapport aux decks de référence :

- **D3** : deux Leaders dans la même main s'annulent (bonus « Cancel Leader », `docs/REGLES.md` § 5) ; le deck de
  référence à 5 Leaders donnait des mains inexploitables. Ici : **un seul Leader par deck**, changé entre deux duels
  (un Leader dans un deck de 8 est en main une fois sur deux).
- **D4** : le bonus Tune Out de Jacob (seule Cosmohnuts possédée) n'est actif qu'avec une seconde Cosmohnuts en main ;
  le test passe donc par **Noon Steevens** (Pussycats, Tune Out en *pouvoir*, sans condition de clan). Dark Yookie
  (Oculus infiltrant Cosmohnuts) est ajoutée pour voir si l'infiltration active le bonus de Jacob.

| # | Question | Deck A | Deck B | Consigne / remarques |
|---|---|---|---|---|
| D1 | **SoA contre SoA** et SoA contre SoB en pouvoir (clans sans Stop en bonus) | SoA : Cardigan (All Stars, niv 2), Cesare (All Stars, 2), Oxo (Sakrohm, 1), Brandon Cr (Junkz, 3) + SoB : Angora (Vortex, 2), Borss (Jungo, 2), Flanagan (Junkz, 2), Graziella (Freaks, 2) | SoA : Onyx (Vortex, 3), Randal (Bangers, 3), Simon (Montana, 3), Alexei (All Stars, 4) + SoB : Aisha (Jungo, 3), Bella Ld (Montana, 3), Mitch (La Junta, 3), Chlora (Bangers, 4) | comme la référence : SoA contre SoA, SoA contre SoB, SoB contre SoB, 1-2 pillz, noter la puissance finale des deux cartes |
| D2a | **All-Stop contre Protection: Ability** (Skeelz) | 8 Skeelz : Sparkle (1, -5 Opp Power), Wan (1, +2 Attack par Opp Power), Danae (1, -10 Opp Attack), Sasha (2, Support: Attack +4), Henry (3, Support: -1 Opp Damage), Sopiket (3, Growth: Power +3), Minerva (5, -2 Opp Power & Damage), Tomas (5, **SoB** : cycle complet contre un All-Stop) | All-Stop : Dieter (Nightmare, 3), Glorg (Nightmare, 4), Madabook (Nightmare, 5), Baba (Piranas, 3, *Courage:* SoA — jouer Baba en premier) + Ksendra (GHEIST, 5), Methane Cr (GHEIST, 4), Bakko (Roots, 4), Kola (Roots, 1) | chaque Skeelz contre un All-Stop : le pouvoir Skeelz doit tomber ; Tomas contre Glorg = SoB protégé contre SoA + SoB, lire les deux cartes |
| D2b | **Chaîne GHEIST/Roots (bonus SoA) contre Nightmare/Piranas (bonus SoB)** | GHEIST : Ksendra (5), Methane Cr (4), Rekt Ld (3), Jaxx Ld (4) + Roots : Bakko (4), Kola (1), Arno (2), Kalija (3) | Nightmare : Dieter (3), Glorg (4), Madabook (5) + Piranas : Baba (3), Sting (3), Taljion (3), Zulu (1), Calliope (4) | jouer bonus contre bonus dans les deux sens ; Morlha (GHEIST, SoB en pouvoir) est à monter du niveau 1 au 2 pour le double Stop |
| D3 | **Le Leader profite-t-il de son Team ?** + Solomon (Tie-break) + Ashigaru (Counter-attack) | **1 Leader** + 7 La Junta (le deck « La junta » sans Natasha) : Eyrik (5) + Arnie (4), Brianna (3), Chiro (3), Naginata (4), Quormac (4), W4r Ld (2), Walker (3) | **1 Leader** + 7 Jungo : Solomon (5) + Odile (3), Nahema (5), Mindy (2), Cindy (3), Radek (3), Eduardo (5), Jalil (3) | jouer le Leader lui-même et lire sa puissance/dégâts ; duels suivants en remplaçant Eyrik par Ambre (Courage), Vholt, Timber, et Solomon par Ashigaru ; égalité d'attaque à provoquer contre Solomon |
| D4 | **Tune Out et fury** ; Consume / Mindwipe / Repair immédiats ? Cancel Life Modif. contre Poison/Toxin | Noon Steevens (Pussycats, 1, **Tune Out**), Jacob (Cosmohnuts, 2, bonus Tune Out), Dark Yookie (Oculus, 3, infiltre Cosmohnuts), Wave Ld (Hive, 2, Consume 1 Min 4), Wilo Ld (Dominion, 2, Repair 1 Max 14), Merweiss Cr (Riots, 5, *Revenge:* Mindwipe 2 — après un round perdu), Artax (Dominion, 2, Poison 2 Min 2), Chopper Ld (Raptors, 3, Toxin 1 Min 0) | Flea (Jungo, 2, Cancel Opp. Life Modif.) + 7 La Junta à pouvoirs de stats, sans effet pillz/vie : Chiyoko (3), Glover (3), Leo (3), Myke (3), Victor (4), Winifred (4), Agent Spinal (5) | round 1 : Noon Steevens avec fury contre une carte à **une pillz de plus** ; faire gagner Wave Ld / Merweiss Cr (après une défaite) / Wilo Ld et lire vies et pillz au round même puis au suivant ; Flea contre un poison posé au round précédent. **Combust** : aucune carte active (Volkan Cr à monter du niveau 2 au 5) |
| D5 | **Limitless** | — | — | **non réalisable** : Fractal est la seule carte Limitless du jeu et n'est pas possédée (les réducteurs Arno, Artus, Ashley, B Ball le sont) |
| D6 | **Exchange contre Copy / Annul / Impose** | Damage Exchange : Blast (Bangers, 2), Homy (Montana, 2), Incubus Cr (Nightmare, 4), Waldegrin Cr (Skeelz, 5) + remplissage à monter : Blackfin (Piranas, 1 → 2), Taki (Rescue, 1 → 2), Mamba (Fang Pi Clang, 1 → 3), Joan Cena (Uppers, 1 → 3, **Power Exchange**) | Copy: Opp. Damage : Bettisia (Pussycats, 2), Natasha (La Junta, 2), Ward hg (Vortex, 2), Nagataa (Hive, 1) + Power Impose : Zwoosh (Bangers, 2), Mozaert (Junkz, 1) + Damage Impose : Jacob (Cosmohnuts, 2) + Lenora (Riots, 1 → 4, Cancel Opp. Damage Modif., à monter) | Exchange contre Copy, contre Impose ; **Annul** : en attendant Lenora, duel à part avec Mr Big Duke (Leader, *Team:* Cancel Opp. Damage Modif.) seul Leader d'un deck quelconque |
| D7 | **Conditions numériques** : Per Pillz Left, Cards, Bet | Hundun (Freaks, 2, +1 Atk Per Pillz Left), Candy Jack (Nightmare, 4, +1 Power Per Pillz Left Max 8), Merrick Cr (Freaks, 3, -2 Cards Damage Min 1), M2 Sansot Cr (Vortex, 1, idem), Delija Cr (Roots, 1, -2 Cards Power Min 2), Pandemos Cr (Paradox, 5, -4 Cards Damage Min 0), Otium Cr (Jungo, 3, *Confidence:* -5 Cards Damage), Tyd (Piranas, 1, Bet > 6 Pillz : +2 Life) | 8 La Junta à gros dégâts : Dugan (5), Agent Spinal (5), Winifred (4), Victor (4), Isatis (4), Quormac (4), Ed 12 Cr (4), Chiyoko (3) | Per Pillz Left : lire l'attaque au round 1 ; Bet : Tyd avec exactement 6 pillz (gratuite comprise) puis 7 ; Cards : lire les dégâts selon le nombre de cartes. **Perfect** : aucune carte possédée (Ataoualpet et Mac Hen, Bet > 4, sont à monter au niveau 3) |
| D8 | **Oculus** (infiltration) et Corrupt | Oculus infiltrant Fang Pi Clang : Dark Nunavik (2, Courage: Power +4), Dark Askai (3, Attack +9), Dark Eklore (3, +1 Atk Per Pillz Left) + Fang Pi Clang : Chan (2), Yoshito (3), Fei Cr (4), Macumba (4), Rimikaru (2) | Nega D Ld (Uppers, 5, Corrupt 2 Min 5) + les 7 La Junta de D4 | main 1 Oculus + 3 Fang Pi (bonus Damage +2 adopté ?), puis 2 Oculus + 2 Fang Pi, puis 3 + 1 (la Fang Pi seule garde-t-elle son bonus ?) ; Nega D Ld gagnant : vies/pillz des deux joueurs au round même. **Tolvack (After), Unison, Xantiax, Corrosion** : aucune carte possédée |

Ordre de rentabilité avec la collection : ~~D4, D1~~ (faits le 2026-09-17, voir journal), puis D2a, D3, D6, D7, D8, D2b.

**Journal (2026-09-17, parties contre l'adversaire d'entraînement « Smash Jabber », règle 2, 15 vies)** — 15 combats
capturés (`data/ur_battles/12104*.json` à `1213913.json`, plus `1181426.json` de la veille), tous rejoués par `tests/test_ur_battles.py` :

- **D1 clos** : chaîne SoA/SoB confirmée dans les deux sens (`1210477`, `1211029`), bonus SoA contre SoA en pouvoir
  (`1210625`), quatre lectures de Stop en pouvoir contre bonus Stop. SoA contre SoA (et SoB contre SoB) en pouvoir est
  inobservable par construction : rien d'autre à stopper.
- **D4 clos** : Tune Out = puissances à 1, attaque = pillz (`1211279`) ; Mindwipe immédiat puis persistant, vie et pillz
  (deux écarts moteur corrigés, commit 30f054c) ; Tune Out avec fury : la fury ne compte pas (`1211570`, égalité 8-8
  perdue) ; Repair = +X vie **et** pillz dès le round gagné, max Y (`1211702`, troisième écart moteur corrigé) ; Cancel
  Life Modif. contre un Repair actif : la moitié vie du tic sautée, le pillz versé, reprise au round suivant (`1211922`,
  quatrième écart corrigé : suspension par attribut) ; Consume au round même (`1212171`, Wave Ld : 12 − 6 − 1 = 5) et
  Corrupt (le propriétaire perd X vies en défaite). **D4 clos** hors Combust (aucune carte).
- **D7 entamé** (`1213913`) : Per Pillz Left = pillz au début du round (Hundun 5 × 5 + 12 = 37) ; Bet > 6 avec 8 pillz
  gratuite comprise → +2 vies (le texte de Tyd dit lui-même « Pillz gratuite comprise et Fury exclue ») ; Brawl compte
  les cartes du clan adverse en main adverse ; égalité 4-4 gagnée par le niveau 1 contre le niveau 4. Restent : « Cards »
  (Merrick Cr, M2 Sansot Cr, Pandemos Cr), Candy Jack, Otium Cr (Confiance).
- En prime : Copy: Opp. Ability (Oblivion) copie un Stop et le retourne (`1211029`) ; After (Tolvack) reproduit.
- Capture : contre un bot qui joue instantanément, l'ordre de jeu se lit sur la carte déjà posée (correction de
  `ur_capture.js`) ; les `roundPower`/`roundDamage` des rounds passés reviennent aux valeurs de base dans les statuts
  suivants — un round manqué ne se reconstitue pas (mettre `null`, non vérifié).

**Cartes à monter d'un ou deux niveaux** qui débloqueraient les tests manquants : Spycee (Piranas, 1 → 2, All-Stop
Piranas), Morlha (GHEIST, 1 → 2, SoB en pouvoir sur bonus SoA), Blackfin et Taki (1 → 2, Damage Exchange), Joan Cena
(1 → 3, Power Exchange), Ella et Klaus (1 → 2, réducteurs à minimum), Ataoualpet et Mac Hen (1 → 3, Bet > 4).
Lenora (1 → 4) et Volkan Cr (2 → 5, Combust) sont plus longues.

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
