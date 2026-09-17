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

Si la page est rechargée : recoller le script puis exécuter `urRestore()` pour récupérer ce qui a été sauvegardé —
**avant** de lancer le combat suivant : un round manqué ne se reconstitue pas (les `roundPower` / `roundDamage` des
rounds passés reviennent aux valeurs de base dans les statuts suivants ; le mettre à `null` dans le fichier, il n'est
alors pas vérifié). Contre un adversaire qui joue instantanément (bot), l'ordre de jeu se lit sur la carte déjà posée
dans le premier statut du round, pas sur `turnPlayerId` — le script le fait.

## 2. Jouer

Enchaîner les combats normalement (n'importe quel mode). Un combat dure ~4 minutes ; une session d'une heure donne une
dizaine de combats, soit 40 rounds vérifiés. Contre l'adversaire d'entraînement (« Smash Jabber », règle 2, 15 vies),
chaque combat est exploitable : le moteur reproduit ce mode.

**Pour cibler une règle précise**, composer le deck autour de la question : on choisit ses 8 cartes, donc la moitié du
scénario ; l'adversaire d'entraînement tire des clans variés et finit par fournir l'autre moitié. Questions encore
ouvertes (les questions tranchées le 2026-09-17 sont consignées dans `docs/REGLES.md` § 5) :

| Question | Scénario à jouer | Deck |
|---|---|---|
| Protection contre All-Stop (cycle Stop / Protection, REGLES § 3.2) | Skeelz (bonus Protection: Ability) contre un Nightmare / Piranas à SoA en pouvoir | D2a |
| Chaîne bonus SoA (GHEIST, Roots) contre bonus SoB (Nightmare, Piranas) | jouer bonus contre bonus dans les deux sens | D2b |
| Le Leader profite-t-il de son Team ? (REGLES § 3.7) ; Ashigaru joue-t-il toujours second ? ; Solomon sur égalité | jouer le Leader lui-même ; observer l'ordre avec Ashigaru en main | D3 |
| Limitless (Fractal) | Fractal en main + allié « −X Opp Damage, Min Y » gagnant | D5, non réalisable (Fractal absente) |
| Exchange contre Copy / Annul / Impose | Damage Exchange contre Copy: Opp. Damage, Cancel Opp. Damage Modif., Power Impose | D6 |
| Oculus : mains 1 Oculus + 3 du clan infiltré, et 1 + 2 + 1 (REGLES § 3.6) | lire le bonus adopté et l'activation du pouvoir Infiltrated | D8 |
| Combust : immédiat ? | une carte Combust gagnante, vie et pillz au round même | aucune carte possédée (Volkan Cr à monter au niveau 5) |
| Tolvack (After), Unison, Xantiax, Corrosion, Perfect | — | aucune carte possédée |

### Decks de référence (2026-09-16, toutes cartes du jeu)

Un duel = deck A (vous) contre deck B (l'ami / le second compte), 8 cartes chacun composées autour du scénario pour que
tout tirage de 4 convienne. Les cartes sont choisies petites (2-3★) et fréquentes ; remplacer par une équivalente
(même pouvoir) si elle manque. Les stats sont celles du niveau max.

| # | Question | Deck A | Deck B | Consigne par round |
|---|---|---|---|---|
| D2 | **All-Stop contre Protection: Ability** (Skeelz) et chaîne GHEIST/Roots contre Nightmare/Piranas | 8 Skeelz avec pouvoirs de stats visibles (bonus Protection: Ability), ex. Liam + n'importe quels Skeelz « Power +X » / « Damage +X » | Glorg, Dieter (Nightmare), Spycee, Yaccanemba (Piranas) + Morlha, XU-Dr0ne, Leviatonn Cr (GHEIST), Nahi Cr (Roots) | chaque Skeelz contre un All-Stop : le pouvoir Skeelz doit tomber (SoB retire la Protection, puis SoA passe) ; puis GHEIST contre Piranas entre eux |
| D3 | **Le Leader profite-t-il de son Team ?** + Solomon (Tie-break) + Ashigaru (Counter-attack) | Ambre, Eyrik, Vholt, Timber, Hugo + 3 cartes quelconques d'un même clan | Solomon, Ashigaru + 6 cartes quelconques | jouer **le Leader lui-même** (Ambre avec Courage, Eyrik…) et lire sa puissance/dégâts ; provoquer une égalité d'attaque contre Solomon ; observer qui joue en premier avec Ashigaru en main |
| D5 | **Limitless** (Fractal) et bornes | Fractal + 7 réducteurs à minimum : Arno, Artus, Ashley, B Ball, Ella, Kit-E, Klaus | 8 cartes à gros dégâts quelconques | faire gagner un réducteur avec Fractal en main : le minimum doit tomber à 0 ; vérifier que le bonus (ex. Pussycats -2 min 1) n'est pas touché |
| D6 | **Exchange contre Copy / Annul** | Blast, Blackfin, Cerra, Fink Cr, Homy, Taki (Damage Exchange), Bruno, Calamity (Power Exchange) | Angelina, Bettisia, Darril, Dash (Copy: Opp. Damage) + Shaker, Lenora (Cancel Opp. Damage Modif.) + Zwoosh, Zombiyaki (Power Impose) | Exchange contre Copy (qui l'emporte ?), Exchange contre Annul (annulé ?), Exchange contre Impose |
| D8 | **Clans à condition de main** : Oculus, Tolvack (After), Unison, Xantiax/Corrupt/Corrosion | 1 Oculus (Dark Nunavik, Dark Kupanda…) + 3 cartes d'un clan qu'il infiltre + Frau Vanda, Rauta (Tolvack) + Jamtiax, Cameron | Almastine, Aquiline, Caballine, Carcharine (Unison, mono-clan impossible → tester la **non-activation**) + 4 quelconques | Oculus : main 1 Oculus + 3 clan X (bonus adopté), puis 2 + 1 (carte seule) ; After : jouer Tolvack après une carte du clan indiqué ; Xantiax/Corrosion : vies des deux joueurs en fin de round |

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

Correction par rapport au deck de référence D3 : deux Leaders dans la même main s'annulent (bonus « Cancel Leader »,
`docs/REGLES.md` § 5) ; le deck à 5 Leaders donnait des mains inexploitables. Ici : **un seul Leader par deck**, changé
entre deux duels (un Leader dans un deck de 8 est en main une fois sur deux).

| # | Question | Deck A | Deck B | Consigne / remarques |
|---|---|---|---|---|
| D2a | **All-Stop contre Protection: Ability** (Skeelz) | 8 Skeelz : Sparkle (1, -5 Opp Power), Wan (1, +2 Attack par Opp Power), Danae (1, -10 Opp Attack), Sasha (2, Support: Attack +4), Henry (3, Support: -1 Opp Damage), Sopiket (3, Growth: Power +3), Minerva (5, -2 Opp Power & Damage), Tomas (5, **SoB** : cycle complet contre un All-Stop) | All-Stop : Dieter (Nightmare, 3), Glorg (Nightmare, 4), Madabook (Nightmare, 5), Baba (Piranas, 3, *Courage:* SoA — jouer Baba en premier) + Ksendra (GHEIST, 5), Methane Cr (GHEIST, 4), Bakko (Roots, 4), Kola (Roots, 1) | chaque Skeelz contre un All-Stop : le pouvoir Skeelz doit tomber ; Tomas contre Glorg = SoB protégé contre SoA + SoB, lire les deux cartes |
| D2b | **Chaîne GHEIST/Roots (bonus SoA) contre Nightmare/Piranas (bonus SoB)** | GHEIST : Ksendra (5), Methane Cr (4), Rekt Ld (3), Jaxx Ld (4) + Roots : Bakko (4), Kola (1), Arno (2), Kalija (3) | Nightmare : Dieter (3), Glorg (4), Madabook (5) + Piranas : Baba (3), Sting (3), Taljion (3), Zulu (1), Calliope (4) | jouer bonus contre bonus dans les deux sens ; Morlha (GHEIST, SoB en pouvoir) est à monter du niveau 1 au 2 pour le double Stop |
| D3 | **Le Leader profite-t-il de son Team ?** + Solomon (Tie-break) + Ashigaru (Counter-attack) | **1 Leader** + 7 La Junta (le deck « La junta » sans Natasha) : Eyrik (5) + Arnie (4), Brianna (3), Chiro (3), Naginata (4), Quormac (4), W4r Ld (2), Walker (3) | **1 Leader** + 7 Jungo : Solomon (5) + Odile (3), Nahema (5), Mindy (2), Cindy (3), Radek (3), Eduardo (5), Jalil (3) | jouer le Leader lui-même et lire sa puissance/dégâts ; duels suivants en remplaçant Eyrik par Ambre (Courage), Vholt, Timber, et Solomon par Ashigaru ; égalité d'attaque à provoquer contre Solomon |
| D5 | **Limitless** | — | — | **non réalisable** : Fractal est la seule carte Limitless du jeu et n'est pas possédée (les réducteurs Arno, Artus, Ashley, B Ball le sont) |
| D6 | **Exchange contre Copy / Annul / Impose** | Damage Exchange : Blast (Bangers, 2), Homy (Montana, 2), Incubus Cr (Nightmare, 4), Waldegrin Cr (Skeelz, 5) + remplissage à monter : Blackfin (Piranas, 1 → 2), Taki (Rescue, 1 → 2), Mamba (Fang Pi Clang, 1 → 3), Joan Cena (Uppers, 1 → 3, **Power Exchange**) | Copy: Opp. Damage : Bettisia (Pussycats, 2), Natasha (La Junta, 2), Ward hg (Vortex, 2), Nagataa (Hive, 1) + Power Impose : Zwoosh (Bangers, 2), Mozaert (Junkz, 1) + Damage Impose : Jacob (Cosmohnuts, 2) + Lenora (Riots, 1 → 4, Cancel Opp. Damage Modif., à monter) | Exchange contre Copy, contre Impose ; **Annul** : en attendant Lenora, duel à part avec Mr Big Duke (Leader, *Team:* Cancel Opp. Damage Modif.) seul Leader d'un deck quelconque |
| D8 | **Oculus** (infiltration) | Oculus infiltrant Fang Pi Clang : Dark Nunavik (2, Courage: Power +4), Dark Askai (3, Attack +9), Dark Eklore (3, +1 Atk Per Pillz Left) + Fang Pi Clang : Chan (2), Yoshito (3), Fei Cr (4), Macumba (4), Rimikaru (2) | 8 cartes quelconques à pouvoirs de stats, ex. La Junta : Chiyoko (3), Glover (3), Leo (3), Myke (3), Victor (4), Winifred (4), Agent Spinal (5), Dugan (5) | main 1 Oculus + 3 Fang Pi (bonus Damage +2 adopté ?), puis 2 Oculus + 2 Fang Pi, puis 3 + 1 (la Fang Pi seule garde-t-elle son bonus ?). Déjà vu : avec trois autres clans, l'Oculus n'infiltre rien (`1211570`, `1214141`) |

Ordre de rentabilité : D3 et D8 (jouables contre n'importe quel adversaire), D6, puis D2a et D2b (il faut que l'adversaire
tire Nightmare / Piranas ou GHEIST / Roots).

**Cartes à monter d'un ou deux niveaux** qui débloqueraient des tests : Spycee (Piranas, 1 → 2, All-Stop Piranas), Morlha
(GHEIST, 1 → 2, SoB en pouvoir sur bonus SoA), Blackfin et Taki (1 → 2, Damage Exchange), Joan Cena (1 → 3, Power
Exchange) ; Lenora (1 → 4, Cancel Opp. Damage Modif.) et Volkan Cr (2 → 5, Combust) sont plus longues.

**Fait le 2026-09-17** (18 combats, `data/ur_battles/12104*.json` à `1214370.json`) : D1 (Stops), D4 (Tune Out, Mindwipe,
Repair, Consume, Annul Modif. Vie, Corrupt) et D7 (Per Pillz Left, Bet, Cards, Equalizer, Brawl) sont clos — quatre
écarts moteur corrigés, tout est consigné dans `docs/REGLES.md` § 5 et dans le `_comment` de chaque fichier de combat.

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
