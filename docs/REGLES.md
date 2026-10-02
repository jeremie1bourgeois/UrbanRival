# Règles officielles d'Urban Rivals — registre du moteur

Confronte chaque décision de règle du moteur aux sources disponibles, et consigne ce qui reste incertain. Les
sections « Règles confirmées » et « Pouvoirs exclus » décrivent l'état **actuel** du moteur — les corrections
passées sont dans l'historique git, pas ici. **Le § 3 (registre R1-R7) est le seul endroit où sont écrites les
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
| Protection de stat : bloque aussi un « -X Cards <stat> » adverse, qui **continue de s'appliquer à son propre porteur** | `apply_capacity_lvl_1._strip_types` | combats réels 1412809, 1414093 |
| Annul Modif. Vie/Pillz suspend l'effet persistant adverse **pour le round où il est joué** (poison/toxine/heal/regen ; dope/consume côté pillz) ; il reprend au round suivant, **attribut par attribut** (un Annul Vie contre un Repair laisse passer les pillz). Annul Modif. Dégâts n'annule pas la Fury | `Card.cancelled_modifs`, `apply_capacity_lvl_4._suspended` | glossaire 56 ; combat réel 1211922 |
| Copie : lit les valeurs **imprimées** ; Copie Bonus seulement si le bonus adverse est actif ; Copie contre Copie → rien ; le texte copié garde ses conditions, **réévaluées pour le copieur** (pas « tel que joué ») ; les abilities de Leader et Genesis ne peuvent être copiées | `apply_capacity_lvl_1.apply_copies`, `drop_unmet_conditions` | glossaire 59 ; wiki *Oblivion* ; combat réel 1349481 |
| Copie de puissance / dégâts : annulée stat par stat par un Annul adapté porté par la carte visée (« Copy: Power And Damage Opp. » contre « Cancel Opp. Damage Modif. » : puissance copiée, dégâts imprimés) | `apply_capacity_lvl_1._opp_cancels_stat` | combat réel 1734264 |
| Impose : lit les valeurs **imprimées**, inverse de Copie ; annulé par un Annul adapté porté par la carte visée | `_apply_value_copies_and_exchanges`, `_opp_cancels_stat` | glossaire 172 ; combats réels 1412809, 1414093 |
| Echange : échange les valeurs **imprimées** même contre une Protection adaptée ; annulé par un Annul adapté (les deux cartes gardent alors leurs valeurs imprimées) ; face à une Copie ou un Echange du même type, seul l'Echange agit | `apply_capacity_lvl_1._opp_cancels_stat` | glossaire 60 ; combat réel 1294992 |

### Niveau 2 — Puissance, Dégâts, Attaque
| Règle | Moteur | Source |
|---|---|---|
| La réduction au **Min le plus haut s'applique d'abord**, quelle que soit la carte qui la porte (à Min égal : carte alliée puis ennemie, et bonus, pouvoir, Leader) | `apply_capacity_lvl_2._modifiers_highest_floor_first` | combats réels 1347131, 1294992, 1414453 |
| Bet > N / < N compare `pillz_fight` directement (pillz gratuite comprise, fury exclue) | `process_round._bet_condition_met` | texte de carte (Zenith et autres) |
| Killshot : attaque ≥ 2 × attaque adverse, évaluée après les modificateurs | `process_round.apply_killshot_condition` | glossaire 68 |
| Versus (clan) s'active si le clan est présent n'importe où dans la **main** adverse, pas seulement en face | `check_capacity_condition` | glossaire 173 |
| Symétrie / Asymétrie : active si la carte adverse est / n'est pas en face | — | glossaire 174 |
| Support × cartes de ma main du même clan ; Brawl × cartes de la main adverse du clan affronté, **exemplaires comptés** ; Growth × numéro du round, Degrowth × rounds restants ; Equalizer × étoiles de la carte affrontée ; Per Opp. Power/Damage × valeur **imprimée** adverse | `multipliers` | glossaire 63, 64, 65, 67 |
| Per Pillz/Vie restante : lu **avant** la mise (pillz gratuite exclue) | `multipliers._nb_pillz_left`, `_nb_life_left` | glossaire 66 |
| Per Pillz perdue : écart entre les pillz de départ de la partie et celles d'avant la mise du round, **borné à 0** au-dessus (13 pillz pour 12 au départ : ni bonus ni malus) | `multipliers._nb_pillz_lost` | combats réels 1649648, 1650032 (Korapacce), 1734264 (Korapacce au-dessus du départ) |
| Per Vie perdue : écart avec la vie de départ de la partie, **borné à 0** au-dessus (un soin qui dépasse ne donne pas de malus) | `multipliers._nb_life_lost` | combat réel 1649965 (Zell à 16 vies sur 15, puissance inchangée) |
| per damage (Vie/Pillz) : dégâts de la carte, **qu'elle gagne ou perde** — en défaite, ses propres dégâts, pas ceux qu'elle subit | `multipliers._nb_damage_inflicted` | glossaire 49 ; combats réels 1736136, 1735837 |

