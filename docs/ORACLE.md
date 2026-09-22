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
| Exchange contre Copy / Annul | Dominion « Damage Exchange » contre « Copy: Opp. Damage » puis contre « Cancel Opp. Damage Modif. » |
| **« Per Damage » en défaite** (2026-09-22) | voir C1 ci-dessous |
| **Protection: \<stat\> contre « Cards »** (2026-09-22) | voir C2 ci-dessous |
| **Ordre entre les deux cartes** (2026-09-22) | voir C3 ci-dessous |
| **« Per Life Lost » au-delà de 12 vies** (2026-09-22) | voir C4 ci-dessous |

### Decks prêts à jouer (2026-09-16)

Un duel = deck A (vous) contre deck B (l'ami / le second compte), 8 cartes chacun composées autour du scénario pour que
tout tirage de 4 convienne. Les cartes sont choisies petites (2-3★) et fréquentes ; remplacer par une équivalente
(même pouvoir) si elle manque. Les stats sont celles du niveau max.

> **Colonne Deck A mise à jour le 2026-09-19** à partir de la collection réelle (1 234 personnages sur 2 497, voir
> « La collection du compte » ci-dessous). Chaque carte
> listée est possédée à un niveau où son ability est active ; les substitutions et les duels non constituables faute
> de carte-clé sont signalés dans la cellule. La colonne Deck B reste la composition théorique d'origine.

| # | Question | Deck A | Deck B | Consigne par round |
|---|---|---|---|---|
| D1 | **SoA contre SoA** (cycle pur) et SoA contre SoB en ability | **Possédé** — SoA en ability : Cardigan, Cesare (All Stars), Oxo (Sakrohm), Randal (Bangers, 3★) + SoB en ability : Angora (Vortex), Borss (Jungo), Flanagan (Junkz), Graziella (Freaks). *(Angelo, Jean, Bol, Flo Cr non possédés)* | idem, autres clans : Doggonuts (Cosmohnuts), Graff Cr (Bangers), Guiliug (Dominion), Liam (Skeelz) + Angora (Vortex), Graziella (Freaks), Hella (Paradox), Globumm Cr (Sakrohm) | jouer SoA contre SoA, puis SoA contre SoB, puis SoB contre SoB ; 1-2 pillz, noter puissance finale des deux cartes |
| D2 | **All-Stop contre Protection: Ability** (Skeelz) et chaîne GHEIST/Roots contre Nightmare/Piranas | **Possédé** — 8 Skeelz (bonus Protection: Ability), pouvoirs visibles : Sparkle (−5 Opp Power), Sasha (Support Atk+4), Danae (−10 Opp Atk), Henry (Support −1 Opp Dmg), Wan (+2 Atk/Opp Power), Sopiket (Growth Power+3), Minerva (−2 Opp Pow&Dmg), Deebler (Conf. −4 Opp Dmg). *(Liam possédé mais niv 1 : ability inactive)* | Glorg, Dieter (Nightmare), Spycee, Yaccanemba (Piranas) + Morlha, XU-Dr0ne, Leviatonn Cr (GHEIST), Nahi Cr (Roots) | chaque Skeelz contre un All-Stop : le pouvoir Skeelz doit tomber (SoB retire la Protection, puis SoA passe) ; puis GHEIST contre Piranas entre eux |
| D3 | **Le Leader profite-t-il de son Team ?** + Solomon (Tie-break) + Ashigaru (Counter-attack) | **Possédé** — 5 Leaders Team : Ambre, Eyrik, Vholt, Timber, John Doom + 3 All Stars quelconques : Frank, Stacey, Loretta. *(John Doom remplace Hugo, non possédé)* | Solomon, Ashigaru + 6 cartes quelconques | jouer **le Leader lui-même** (Ambre avec Courage, Eyrik…) et lire sa puissance/dégâts ; provoquer une égalité d'attaque contre Solomon ; observer qui joue en premier avec Ashigaru en main |
| D4 | Consume/Combust/Mindwipe immédiats ? (Tune Out et fury : tranché par le combat 1248952) | ⚠️ **Non constituable** : aucun Combust ni Cosmohnuts possédé (hormis Jacob). Cartes possédées pour tester l'immédiateté (autres clans) : Consume — Wave Ld, C-Arib ; Mindwipe — Merweiss Cr ; Repair — Wilo Ld | Prince Candle (Combust, Skeelz), Virtmund (Mindwipe, GHEIST), Hoffman, Wave Ld (Consume), H4rp3r (Toxin), Artax (Poison), Wilo Ld (Repair), Fletcher (Cancel Life Modif.) | faire gagner Combust / Mindwipe / Consume / Repair et lire vies et pillz **au round même** puis au suivant ; Fletcher contre un poison posé au round précédent |
| D5 | **Limitless** (Fractal) et bornes | ⚠️ **Non constituable** : Fractal (Limitless) non possédé et carte unique — duel injouable en l'état. Réducteurs à minimum possédés (pour mémoire) : Arno, Artus, Ashley, B Ball, Neloe, Soushee, Winston | 8 cartes à gros dégâts quelconques | faire gagner un réducteur avec Fractal en main : le minimum doit tomber à 0 ; vérifier que le bonus (ex. Pussycats -2 min 1) n'est pas touché |
| D6 | **Exchange contre Copy / Annul** | **Possédé** — Damage Exchange : Blast, Homy, Serleena, Incubus Cr, Duchess, Waldegrin Cr + Power Exchange : Casagrande Cr (seul possédé). 8ᵉ case = carte au choix (aucun autre Exchange possédé) | Angelina, Bettisia, Darril, Dash (Copy: Opp. Damage) + Shaker, Lenora (Cancel Opp. Damage Modif.) + Zwoosh, Zombiyaki (Power Impose) | Exchange contre Copy (qui l'emporte ?), Exchange contre Annul (annulé ?), Exchange contre Impose |
| D7 | **Conditions numériques** : Perfect, Bet, Per Pillz Left, Cards | ⚠️ **Perfect non possédé.** Autres conditions possédées — Per Pillz Left : Hundun, Candy Jack ; Bet : Tyd (Bet > 6) ; Cards : Delija Cr, M2 Sansot Cr, Merrick Cr, Otium Cr, Pandemos Cr | Imbris Cr, Flotillo, Slatka, Ziwi (Zenith, Bet > N) + Giovanni, Merrick Cr (Cards) + 2 quelconques | Perfect : gagner avec exactement la pillz nécessaire, puis une de trop ; Bet : miser exactement N pillz (gratuite comprise) puis N+1 ; Per Pillz Left : lire l'attaque au round 1 |
| D8 | **Clans à condition de main** : Oculus, Tolvack (After), Unison, Xantiax/Corrupt/Corrosion | ⚠️ **Tolvack (After) et Xantiax non possédés.** Oculus possédés : Dark Nunavik (+ 3 All Stars infiltrés : Cardigan, Cesare, Ashley) ; Corrosion/Corrupt : Nega D Ld (Corrupt 2) | Almastine, Aquiline, Caballine, Carcharine (Unison, mono-clan impossible → tester la **non-activation**) + 4 quelconques | Oculus : main 1 Oculus + 3 clan X (bonus adopté), puis 2 + 1 (carte seule) ; After : jouer Tolvack après une carte du clan indiqué ; Xantiax/Corrosion : vies des deux joueurs en fin de round |

Ordre de rentabilité (théorique) : D4 (3 questions ouvertes en un duel), D1, D3, D6, puis D5, D7, D8, D2.

### Points relevés par le corpus combinatoire (C1-C4, 2026-09-22)

Quatre comportements que le moteur applique sans source : le corpus les a mis au jour, aucun n'a été modifié. Chacun
dit ce que fait le moteur aujourd'hui, la manip qui tranche, et la retouche à appliquer si le serveur dit le
contraire. Détail et exemples chiffrés : `docs/REGLES.md` § 5.1. Après chaque décision : corriger, ajouter un test,
puis régénérer les digests (`python scripts/build_engine_corpus.py`).

#### C1 — « Per Damage » en défaite

- **Moteur aujourd'hui** : le multiplicateur vaut 0 quand la carte perd (`multipliers._nb_damage_inflicted`). Résultat :
  le volet « défaite » de trois cartes réelles ne peut jamais rien faire, ce qu'aucune carte imprimée ne ferait.
- **Cartes** : **Zalindra** (Zenith 3★ P9 D4, « Defeat: +1 Life Per Damage ») ; **Griffonmor Cr** (Skeelz 4★ P8 D4) et
  **Senestra** (Nightmare 3★ P8 D2), toutes deux « Victory Or Defeat: +1 Life Per Damage ».
- **Manip** : faire **perdre** Zalindra (1 pillz contre une grosse mise adverse) et lire les vies gagnées. Puis
  Griffonmor Cr / Senestra en victoire (témoin) **puis** en défaite. Refaire une défaite face à un réducteur de dégâts
  (Pussycats « -2 Opp Damage, Min 1 ») pour savoir si ce sont les dégâts imprimés ou les dégâts après modificateurs.
- **Attendu si le moteur a tort** : `_nb_damage_inflicted` renvoie `card1.damage_fight` sans regarder `card1.win`.

#### C2 — Protection: \<stat\> contre « Cards »

- **Moteur aujourd'hui** : `apply_capacity_lvl_1._apply_stat_protections` ne retire que les modificateurs adverses qui
  ciblent explicitement l'adversaire (`target == "enemy"`). Un « -X Cards <stat> » (cible **les deux** cartes) traverse
  donc la Protection. L'utilisateur penche pour l'inverse.
- **Cartes** : protégés — **Vivian** (Berzerk 3★ P7 D4, « Protection : Damage »), **Fixit** (Bangers 5★ P7 D6,
  « Protection: Power And Damage »), **Eyrton Cr** (All Stars **2★** P8 D2, « Protection : Damage » — à 5★ son pouvoir
  est un Cancel, pas une Protection) ; réducteurs « Cards » — **Giovanni** (Montana 3★, « -2 Cards Damage, Min 1 »),
  **Pandemos Cr** (Paradox, « -4 Cards Damage, Min 1/0 »), **Rajesh** (Uppers 2★, « -2 Cards Damage, Min 4 »),
  **Delija Cr** (Roots 1★, « -2 Cards Power, Min 2 »).
- **Manip** : Vivian face à Giovanni, 1 pillz chacun, et lire les **dégâts de Vivian** : le moteur donne **2**
  (la Protection ne bloque pas) ; **4** si elle bloque. Idem Fixit face à Giovanni : moteur **4**, attendu **6**.
  Refaire une fois sur la puissance (Delija Cr contre un « Protection: Power »).
- **Attendu si le moteur a tort** : `_strip_types(..., only_targeting_opponent=True)` doit aussi retirer les capacités
  `target == "both"` quand la carte protégée est visée.

#### C3 — Ordre entre les deux cartes

- **Moteur aujourd'hui** : la carte **alliée** est toujours résolue avant la carte ennemie, aux niveaux 2, 3 et 4. Dès
  qu'un plancher, un plafond ou une liste entre en jeu, le résultat dépend du camp qui s'appelle « allié » — ce qui
  n'existe pas dans le vrai jeu. 25 scénarios asymétriques sont épinglés dans `tests/test_engine_properties.py`.
  **Rejouer chaque manip en inversant le premier joueur** : si le résultat suit l'ordre de jeu, la règle est « le
  premier joueur d'abord ».
- **C3a, niveau 2 (stats)** : **Rajesh** (Uppers 2★ P5 D6, « -2 Cards Damage, Min 4 ») contre **Pandemos Cr**
  (Paradox 5★ P9 D8, « -4 Cards Damage, Min 0 »), 1 pillz chacun. Selon la carte résolue en premier, le moteur donne
  **Rajesh 0 / Pandemos 2** (Rajesh d'abord : 6→4 et 8→6, puis −4) ou **Rajesh 2 / Pandemos 4** (Pandemos d'abord :
  8→4 et 6→2, puis le « Min 4 » ne mord plus). Lire les dégâts des deux cartes.
- **C3b, niveau 3 (vie / pillz)** : faire **perdre** **Kusuri** (Fang Pi Clang 2★ P7 D2, « Defeat: +2 Life ») face à
  **Phyllis** (Nightmare 2★ P7 D1, « -3 Opp. Life Min 4 »), le joueur de Kusuri **à 6 vies**. Le moteur donne **4**
  (gain d'abord : 5 → 7, puis −3) ou **6** (perte d'abord : plancher 4, puis +2). Variantes équivalentes :
  **Melinda** ou **Wonald** (« Defeat: +2 Life ») contre **Oxen** ou **Jeyn** (« -3 Opp. Life Min 5 »).
- **C3c, niveau 4 (effets persistants)** : faire **perdre** **Willow** (Roots 2★ P7 D2, « Defeat : Heal 1 Max. 10 »)
  contre une carte **Freaks** (bonus « Poison 2, Min 3 ») qui gagne, de sorte que le joueur de Willow soit à
  **exactement 10 vies après les dégâts du round** (le plafond du soin). Les deux effets se posent alors sur le même
  joueur le même round ; lire ses vies **au round suivant** : le moteur donne **8** (soin d'abord, sans effet à 10,
  puis poison) ou **9** (poison 10 → 8, puis soin → 9).
- **Attendu si le moteur a tort** : ordonner les deux cartes par `game.turn` (premier joueur d'abord) dans
  `apply_capacity_lvl_2`, `apply_capacity_lvl_3` et `apply_capacity_lvl_4` ; au niveau 2, étendre éventuellement la
  règle 3.6 bis (plancher le plus haut d'abord) aux deux cartes à la fois.

#### C4 — « Per Life Lost » au-delà de la vie de départ

- **Moteur aujourd'hui** : le multiplicateur vaut `12 − vie` (`multipliers.MAX_LIFE`), donc **négatif** au-dessus de
  12 vies : « +1 Power Per Life Lost » à 14 vies retire 2 de puissance. Ce 12 n'est pas une règle : c'est le hardcode
  d'origine (`7ae5f73`, 2024-12-30, commentaire « change le hardcode 12 »), simplement renommé en 2026.
- **Cartes** : **Razor** (Ulu Watu 4★ P5 D6), **Zell** (Berzerk 1★ P6 D2), **Padre Nido** (Paradox 3★ P6 D5),
  **Miss Donna Luna** (Pussycats 2★ P3 D5), toutes « +1 Power Per Life Lost, Max. N » ; **P. Steevens Cr** (La Junta
  1★, « +1 Damage Per Life Lost Max. 3 »). Pour dépasser 12 vies : bonus Jungo « +2 Life », ou **Dallas** (All Stars
  3★, « Heal 1 Max. 14 »), ou un mode à plus de 12 vies.
- **Manip** : monter au-dessus de 12 vies, puis jouer Razor et lire sa **puissance** (5 si le multiplicateur est borné
  à 0, 3 à 14 vies s'il devient négatif). Vérifier aussi le cas « pillz » (`MAX_PILLZ`) avec un « Per Pillz Lost ».
- **Attendu si le moteur a tort** : borner le multiplicateur à 0, et à terme lire la **vie de départ de la partie**
  (le `Format` de la branche `feat/ia-tous-modes` la porte déjà) plutôt qu'une constante.

Avec la collection actuelle (2026-09-19), jouables tout de suite : **D1, D2, D3, D6** ; partiels : **D7** (sans Perfect),
**D8** (Oculus seul) ; bloqués faute de carte-clé : **D4** (aucun Combust), **D5** (pas de Fractal).

### La collection du compte

`UrbanPy/Backend_fastAPI/data/collection/collection_jerem.json` est la collection du compte Urban Rivals **« jere'm »**
(celui qui joue les combats de `data/ur_battles/`), relevée le 2026-09-17 : 1 304 entrées pour 1 234 personnages
distincts, chacun au niveau possédé. Elle a été lue **passivement dans le DOM** de la page `/collection/` (filtre
« Seulement possédés », pagination côté client) — aucun appel à l'API du site, aucune rétro-ingénierie du client.

Elle sert à composer des duels jouables : `scripts/collection_lookup.py` cherche les cartes possédées dont le pouvoir
correspond à un motif, et signale celles dont le pouvoir n'est débloqué qu'à un niveau supérieur.

```bash
cd UrbanPy/Backend_fastAPI
.venv/bin/python scripts/collection_lookup.py "Protection : Damage"
.venv/bin/python scripts/collection_lookup.py "Stop Opp. Ability" --exclude GHEIST,Roots,Nightmare,Piranas
.venv/bin/python scripts/collection_lookup.py . --clan Leader
```

Le relevé date du 2026-09-17 : le refaire après des achats ou des montées de niveau.

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
