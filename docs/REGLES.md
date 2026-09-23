# Règles officielles d'Urban Rivals — registre du moteur

Confronte chaque décision de règle du moteur aux sources disponibles, et consigne ce qui reste incertain. Les
sections « Règles confirmées » et « Pouvoirs exclus » décrivent l'état **actuel** du moteur — les corrections
passées sont dans l'historique git, pas ici. **Le § 3 (registre R1-R6) est le seul endroit où sont écrites les
questions de règles ouvertes** ; `docs/ROADMAP.md` y renvoie, `docs/ORACLE.md` décrit seulement la logistique de
capture des combats qui les tranchent.

## Sources

| Source | Statut | Accès |
|---|---|---|
| **Règles officielles** `urban-rivals.com/game/rules/` (glossaire de 35 entrées) | Texte intégral relevé en session connectée, reproduit dans [REGLES-glossaire-officiel.md](REGLES-glossaire-officiel.md) | Connexion requise (`?question=N`, contenu chargé en AJAX) |
| **Base de connaissances du support** | Site fermé ; l'article 91 (« Ability, Bonus, Stop… priorités ») est archivé sur la Wayback Machine | `web.archive.org/web/2023/https://support.urban-rivals.com/index.php?pg=kb.page&id=91` |
| **Wiki des joueurs** `urban-rivals.fandom.com` | Définitions le plus souvent recopiées du texte officiel des cartes | API MediaWiki : `/api.php?action=parse&page=<Titre>&prop=wikitext` |
| **Combats réels capturés** | Le juge de paix : le moteur doit reproduire exactement les valeurs calculées par le serveur | `data/ur_battles/`, procédure : [ORACLE.md](ORACLE.md) |