### Combat, KO, fin de round
| Règle | Moteur | Source |
|---|---|---|
| Un effet de vie / pillz **sans préfixe** (`Defeat`, `Backlash`, `Victory Or Defeat`) n'agit que si la carte **gagne** le round, qu'il soigne son camp ou frappe l'adversaire. Sa condition d'activation (Bet, Equalizer, Courage…) est consommée en amont par `check_capacity_condition` et ne dispense pas de gagner | `apply_capacity_lvl_3.check_capacity_condition_lvl_3` | combats réels 1402251 (Akem, « Bet < 6 Pillz: +3 Life » non versé), 1414369 et 1414453 (Owen, « -4 Opp. Life Min 2 » non infligé) |
| Vie / pillz en fin de round : les **gains avant les pertes**, quels que soient la carte qui les porte et le premier joueur — un plancher (« -4 Opp. Life Min 2 ») mord après le « Defeat: +2 Life » adverse | `apply_capacity_lvl_3` | combats réels 1734030, 1734587, 1734860 |
| Reanimate = « Defeat: +X Life » qui fonctionne aussi depuis 0 vie (soigne sur **toute** défaite, pas seulement un KO) | `apply_capacity_lvl_3` | wiki *Reanimate* |
| Recover X sur Y : ⌊pillz posées × X / Y⌋, **minimum 1**, pillz gratuite et fury comprises | `apply_capacity_lvl_3.recovered_pillz` | glossaire 53 ; combat réel 1347075 |
| Repair X, Max Y verse **X vies ET X pillz**, chacune plafonnée à Y | `apply_capacity_lvl_4._STATS_OF_KIND` | combat réel 1211702 |
| Poison/Toxine/Heal/Regen/Dope/Consume : au sein d'une même sorte, le second remplace le premier (Poison et Heal, sortes opposées, coexistent) ; Toxine, Régén, Dope, Consume, Repair, Mindwipe agissent **dès le round joué** ; Poison, Heal et Combust, aux rounds suivants. Une Toxine remplace le Poison du joueur visé, qui n'agit pas au round de la Toxine (combat réel 1647870) ; une Regen remplace de même le Heal du joueur (combat réel 1734431). Mindwipe est un Combust immédiat : même sorte d'effet, marqué `how` « immediate » au parsage. Les **gains agissent avant les pertes** (combat réel 1735837 : Heal puis Poison) | `apply_capacity_lvl_4.IMMEDIATE_KINDS`, `_REPLACED_BEFORE_ACTING` | glossaire 50, 51, 52 ; utilisateur ; combats réels 1638346 (Combust), 1211702, 1214027, 1214141 (Mindwipe), 1647870, 1734431, 1735837 |

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
| **R1** | Fin de round : « les gains avant les pertes », ou « la carte perdante d'abord » au niveau 3 ? | les gains d'abord, aux niveaux 3 et 4 | 1 duel |
| **R2** | « Par Dégât » : dégâts imprimés ou après modificateurs ? | après modificateurs | duel face à un réducteur |
| **R5** | Exchange contre Copie / Impose | appliqués dans l'ordre rencontré, sans interaction ; conforme aux combats du 23/09 | duel avec un 3ᵉ modificateur intercalé |
| **R6** | Perfection (Glibon Cr) | pouvoir non parsé, carte injouable | aucune règle publiée |

### R1 — Gains avant pertes, ou carte perdante d'abord ?

L'ordre ne dépend **ni du camp ni du premier joueur** : c'est tranché à tous les niveaux.

- **Niveau 2** — combat réel 1414453 : le plancher le plus haut s'applique d'abord, quelle que soit la carte qui le
  porte (§ « Règles confirmées »). Une lecture par cumul des deux réductions sous le plancher le plus bas donne le
  même résultat sur ce combat ; il faudrait une grosse réduction mordant son propre plancher pour les départager.
- **Niveau 3** — combats réels 1734030 r2, 1734587 r2 et 1734860 r3 : le « Defeat: +2 Life » de la carte perdante
  (Kusuri, Eugene) passe avant le « -X Opp. Life Min Y » du gagnant (Owen, Zeke), que son porteur ait joué en
  premier ou en second, qu'il soit le joueur 0 ou 1 du serveur.
- **Niveau 4** — combats réels 1413898 et 1735837 r3 : le Heal agit avant le Poison, le porteur du soin jouant en
  premier puis en second.

Le moteur applique donc « les gains avant les pertes » aux niveaux 3 et 4, et `KNOWN_ASYMMETRIES` est passé de 5 à
**2** scénarios (l'ordre d'enregistrement des effets persistants). Reste une lecture concurrente au **niveau 3** :
dans les trois combats, le gain venait de la carte **perdante** (« Defeat: »), donc « la carte perdante d'abord »
donne les mêmes nombres.

Manipulation : un gain porté par le **gagnant** contre une perte portée par le **perdant**. Faire gagner **Grace**
(Riots, « +1 Pillz Per Damage », D2) contre **Antoinette** (Freaks 2★ niveau 2, « Defeat: -2 Opp. Pillz, Min 3 »),
le joueur de Grace à **3 pillz** après sa mise : les gains d'abord donnent 3 → 5 → **3** ; la perdante d'abord,
3 → 3 (plancher) → **5**.

### R2 — « Par Dégât » : dégâts imprimés ou après modificateurs ?

**La défaite est tranchée** par les combats réels 1736136 r1 et 1735837 r4 : **Zalindra** (Zenith 3★ P9 D4,
« Defeat: +1 Life Per Damage ») perd et rend ses **propres** 4 dégâts — y compris quand elle n'en subit qu'un
(1735837). Le moteur lit les dégâts **après modificateurs** (`card1.damage_fight`), gagnante ou non ; dans ces deux
combats, les dégâts de Zalindra n'étaient pas modifiés.

Manipulation : faire perdre Zalindra (ou **Griffonmor Cr**, Skeelz 4★ D4, et **Senestra**, Nightmare 3★ D2, toutes
deux « Victory Or Defeat: +1 Life Per Damage ») face à un réducteur de dégâts (Pussycats « -2 Opp Damage, Min 1 ») :
4 vies rendues pour les dégâts imprimés, 2 après modificateurs.

### R5 — Exchange contre Copie / Impose

Trois cas sont tranchés (§ « Règles confirmées ») : un Cancel Opp. X Modif. annule un X Exchange en entier (combat
1294992), un X Impose (combat 1412809) et une Copie de X (combat 1734264). Le moteur traite les autres croisements
dans l'ordre où il les rencontre.

Les combats du 23 septembre **contraignent** Exchange contre Copie et Exchange contre Impose sans les départager.
Ce qu'ils excluent : la Copie ne lit pas le résultat de l'Échange (1412809 r1, 1412980 r1, 1414277 r4 — Blast D2 contre
Flood Ed « Copy: Power And Damage Opp. », l'Échange porte Blast à 3 et Flood Ed finit à **2**, la valeur imprimée
de Blast, non à 3) ; et l'Impose ne rend pas au lanceur sa valeur imprimée, l'Échange tient sur lui (1402174 r2,
Honikai à 6 = 3 reçus + 3 de bonus ; 1412902 r4, Honikai à 5 = 3 reçus + 2 de fury — dans les deux cas 2+X aurait
donné un de moins).

Ce qu'ils ne départagent pas, et pourquoi c'est structurel : dans un échange à deux, la valeur reçue par une carte
**est** la valeur imprimée de l'adversaire — exactement ce qu'une Copie ou un Impose lui donnerait. « Les deux
pouvoirs agissent, chacun sur les imprimées » et « seul l'Échange agit » produisent donc le même nombre. Les sept
occurrences de « Reprisal: Damage Impose » de ces 17 combats — trois face à un Échange, trois face à un Cancel —
sont toutes sans effet observable.

Manipulation : il faut un **troisième modificateur intercalé** entre l'Échange et la Copie / l'Impose, sinon les
deux lectures resteront confondues quel que soit le nombre de duels.

### R6 — Perfection, seul pouvoir sans règle publiée

**Perfection** (Glibon Cr) n'a de règle ni sur le site ni sur le wiki ; la carte qui le porte est injouable. S'y
ajoute une coquille probable du scraping, `Growth: -1 Power And Damage, Min 4` (Bugamon) — pas une question de
règle, mais de parsing.

Les sept pouvoirs exclus par décision (Beyond, Hazard, Illusion, Bypass, Overdose, Remove Ability Conditions,
Rebirth) sont documentés ci-dessus : ce ne sont pas des questions ouvertes.