Hiérarchie de confiance : règle officielle (support ou glossaire) > combat réel capturé > confirmation utilisateur
(connaissance du jeu, à défaut d'écrit) > texte de carte cité par le wiki > prose du wiki.

## Règles confirmées

### Round de base
| Règle | Moteur | Source |
|---|---|---|
| Attaque = Puissance × Pillz ; 1 pillz gratuite obligatoire ; vies et pillz de départ réglables par mode (12 par défaut) | `process_round` | glossaire 76, 48 |
| Fury : 3 pillz sacrifiées → +2 dégâts, ajoutés **après** les réducteurs de dégâts | `process_round` | glossaire 41, 56 ; utilisateur |
| Puissance et pillz minimales 1 → attaque minimale 1 hors effet ; un réducteur « Min 0 » descend bien à 0 | `apply_capacity_lvl_2` | wiki *Power* ; utilisateur |
| Égalité d'attaque : la carte de **niveau (étoiles) le plus bas** gagne ; à niveau égal, celui qui a joué **en premier** | `resolve_combat` | wiki *Power* + FAQ support ; combat réel 1294088 |
| Premier joueur du round 1 : aléatoire, puis alternance | `create_game` | wiki *Strike Back* |
| Fin de partie : KO à 0 vie ; sinon après 4 rounds, plus de vie gagne ; égalité = match nul | `check_end` | wiki *KO*, *Life* |

### Niveau 1 — Stop, Protection, Copie, Annul, Echange
| Règle | Moteur | Source |
|---|---|---|
| Les Stop (SoA/SoB) se résolvent **en chaîne** : un Stop lui-même stoppé ne stoppe rien. En cycle (SoA contre SoA, ou double Protection contre SoA+SoB), **les Stops gagnent** | `apply_capacity_lvl_1._stopped_slots` | support art. 91 (chaîne) ; utilisateur (cycles, 2026-09-21) |
| La condition Stop ne s'active pas contre un Annul | `apply_capacity_lvl_1` | glossaire 58 |
| Protection : Bonus/Pouvoir protège des Stop mais pas d'un Annul ni d'une Protection adverse adaptée ; protège aussi des effets négatifs d'un Leader | `apply_capacity_lvl_1._apply_stat_protections` | glossaire 55 |
| Annul Modif. Vie/Pillz suspend l'effet persistant adverse **pour le round où il est joué** (poison/toxine/heal/regen ; dope/consume côté pillz) ; il reprend au round suivant, **attribut par attribut** (un Annul Vie contre un Repair laisse passer les pillz). Annul Modif. Dégâts n'annule pas la Fury | `Card.cancelled_modifs`, `apply_capacity_lvl_4._suspended` | glossaire 56 ; combat réel 1211922 |
| Copie : lit les valeurs **imprimées** ; Copie Bonus seulement si le bonus adverse est actif ; Copie contre Copie → rien ; le texte copié garde ses conditions, **réévaluées pour le copieur** (pas « tel que joué ») ; les abilities de Leader et Genesis ne peuvent être copiées | `apply_capacity_lvl_1.apply_copies`, `drop_unmet_conditions` | glossaire 59 ; wiki *Oblivion* ; combat réel 1349481 |
| Impose : lit les valeurs **imprimées**, inverse de Copie | `_apply_value_copies_and_exchanges` | glossaire 172 |
| Echange : échange les valeurs **imprimées** même contre une Protection adaptée ; annulé par un Annul adapté (les deux cartes gardent alors leurs valeurs imprimées) ; face à une Copie ou un Echange du même type, seul l'Echange agit | `apply_capacity_lvl_1._opp_cancels_stat` | glossaire 60 ; combat réel 1294992 |

### Niveau 2 — Puissance, Dégâts, Attaque
| Règle | Moteur | Source |
|---|---|---|
| Sur une même carte, la réduction au **Min le plus haut s'applique d'abord** (à Min égal : bonus, pouvoir, Leader) | `apply_capacity_lvl_2._slots_highest_floor_first` | combats réels 1347131, 1294992 |
| Bet > N / < N compare `pillz_fight` directement (pillz gratuite comprise, fury exclue) | `process_round._bet_condition_met` | texte de carte (Zenith et autres) |
| Killshot : attaque ≥ 2 × attaque adverse, évaluée après les modificateurs | `process_round.apply_killshot_condition` | glossaire 68 |
| Versus (clan) s'active si le clan est présent n'importe où dans la **main** adverse, pas seulement en face | `check_capacity_condition` | glossaire 173 |
| Symétrie / Asymétrie : active si la carte adverse est / n'est pas en face | — | glossaire 174 |
| Support × cartes de ma main du même clan ; Brawl × cartes de la main adverse du clan affronté, **exemplaires comptés** ; Growth × numéro du round, Degrowth × rounds restants ; Equalizer × étoiles de la carte affrontée ; Per Opp. Power/Damage × valeur **imprimée** adverse | `multipliers` | glossaire 63, 64, 65, 67 |
| Per Pillz/Vie restante : lu **avant** la mise (pillz gratuite exclue) | `multipliers._nb_pillz_left`, `_nb_life_left` | glossaire 66 |
| per damage (Vie/Pillz) : dégâts réellement infligés après modificateurs, **0 si la carte perd** | `multipliers._nb_damage_inflicted` | glossaire 49 ; wiki *Terminology* |

### Combat, KO, fin de round
| Règle | Moteur | Source |
|---|---|---|
| Reanimate = « Defeat: +X Life » qui fonctionne aussi depuis 0 vie (soigne sur **toute** défaite, pas seulement un KO) | `apply_capacity_lvl_3` | wiki *Reanimate* |
| Recover X sur Y : ⌊pillz posées × X / Y⌋, **minimum 1**, pillz gratuite et fury comprises | `apply_capacity_lvl_3.recovered_pillz` | glossaire 53 ; combat réel 1347075 |
| Repair X, Max Y verse **X vies ET X pillz**, chacune plafonnée à Y | `apply_capacity_lvl_4._STATS_OF_KIND` | combat réel 1211702 |
| Poison/Toxine/Heal/Regen/Dope/Consume : au sein d'une même sorte, le second remplace le premier (Poison et Heal, sortes opposées, coexistent) ; Toxine, Régén, Dope, Consume, Repair, Combust, Mindwipe agissent **dès le round joué** ; Poison et Heal, aux rounds suivants | `apply_capacity_lvl_4.IMMEDIATE_KINDS` | glossaire 50, 51, 52 ; utilisateur |

### Bonus de clan, Leader, Oculus
| Règle | Moteur | Source |
|---|---|---|
| Le bonus de clan est actif à partir de 2 cartes **de noms distincts** du clan (les doublons ne comptent qu'une fois) | `is_clan_bonus_active` | glossaire 42 ; wiki *Bonus* |
| Team (Leader) s'applique à chaque carte jouée, **Leader compris**, seulement si le Leader est **unique** en main (deux exemplaires du même Leader, ou deux Leaders différents, s'annulent — bonus « Cancel Leader ») ; immunisé aux SoA | `leader_team_capacity` | wiki *Leader*, *Team* ; utilisateur |
| Infiltrated (Oculus) : 1 autre clan présent dans le tirage → ce clan ; 2 → le clan de la **carte seule** ; 3, ou 2 Oculus → rien. **Chaque Leader est son propre clan.** La liste de clans imprimée sur la carte ne restreint que le bonus/ability adoptés, pas l'appartenance au clan. Support et Brawl comptent les **exemplaires** de la carte seule, pas les noms distincts ; Unison (main mono-clan) ignore les doublons | `clan.infiltrated_clan`, `clan._clan_for_infiltration` | glossaire 175 ; combats réels 1346878, 1347500, 1347671, 1347602, 1349230, 1349443-1349511, 1214141 |
| Counter-attack (Ashigaru) et Limitless (Fractal) : codés et testés unitairement | `process_round.apply_leader_modes` | utilisateur seul — vérification par combat réel **abandonnée** (le combat 1349159 contredisait la règle énoncée pour Ashigaru) |

### Jour / Nuit
| Règle | Moteur | Source |
|---|---|---|
| Tiré au sort à la création de la partie ; les cartes `Day:` / `Night:` et le bonus GhosTown changent de texte selon la valeur tirée | `create_game` (`Game.night`), `Card(night=)` | glossaire 70 ; utilisateur |

## Pouvoirs exclus du moteur et de l'IA

Couverture du parseur : 1 386 / 1 395 descriptions (99,4 %, `scripts/capacity_coverage.py`). Tout ce qui a une
définition connue est implémenté et testé (code : `capacity_parser.py`, `apply_capacity_lvl_*.py`, `tests/`) ; cette
section liste seulement ce qui reste **volontairement** hors périmètre malgré une définition connue. Perfection
(Glibon Cr) et la coquille de Bugamon n'y figurent pas : ce ne sont pas des exclusions mais des cas sans règle
publiée (§ 3, R6).

| Mécanique | Définition (texte de carte) | Raison de l'exclusion |
|---|---|---|
| **Beyond** (Genesis) | « Si aucun joueur n'est KO à la fin des 4 rounds, une carte est tirée au hasard des decks restants pour un 5ᵉ round. » | Décision utilisateur (2026-09-23) : le moteur fixe `NB_ROUNDS = 4` |
| **Rebirth** (dont « Rebirth 1, Max. 1 », Nemo Cr) | Pas une mécanique : anciennes rééditions graphiques de cartes | Décision utilisateur (2026-09-21) |
| **Hazard** (Administrator, Leader) | Remplace les pouvoirs des 3 autres cartes du tirage par des pouvoirs aléatoires déjà utilisés dans le jeu | Décision utilisateur (2026-09-21) |
| **Bypass** (Robert Cobb, Leader) | Le bonus des autres cartes du joueur est actif même sans 2 cartes du clan | Décision utilisateur (2026-09-21) |
| **Illusion** (Kate, Leader) | Kate prend l'apparence et la position d'une des 3 autres cartes du tirage, au hasard, jusqu'à la révélation des pillz | Décision utilisateur (2026-09-21) ; concerne l'IA (information cachée), pas le moteur à information parfaite |
| **Overdose** (Hekate, Leader) | Fury inversée : sacrifier 2 dégâts (min. 0) pour 2 pillz en fin de round | Décision utilisateur (2026-09-21) |
| **Remove Ability Conditions** (Memento) | Définition wiki non exploitable | Décision utilisateur (2026-09-21) |

## Registre des règles non tranchées

**C'est le seul endroit où sont écrites les questions de règles ouvertes.** Chaque entrée dit ce que fait le moteur
aujourd'hui, pourquoi c'est incertain, la manipulation qui tranche (avec des cartes réelles) et la retouche à
appliquer si le serveur dit le contraire. Après chaque décision : corriger, ajouter un test de bout en bout,
régénérer les digests du corpus (`python scripts/build_engine_corpus.py`), et faire disparaître l'entrée d'ici —
le fait tranché rejoint « Règles confirmées » ci-dessus, sans y rester dupliqué.

| # | Question | Ce que fait le moteur aujourd'hui | Comment trancher |
|---|---|---|---|
| **R1** | Ordre de résolution entre les deux cartes | la carte **alliée** d'abord, aux niveaux 2, 3 et 4 | duel, 3 manips |
| **R2** | « Par Dégât » quand la carte perd | multiplicateur **0** | duel |
| **R3** | « Par Vie perdue » au-dessus de la vie de départ | borné à **0** (pas de malus) | duel avec un soin |
| **R4** | Protection de stat contre un « Cards » | la Protection **ne bloque pas** | duel |
| **R5** | Exchange contre Copie / Impose, Copie / Impose contre Cancel | non géré (aucune interaction) | duel |
| **R6** | Perfection (Glibon Cr) | pouvoir non parsé, carte injouable | aucune règle publiée |

### R1 — Ordre de résolution entre les deux cartes

Le moteur résout toujours la carte **alliée** avant la carte ennemie. Tant qu'aucun plancher, plafond ou liste
n'intervient, l'ordre est sans effet ; dès qu'il y en a un, le résultat dépend du camp qui s'appelle « allié » — ce
qui n'existe pas dans le vrai jeu. 25 scénarios asymétriques sont épinglés dans `tests/test_engine_properties.py`
(`KNOWN_ASYMMETRIES`) : une décision ici les fera disparaître.

Trois manipulations, chacune à **rejouer en inversant le premier joueur** : si le résultat suit l'ordre de jeu, la
règle est « le premier joueur d'abord ».

- **R1a, niveau 2 (stats)** — **Rajesh** (Uppers 2★ P5 D6, « -2 Cards Damage, Min 4 ») contre **Pandemos Cr**
  (Paradox 5★ P9 D8, « -4 Cards Damage, Min 0 »), 1 pillz chacun. Rajesh résolu en premier : 6→4 et 8→6, puis −4 →
  **Rajesh 0, Pandemos 2**. Pandemos en premier : 8→4 et 6→2, puis le « Min 4 » ne mord plus → **Rajesh 2,
  Pandemos 4**. Du simple au double.
- **R1b, niveau 3 (vie / pillz)** — faire **perdre** **Kusuri** (Fang Pi Clang 2★ P7 D2, « Defeat: +2 Life ») face à
  **Phyllis** (Nightmare 2★ P7 D1, « -3 Opp. Life Min 4 »), le joueur de Kusuri **à 6 vies**. Le gain résolu en
  premier donne 5 → 7 → **4** ; la perte en premier donne 5 → 4 (plancher) → **6**. Variantes : **Melinda** ou
  **Wonald** (« Defeat: +2 Life ») contre **Oxen** ou **Jeyn** (« -3 Opp. Life Min 5 »).
- **R1c, niveau 4 (effets persistants)** — faire **perdre** **Willow** (Roots 2★ P7 D2, « Defeat : Heal 1 Max. 10 »)
  contre une carte **Freaks** (bonus « Poison 2, Min 3 ») qui gagne, de sorte que le joueur de Willow soit à
  **exactement 10 vies après les dégâts du round** (le plafond du soin). Au round suivant : **8** (soin d'abord,
  sans effet à 10, puis poison) ou **9** (poison 10 → 8, puis soin).

Options si le moteur a tort : (a) garder « allié d'abord » ; (b) « le premier joueur d'abord » — symétrique et
cohérent avec l'ordre de jeu ; (c) au niveau 2, étendre la règle du plancher le plus haut aux deux cartes à la fois.

### R2 — « Par Dégât » quand la carte perd

`multipliers._nb_damage_inflicted` vaut 0 quand la carte perd le round (la victoire est confirmée par une source, la
défaite non). Conséquence : le volet « défaite » de trois cartes réelles ne peut jamais rien faire — **Zalindra**
(Zenith 3★ P9 D4, « Defeat: +1 Life Per Damage »), **Griffonmor Cr** (Skeelz 4★ P8 D4) et **Senestra** (Nightmare
3★ P8 D2), ces deux dernières en « Victory Or Defeat: +1 Life Per Damage ».

Manipulation : faire **perdre** Zalindra (1 pillz contre une grosse mise) et lire les vies gagnées ; puis Griffonmor
Cr ou Senestra en victoire (témoin) **puis** en défaite ; refaire une défaite face à un réducteur de dégâts
(Pussycats « -2 Opp Damage, Min 1 ») pour savoir si ce sont les dégâts imprimés ou après modificateurs.

Lecture probable : les dégâts après modificateurs, gagnante ou non. Si le moteur a tort : `_nb_damage_inflicted`
renvoie `card1.damage_fight` sans regarder `card1.win`.

### R3 — « Par Vie / Pillz perdue » au-dessus de la situation de départ

Le multiplicateur vaut l'écart avec la **situation de départ de la partie** (`Player.start_life` / `start_pillz`).
Reste une hypothèse : au-dessus de la vie de départ (un soin qui dépasse), le moteur **borne à 0**, faute de quoi le
pouvoir se retournerait en malus.

Manipulation : monter au-dessus de la vie de départ avec un soin (bonus Jungo « +2 Life », ou **Dallas**, All Stars
3★ « Heal 1 Max. 14 »), puis jouer **Razor** (Ulu Watu 4★ P5), **Zell** (Berzerk 1★ P6), **Padre Nido** (Paradox
3★ P6) ou **Miss Donna Luna** (Pussycats 2★ P3), toutes « +1 Power Per Life Lost », et lire la **puissance** :
inchangée si le plancher à 0 est juste, réduite si le jeu compte un écart négatif. Même question côté pillz avec un
« Per Pillz Lost » après un Dope ou un Recover.

### R4 — Protection de stat contre un « Cards »

`apply_capacity_lvl_1._apply_stat_protections` ne retire que les modificateurs adverses qui ciblent explicitement
l'adversaire (`target == "enemy"`). Un « -X Cards <stat> », qui vise **les deux** cartes, traverse donc la
Protection. L'utilisateur penche pour l'inverse (2026-09-22), sans source écrite.

Manipulation : **Vivian** (Berzerk 3★ P7 D4, « Protection : Damage ») face à **Giovanni** (Montana 3★,
« -2 Cards Damage, Min 1 »), 1 pillz chacun ; lire les **dégâts de Vivian** — le moteur donne **2**, la Protection
donnerait **4**. Idem **Fixit** (Bangers 5★ P7 D6, « Protection: Power And Damage ») face à Giovanni : moteur **4**,
attendu **6**. Attention, **Eyrton Cr** n'a sa Protection qu'à 2★ (à 5★ c'est un Cancel). Refaire une fois sur la
puissance avec **Delija Cr** (Roots 1★, « -2 Cards Power, Min 2 ») contre un « Protection: Power ».

Si le moteur a tort : `_strip_types(..., only_targeting_opponent=True)` doit aussi retirer les capacités
`target == "both"` quand la carte protégée est visée.

### R5 — Exchange contre Copie / Impose, et Copie / Impose contre Cancel

Un seul cas est tranché (combat 1294992, § « Règles confirmées ») : un Cancel Opp. X Modif. annule un X Exchange en
entier. Les autres croisements de ces trois pouvoirs, qui réécrivent tous les valeurs imprimées, ne sont couverts
par aucun combat et le moteur les traite dans l'ordre où il les rencontre.

Manipulation : un **Damage Exchange** (Blast, Homy, Serleena, Incubus Cr, Duchess, Waldegrin Cr) contre
**Copy: Opp. Damage** (Angelina, Bettisia, Darril, Dash), puis contre **Damage Impose** (Zwoosh, Zombiyaki) ; puis
Copie contre Cancel et Impose contre Cancel (Shaker, Lenora).

### R6 — Perfection, seul pouvoir sans règle publiée

**Perfection** (Glibon Cr) n'a de règle ni sur le site ni sur le wiki ; la carte qui le porte est injouable. S'y
ajoute une coquille probable du scraping, `Growth: -1 Power And Damage, Min 4` (Bugamon) — pas une question de
règle, mais de parsing.

Les sept pouvoirs exclus par décision (Beyond, Hazard, Illusion, Bypass, Overdose, Remove Ability Conditions,
Rebirth) sont documentés ci-dessus : ce ne sont pas des questions ouvertes.
