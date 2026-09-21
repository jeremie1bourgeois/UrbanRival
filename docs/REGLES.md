# Règles officielles d'Urban Rivals — audit du moteur

Audit documentaire réalisé le 2026-09-16 (`main` = `6f02fc5`). Objectif : confronter chaque décision de règle prise
« sans certitude » (voir `docs/ROADMAP.md` § 1) aux règles officielles, et documenter les mécaniques non encore gérées.

Ce document ne remplace pas la vérification par rejeu de combats réels (ROADMAP § 2.B.2) : il tranche ce que les
textes tranchent, et liste explicitement ce qu'ils ne tranchent pas.

## 1. Sources et accès

| Source | Statut | Accès |
|---|---|---|
| **Règles officielles** `urban-rivals.com/game/rules/` (glossaire de 35 entrées : Fury, Bonus, Ability, Stop, Copy, Recover, Killshot, Impose, Infiltration…) | Existe, **mais le contenu exige d'être connecté** (`?question=N` charge le texte en AJAX, 401 `session_expired` sans cookie ; la page redirige vers l'écran de connexion). | À lire connecté : `https://www.urban-rivals.com/game/rules/?question=41` (Fury) … `=175` (Infiltration). Liste des identifiants en annexe A. |
| **Base de connaissances du support** `support.urban-rivals.com` — article 2.8 « Ability, Bonus, Stop Ability, Stop Bonus, what is the order and what are the priorities? » (id 91) et 3.2 « List of current abilities » (id 3578) | Site fermé (redirige vers `/support/`). L'article 91 est **archivé** sur la Wayback Machine ; le 3578 n'a pas pu être récupéré (archive indisponible pendant l'audit). | `https://web.archive.org/web/2023/https://support.urban-rivals.com/index.php?pg=kb.page&id=91` |
| **Wiki des joueurs** `urban-rivals.fandom.com` | Accessible via l'API MediaWiki (`/api.php?action=parse&page=<Titre>&prop=wikitext`) ; la page HTML est derrière Cloudflare. Les définitions y sont le plus souvent recopiées du texte officiel des cartes (entre guillemets). | `https://urban-rivals.fandom.com/wiki/<Titre>` |

Hiérarchie de confiance : support officiel > glossaire officiel > texte de carte cité par le wiki > prose du wiki.

## 2. Règles de base du round

| Règle | Source | Moteur | Verdict |
|---|---|---|---|
| Attaque = Puissance × Pillz ; 1 pillz gratuite obligatoire par round ; 12 pillz au départ ; 12 vies | wiki *Pillz*, *Attack* | `process_round` | ✅ Confirmé |
| Fury : 3 pillz pour +2 dégâts, ajoutés après les réducteurs de dégâts | wiki *Fury* + utilisateur | `process_round` | ✅ Confirmé |
| Égalité d'attaque : la carte de **niveau (étoiles) le plus bas** gagne ; à niveau égal, **celui qui a joué en premier** gagne | wiki *Power* (« the card with a lower star count wins ») + FAQ support | `resolve_combat` | ✅ Confirmé |
| Bonus de clan actif avec **≥ 2 cartes du clan** dans la main. Précision : « This doesn't apply to the same Characters » — deux exemplaires de la même carte **ne comptent pas** | wiki *Bonus* | `is_clan_bonus_active` compte les noms distincts par clan | ✅ Confirmé (doublons possibles selon le mode, confirmé par l'utilisateur) |
| Fin de partie : KO à 0 vie ; sinon, après 4 rounds, plus de vie gagne ; vies égales = **match nul** | wiki *KO*, *Life* | `check_end` (`GameResult.DRAW`) | ✅ Confirmé |
| Premier joueur du round 1 : aléatoire dans le jeu, puis alternance | wiki *Strike Back* (« the order of play is decided randomly ») | toujours l'allié (`turn = True`) | ⚠️ Connu, non modélisé (ROADMAP § 1) |
| Puissance minimale 1, pillz minimale 1 → attaque minimale 1 hors effets ; mais un réducteur « Min 0 » (−X Opp Power / Attack, Min 0) descend bien à **0** | wiki *Power* + utilisateur (2026-09-21) | `apply_capacity_lvl_2` respecte la borne du texte, pas de plancher implicite ; `test_minus_opp_power_min_0_*`, `test_minus_opp_attack_min_0_*` | ✅ Confirmé |

## 3. Verdict sur les décisions prises sans certitude

> **Mise à jour 2026-09-16** : les corrections des points 3.1, 3.3, 3.4, 3.6, 3.8 et de Versus (§ 4) ont été appliquées
> au moteur (branche `fix/regles-officielles`), avec les exemples officiels comme tests. Le texte ci-dessous décrit l'état
> **avant** correction. Recover (3.5, minimum 1) est laissé en l'état : source trop fragile.

Les numéros suivent le tableau de `docs/ROADMAP.md` § 1. Les trois premiers points sont **prioritaires** : ce sont
des erreurs avérées, fréquentes en jeu (tous les clans à Stop, Zenith, Oculus).

### 3.1 Stop Opp. Ability contre Stop Opp. Bonus — ❌ CONTREDIT (source officielle)

**Moteur** : résolution simultanée (`apply_capacity_lvl_1._apply_stops` : « simultané : calculé avant toute
suppression ») — chaque Stop agit même s'il est lui-même stoppé.

**Règle officielle** (support, article 91, cité intégralement) :

> There are no priorities. The way to work out if an ability is activated is quite easy: start from the Ability/Bonus
> that you want to know whether it is activated or not, check that nothing is blocking it and if this is the case,
> that nothing is blocking the Ability/Bonus block, just like a chain.
>
> Example 1: your character has +8 Attack as his ability and Stop Bonus as his Bonus, his opponent has Stop Ability as
> his Bonus. Is your Ability activated? **Yes**, because your Ability might be blocked by your opponent's Bonus, but
> your Bonus blocks his Bonus.
>
> Example 2: your character has +2 Power as his Bonus and Stop Opp Ability as his Ability, his opponent has Stop Opp
> Bonus as his Ability. Is your Ability activated? **Yes**, because your Bonus might be blocked by your opponent's
> Ability, but your Ability blocks his Ability.

Autrement dit : **un Stop stoppé ne stoppe rien** (résolution en chaîne, pas simultanée).

**Reproduction dans le moteur** (`UrbanPy/Backend_fastAPI/scripts/regles_kb91_check.py`, Amelia P3 / Asporov P7, 1 pillz) :

| Exemple officiel | Attendu | Moteur actuel |
|---|---|---|
| Ex. 1 : ability « Attack +8 » + bonus SoB contre bonus SoA | attaque 3 + 8 = 11 | **3** |
| Ex. 2 : bonus « Power +2 » + ability SoA contre ability SoB | puissance 3 + 2 = 5 | **3** |
| Test actuel `test_stops_resolve_simultaneously_soa_versus_sob` (ability SoA contre ability SoB) | l'ability SoA n'est bloquée par rien → elle stoppe le SoB adverse → **Amelia garde son bonus** (3), Asporov perd son ability | Amelia 1, Asporov 7 |

**Cas non tranché par la source** : cycle pur (SoA contre SoA en ability, ou Protection: Ability + Protection: Bonus
face à SoA + SoB). L'algorithme « en chaîne » ne termine pas ; le moteur fait gagner les Stops (« cycle : les Stops
gagnent »), ce qui correspond à l'expérience communautaire (deux SoA face à face s'annulent). **Confirmé par
l'utilisateur le 2026-09-21** (les deux cycles). Point 3.2 ci-dessous.

**Correction** : `_stopped_kinds` doit considérer qu'un Stop porté par un emplacement lui-même stoppé n'existe pas
(point fixe : itérer jusqu'à stabilité, cycle → Stops gagnent). Réécrire le test cité et ajouter les deux exemples
officiels comme tests.

### 3.2 Protection cyclique — ✅ CONFIRMÉ (utilisateur, 2026-09-21)

Aucune source écrite ne décrit le cas ; l'utilisateur confirme par connaissance du jeu que dans les deux cycles
(SoA contre SoA ; Protection: Ability + Protection: Bonus face à SoA + SoB) **les Stops gagnent**. Tests
`test_soa_versus_soa_is_a_cycle_where_both_stops_win` et `test_double_protection_versus_all_stop_is_a_cycle_where_the_stops_win`.

### 3.3 « Cancel Opp. Life Modif. » et le poison — ❌ CONTREDIT (texte de carte, via wiki)

**Moteur** : le poison n'est pas annulé (`_strip_types` ne touche pas au type `poison`).

**Source** (wiki *Cancel Opp. Life Modif.*) :

> Any modifier of the opposing character affecting life will be deactivated. This applies to life reductions AND
> increases. This effect is not a Stop Ability or a Stop Bonus. **The effects of your opponent's poison, toxin, regen
> and heal abilities will be deactivated for the round in which the "cancel opponent life modification" is activated.**

Le poison, la toxine, le regen et le heal de la carte adverse **sont** annulés. Interprétation la plus plausible : la
capacité persistante de la carte adverse jouée ce round n'est pas posée (elle n'agit qu'aux rounds suivants, donc
« deactivated for the round » ne peut viser que sa pose). Une lecture alternative — un poison déjà en place ne tique
pas ce round — est possible mais moins cohérente avec « modifier of the opposing **character** ».

**Correction** : `_strip_types` doit retirer aussi `poison`, `toxine`, `heal`, `regen` (et vraisemblablement `-X Opp
Life`, `+X Life`, `per damage` life, déjà couverts par le type `life`) quand le Cancel vise la vie.

### 3.4 Reanimate — ❌ CONTREDIT partiellement (texte de carte)

**Moteur** : n'agit que si son porteur tombe à 0 vie ; sinon rien (`apply_capacity_lvl_3` : « Reanimate n'agit que
sur un KO »).

**Source** (wiki *Reanimate: +X Life*, texte de carte) :

> If your card loses the fight, you will win +X Life Points at the end of the round. This ability is able to prevent
> you from going KO.

Reanimate est donc un **« Defeat: +X Life » qui fonctionne aussi depuis 0** : il soigne à chaque défaite, KO ou pas.
Ce que le moteur fait déjà sur KO (soin et reprise de la partie) est confirmé ; ce qu'il ne fait pas (soin sur défaite
sans KO) est contredit. `test_reanimate_does_not_heal_on_victory` reste valide.

### 3.5 Recover X out of Y : fury comprise — ✅ CONFIRMÉ ; minimum — ⚠️ À CORRIGER

**Fury** : wiki *Vortex* (bonus « Defeat: Recover 2 Pillz out of 3 ») : « Fury counts as pillz used for their
bonus ». Le moteur compte les 3 pillz de fury (`pillz_bet`) : confirmé.

**Minimum** : deux pages indiquent un plancher de 1 pillz récupérée — wiki *Victory Or Defeat: Recover X Pillz Out Of
X* : « rounded down to the nearest unit, **with a minimum of 1** » ; wiki *Recover X Pillz Out Of X* : « 2 Pillz Out
Of 3 = spending **1** Pillz gives you **1** back ». Le moteur renvoie ⌊1 × 2 / 3⌋ = 0. Les exemples de cette dernière
page sont par ailleurs arithmétiquement incohérents (« 1 out of 2 = spending 2 gives you 2 back ») : source fragile,
à confirmer en combat réel, mais deux mentions concordantes du minimum.

**Pillz comptées** : « of the Pillz placed on your card » — la pillz gratuite **est comprise** : combat réel 1347075,
Pyro (Defeat: Recover 1 Pillz Out Of 2) pose 4 pillz (3 misées + la gratuite) et en récupère 2 (12 − 3 = 9 → 11), et
non ⌊3/2⌋ = 1. Cohérent avec Bet (3.8). Le plancher de 1 reste non observé en combat réel.

### 3.6 Infiltrated (Oculus) — ✅ TRANCHÉ (règle officielle + 5 combats réels)

**Source** (texte officiel du bonus « Infiltré », fourni par l'utilisateur le 2026-09-21 ; identique au wiki *Oculus*) :

> Si un seul autre clan est présent dans le tirage, le personnage Oculus est considéré comme une carte de ce clan. Si
> deux autres clans sont présents, le personnage Oculus appartiendra au clan du personnage seul, activant ainsi son
> bonus. Si trois autres clans sont présents dans le tirage, ou si vous avez plus d'un Oculus dans le tirage, le bonus
> Infiltré n'a pas d'effet.

Avec 3 autres cartes : 1 clan (3 cartes) → ce clan ; 2 clans (2 + 1) → le clan de la **carte seule** (c'est le seul
cas où l'infiltration change quelque chose : elle active un bonus qui ne l'était pas) ; 3 clans → rien ; deux Oculus →
rien. Moteur : `clan.infiltrated_clan`.

**Les Leaders** ne sont pas traités par le texte. Combats réels (`data/ur_battles/`) :
- 1346878, Bangers ×2 + Morphun + Dark Morphun : pas de bonus Bangers (puissance 6, pas 8) et Morphun annulé (pillz
  12 − 3 = 9, pas 10) → l'Oculus a rejoint le Leader, carte seule, et compte comme second Leader (« Cancel Leader »).
- 1347500, Freaks ×2 + Ashigaru + Dark Majestic : Counter-attack annulé (ordre de jeu p0, p1, p0, p1 au lieu de
  toujours second) → idem.
- 1347671, Sofilia (Freaks) + Administrator + Ashigaru + Dark Majestic : « Support: Attack +3 » de Sofilia donne +3
  (×1) → l'Oculus n'a **pas** rejoint les Freaks, alors que Freaks ×1 contre Leader ×2 en ferait la carte seule.
- 1347602, Freaks ×3 + Dark Majestic : Support ×4 → l'Oculus a rejoint les Freaks.
- 1214141 (branche `feat/ia-tous-modes`) : trois autres clans → rien.

Seule lecture compatible avec le texte et les cinq combats : **chaque Leader est son propre clan**. Un Leader seul face à
deux cartes d'un clan est la carte seule (l'Oculus le rejoint et le Cancel Leader l'annule) ; deux Leaders différents
plus une carte font trois clans (rien). Moteur : `clan._clan_for_infiltration`, tests `test_infiltrated.py`.
Cas non observé : deux clans différents + un Leader (trois clans selon cette lecture → rien).

**Clans listés sur la carte** (wiki *Infiltrated* : « les icônes de clan dans la section Pouvoir indiquent quels clans
doivent être infiltrés pour activer son bonus ») : la liste, lue dans le texte du pouvoir (« Infiltrated Bangers,
Cosmohnuts, … : ») restreint le **bonus adopté** et l'**ability**, pas l'appartenance au clan (1346878 : le Leader
n'est listé nulle part, l'Oculus le rejoint quand même). Moteur : `clan.infiltrable_clans`, `process_round.apply_infiltrated_bonus`.

**Support avec un Oculus** : 1347602 — l'Oculus rallié aux Freaks compte pour Support, et les deux exemplaires de
Sofilia comptent chacun (contrairement à l'activation du bonus, qui compte les personnages distincts). Brawl aligné
par symétrie, non vérifié. Moteur : `multipliers._support`, `_brawl`.

### 3.6 bis Ordre bonus / pouvoir sur une même carte — ✅ TRANCHÉ (attaque)

Combat réel 1347131, round 2 : Donna Black (bonus « -12 Opp Attack, Min 8 », pouvoir « Revenge: -10 Opp Attack, Min 3 »)
contre Liona à 14 d'attaque → 3. Seul l'ordre **bonus puis pouvoir** le donne (14 → 8 → 3) ; pouvoir puis bonus donnerait
4 (14 → 4, puis le Min 8 ne fait rien). Le moteur applique désormais le bonus avant le pouvoir pour tous les
modificateurs de niveau 2 (puissance, dégâts, attaque) ; seule l'attaque est vérifiée en combat réel.

### 3.7 Team (Leader) — ✅ CONFIRMÉ

- Deux Leaders s'annulent (bonus « Cancel Leader ») : wiki *Leader* — ✅ confirmé.
- « Team abilities are not affected by SoA » (wiki *Team*) : le moteur porte la capacité dans `leader_fight`, hors
  des emplacements visés par `_apply_stops` — ✅ confirmé.
- Le Leader lui-même bénéficie de son Team : non documenté, **confirmé par l'utilisateur (2026-09-21)**. Le moteur dit oui
  (`test_team_ability_applies_to_the_leader_itself`).
- Deux exemplaires du **même** Leader (modes avec doublons) s'annulent comme deux Leaders différents : **confirmé par
  l'utilisateur (2026-09-21)**, `test_two_copies_of_the_same_leader_cancel_the_team_ability`.

### 3.8 Bet > N / < N : pillz comptées — ❌ CONTREDIT (texte de carte, plusieurs occurrences)

**Moteur** : compare `pillz_fight − 1`, c'est-à-dire **sans** la pillz gratuite, sans la fury.

**Source** (texte de carte cité sur wiki *Zenith* — bonus « Bet > 3 Pillz: +3 Life » —, *Bet Under X Pillz: +Y Life*,
*Bet Over X Pillz: Copy Opp. Ability*, à chaque fois la même formule) :

> This effect applies only if the player has bet a number of Pillz strictly greater than 3 (**including free Pillz and
> excluding Fury**).

Et wiki *Zenith*, inconvénients : « They must use at minimum 4 pillz and fury doesn't count towards that » — soit
4 pillz **au total**, gratuite comprise.

**Reproduction** : « Bet > 3 Pillz: +3 Life », victoire avec 4 pillz au total → officiel : +3 vies ; moteur : rien
(il faut 5 pillz). Décalage de un.

**Correction** : `_bet_condition_met` doit comparer `pillz_fight` directement. Fury exclue : confirmé.

### 3.9 Killshot — ✅ CONFIRMÉ

Wiki *Killshot* : « If the Attack of attacker's card is equal or higher than the double of the opposing character's
attack ». Évaluation après les modificateurs d'attaque : implicite (l'« Attack » est la valeur finale). Le garde
`attack > 0` du moteur est sans effet en pratique (attaque minimale 1).

### 3.10 per damage : dégâts réellement infligés — ✅ CONFIRMÉ

Wiki *Terminology* (« +X Life per Damage ») : « Fury, damage-enhancing bonuses (if any), and the opposing character's
damage-reducing abilities/bonuses (if any) are also taken into account ». Exemple donné : Kenny 6/3 +2 Life per Damage
→ 3 dégâts, +6 vies. Le moteur utilise `damage_fight` après tous les modificateurs.

### 3.11 Copy — ✅ CONFIRMÉ

- Wiki *Copy: Opp. Bonus* : « If the opponent's Bonus is not activated, then this ability has no effect. This ability
  cannot be copied. » → copier l'emplacement « tel que joué » et Copy contre Copy → rien : confirmé.
- Wiki *Oblivion* (bonus « Copy: Opp. Ability ») : « Leader and Genesis abilities cannot be copied. » Le moteur ne joue
  jamais l'ability « Team » comme ability de carte (`check_capacity_condition` la refuse), donc rien à copier :
  confirmé. Genesis (« Beyond ») n'est pas géré.
- Wiki *Copy: Opp. Power* / *Power Impose* : « only takes into account the figure shown on the card and does not
  include changes related to an Ability, Bonus or Fury » → copie de la **valeur imprimée**.
  `_apply_value_copies_and_exchanges` lit bien `opp.power` / `opp.damage` (valeurs imprimées) : confirmé.

### 3.12 Fury ajoutée après les modificateurs de dégâts — ✅ CONFIRMÉ (utilisateur, 2026-09-16)

Aucune source textuelle trouvée ; l'utilisateur confirme par connaissance du jeu que la fury s'applique **après** les
réducteurs de dégâts (une carte 2 dégâts + fury face à « −2 Opp Damage, Min 1 » inflige 1 + 2 = 3). C'est ce que fait
le moteur (`process_round` : « Appliquer les fury » après `lvl_2`).

### 3.13 `Day:` toujours valide, `Night:` jamais — ⚠️ DÉCISION UTILISATEUR

Wiki *Day/Night* : les deux conditions dépendent de l'heure dans le jeu. Le moteur ne modélise pas le cycle ; choix
assumé, sans conséquence tant que le jeu n'est pas comparé à des combats réels joués de nuit.

### Synthèse

| # | Décision | Verdict | Effort |
|---|---|---|---|
| 3.1 | Stops simultanés | ❌ contredit (source officielle, 2 exemples reproduits) | moyen : point fixe dans `_stopped_kinds` + 3 tests |
| 3.8 | Bet sans la pillz gratuite | ❌ contredit | trivial : une ligne + tests |
| 3.6 | Infiltrated = clan majoritaire | ❌ contredit (+ restriction de clans listés) | petit ; données à vérifier |
| 3.3 | Cancel Life Modif. épargne le poison | ❌ contredit | petit |
| 3.4 | Reanimate seulement sur KO | ❌ contredit partiellement | petit |
| 3.5 | Recover : fury comprise / minimum 0 | ✅ fury / ⚠️ min 1 | trivial |
| 3.9, 3.10, 3.11 | Killshot, per damage, Copy | ✅ confirmés | — |
| 3.7 | Team | ✅ confirmé (Cancel Leader, immunité SoA, Leader inclus, doublons de Leader) | — |
| 3.12 | Fury après les réducteurs | ✅ confirmé (utilisateur) | — |
| 3.2 | Protection cyclique | ✅ confirmé (utilisateur) : les Stops gagnent | — |
| 3.13 | Day/Night | choix utilisateur | — |

## 4. Mécaniques non gérées : définitions retrouvées

> **Mise à jour 2026-09-16 (soir)** : toutes les mécaniques de ce tableau qui ont une définition sont **implémentées**
> (branche `feat/pouvoirs-regles`), sauf Beyond (hors périmètre) et les cartes uniques sans définition (Hazard, Illusion,
> Bypass, Overdose, Remove Ability Conditions, Rebirth 1 Max 1, Perfection). Couverture : 1 386 / 1 396 descriptions.

Textes de cartes (entre guillemets sur le wiki), utilisables directement comme spécification. Ordre du tableau
ROADMAP § 2.A.

| Mécanique | Définition | Type d'implémentation |
|---|---|---|
| **Tune Out** (bonus Cosmohnuts) | « When a Tune Out card is played, the Attack calculation is ignored and the winner of the round is the player who bet the most Pillz. In case of a tie in Pillz, the two cards are decided in the same way as for a tie in Attack. » | Nouveau mode de résolution dans `resolve_combat` ; la fury **ne compte pas** (utilisateur, 2026-09-21 ; `test_tune_out_ignores_the_fury_pillz`) |
| **Unison: X** | « only activates if the hand of the player contains EXCLUSIVELY cards of the same clan as the card which has the Unison effect » | Condition de début de round (main mono-clan) |
| **Disunion: X** | « only activates if the hand of the player at least contains ONE card from a different clan » | Condition, négation d'Unison |
| **After (Clan X[, Clan Y]): X** (bonus Tolvack + abilities) | « This effect only activates if you played a "Clan X" character in the previous round. Oculus characters, even when infiltrated "Clan X", do not count. » Ne s'active jamais au round 1. | Condition sur `history[-1]` (clan de la carte jouée par le même joueur au round précédent) |
| **Perfect: X** | « your card has to have the exact amount of Pillz needed » — une pillz de moins aurait perdu, une de plus est gaspillée. Exemple : adversaire 25 d'attaque, puissance 8 → exactement 4 pillz (32). | Condition différée après le calcul des attaques (victoire et `attack − power_fight < opp.attack`) |
| **Consume X, Min Y** | « If your card wins the round, the opponent will lose X Pillz, minimum Y. This effect will be felt at the end of each of the following rounds. (If two Consumes are applied, the second will replace the first.) » | Effet persistant sur les pillz adverses (comme Poison sur la vie ; remplace, ne cumule pas) |
| **Combust X, Min Y** | « at the end of each of the following turns the opponent will lose X Life point(s) and Pillz if he/she/they have more than [Min] Life point(s)/Pillz » | Persistant vie + pillz ; « Players Combust » : les deux joueurs |
| **Mindwipe X, Min Y** | « your opponent will lose X Life Points and Pillz, minimum of Y. This effect will persist at the end of each of the following rounds. » | Identique à Combust d'après ces textes (différence éventuelle non documentée) |
| **Xantiax: −X Life, Min Y** | « Whether the character wins or loses the round, the two competing players lose X Life Points or up to a minimum of X » | Effet de fin de round, cible les deux joueurs, sans condition de victoire |
| **Corrosion X, Min Y** | « the opponent will lose 1 multiplied by the number of the round in which your card was played. (Corrosion is considered a Poison.) » | Poison de valeur = numéro du round ; partage l'emplacement du poison |
| **Corrupt X, Min Y** | « If your card wins or loses the fight, the number of Life points **you** have will be reduced by X, or up to a minimum » | Effet de fin de round sur soi, victoire ou défaite (Nega D Ld) |
| **Damage Impose / Power Impose** | « The opposing character has the same number of Damage points as your character. This number only takes into account the figure shown on your card and does not include changes related to an Ability, Bonus or Fury. » | Écriture de la stat adverse = valeur imprimée de la carte (phase des Copy/Exchange) |
| **−X Cards Damage, Min Y** (et Support:, Protection: Cards …) | « The Damage points of **both** characters are reduced by X points or up to a minimum of X » | Modificateur appliqué aux deux cartes du round (pas à toute la main, contrairement à l'hypothèse de la roadmap) |
| **Beyond** (Genesis) | « If no player is left KO at the end of the 4 rounds, a card will be randomly selected from the two players remaining decks and a 5th round will be held. […] Your card's ability cannot be stopped. » | Hors périmètre (5e round) |
| **Fatal Killshot** | « If the Attack of your card is equal or higher than the double of the opposing character's attack, the match is over and you win by KO. » | Fin de partie immédiate |
| **Sinister Symmetry** | « If your card wins the round against the card in front of it, the match is over and you win. » | Fin de partie immédiate |
| **Limitless** (Fractal) | « For all the cards in your hand, the maximums on abilities are cancelled and the minimums are replaced by 0. […] This effect does not apply to bonuses. » | Modificateur global des bornes |
| **Tie-Break** (Solomon) | Gagne toutes les égalités d'attaque (wiki *Power* : « unless Solomon is in play ») | Cas dans `resolve_combat` |
| **Counter-Attack** (Ashigaru) | « The player who has Ashigaru in their team always plays second in the fight […]. If both players have Ashigaru, the order of play is decided in the usual way. » | Ordre de jeu |
| **Rebirth** | Pas une mécanique : anciennes rééditions graphiques de cartes | Ignorer |
| Hazard, Illusion, Bypass, Overdose, Remove Ability Conditions | Pages du wiki sans définition exploitable (cartes uniques) | Reporter |

Précisions utiles glanées au passage :
- **Poison / Toxin / Dope / Consume / Heal** : ne se cumulent pas, le second **remplace** le premier (wiki *Poison*,
  *Toxin*, *Dope*, *Consume*). À vérifier dans `apply_capacity_lvl_4`.
- **Regen** : agit dès le round où la carte est jouée, victoire ou défaite (« the turn your card won or lost the round
  and […] each of the following rounds »), contrairement à Heal (victoire, rounds suivants).
- **Growth / Degrowth** : Growth = valeur × numéro du round ; Degrowth = valeur × (5 − numéro du round).
- **Brawl** : comme Support, mais compte les cartes de la main **adverse** du clan de la carte adverse.
- **Equalizer** : valeur × étoiles de la carte adverse.
- **Versus (Clan)** : s'active si la main adverse contient au moins une carte du clan, **même si la carte en face n'en
  est pas** (wiki *Versus*). Le moteur teste le clan de la carte adverse jouée (`versus:` dans
  `check_capacity_condition`) — ❌ à corriger.
- **Cancel Opp. Attack Modif.** : « the Attack gained by your opponent through Pillz does not constitute a
  modification ».

## 5. Ce que les textes ne tranchent pas — à régler par rejeu de combats réels

Par ordre d'impact :
1. Recover : pillz gratuite comptée ou non (3.5).
2. Cancel Life Modif. : pose du poison empêchée, ou tic du round sauté (3.3).
3. Combust contre Mindwipe : différence réelle.

Tranchés par l'utilisateur le 2026-09-21 (connaissance du jeu, sans source écrite) : cycles de Stops et de Protections
(3.2, les Stops gagnent), Leader bénéficiant de son propre Team (3.7, oui), deux exemplaires du même Leader
s'annulent (3.7, oui), Tune Out ignore la fury (§ 4).

Chaque combat rejoué se transcrit dans `data/test/` (voir ROADMAP § 2.B.2) ; le journal des effets (D2) rendra la
localisation des écarts immédiate.

## 6. Glossaire officiel lu en session connectée (2026-09-16, après-midi)

Les 35 entrées de `urban-rivals.com/game/rules/` ont été lues connecté (texte intégral : `docs/REGLES-glossaire-officiel.md`).
Verdicts sur les points encore ouverts ou déjà codés :

| Entrée | Règle officielle | Moteur (après les corrections du matin) | Verdict |
|---|---|---|---|
| 53 Récup | « arrondie à l'unité inférieure, **avec un minimum de 1** » | pas de minimum | ❌ → **corrigé** |
| 51 Toxine / Régén, 52 Consume / Dope | « agissent **immédiatement à la fin du round** dans lequel ils ont été joués » (Drak au round 1 : vies aux rounds 1, 2, 3 et 4) | n'agissent qu'aux rounds suivants | ❌ → **corrigé** (Repair reste aux rounds suivants, par symétrie avec Heal : hypothèse) |
| 66 Par Pillz / Vie restante | pillz/vies « **avant de mettre des pillz** sur ton perso (sans compter la Pillz gratuite) » — Lady Ametia Cr : 13 de puissance au round 1 | `nb_pillz_left` lit les pillz **après** la mise | ❌ → **corrigé** (vie : inchangée pendant la mise, OK) |
| 56 Annule (Vie / Pillz) | « n'annule un effet permanent (Poison, Soin, Toxine, Régén) que **pendant le round où il est joué. L'effet reprendra lors du round suivant** » ; idem Pillz face à Dope / Consume | la correction du matin **retire** le poison/heal/… de la carte adverse | ⚠️ → **corrigé** : le tic du round est sauté (y compris le tic immédiat d'une toxine posée ce round), l'effet subsiste |
| 56 Annule (Dégâts) | « n'annule pas la Fury » | fury ajoutée après les modificateurs, jamais annulée | ✅ |
| 58 Stop | « la condition Stop ne s'active pas contre des cartes Annul » | « stop » consommé à la phase des Stops uniquement | ✅ |
| 55 Protection | Protection: Bonus/Pouvoir protège des Stops « mais pas d'une carte Annul » ; « peut également annuler les effets négatifs d'un Leader » | Protection: X retire les modifs adverses ciblant ma carte, y compris `leader_fight` adverse | ✅ |
| 59 Copie, 172 Impose | valeurs **de base** ; Copie Bonus « s'il est actif » | ✅ | ✅ |
| 60 Echange | échange des valeurs de base « même si la carte en face a une Protection appropriée » ; annulé par un Annul approprié ; Echange face à Copie/Echange du même type → seul l'Echange agit | Exchange est méta (non touché par Protection) ; Cancel : à vérifier ; Exchange vs Copy : non géré | ➖ à vérifier |
| 63 Support / Brawl, 64 Croissance, 65 Equalizer, 67 Par Puissance/Dégâts adv. (valeurs de base) | ✅ conformes | | ✅ |
| 68 Killshot, 173 Versus (main adverse), 174 Symétrie, 175 Infiltration (carte seule, clans spécifiques) | ✅ conformes aux corrections du matin | | ✅ |
| 50 Poison / Soin | le second remplace le premier ; Poison et Soin coexistent | ✅ | ✅ |
| 61 Courage / Riposte, 62 Confiance / Revanche | ✅ | | ✅ |
| 70 Jour / Nuit | cycle de 4 h dans le jeu | non modélisé (Day toujours vrai) | choix utilisateur |

Non tranché par le glossaire : Mindwipe vs Combust, Limitless. (Cycles de Stops/Protections, Leader et son Team,
Tune Out et fury : tranchés par l'utilisateur, voir § 5.)

**Historique de combats** : `player/history.php` ne donne que le score final de chaque combat (ex. « 12-3 »), sans détail
de rounds ni rapport. Le jeu lui-même est un client Unity WebGL (`/game/play/`) ; les données de round transitent
entre ce client et le serveur — piste pour B2 : jouer un combat dans le panneau navigateur et capturer les échanges
réseau du client.

## Annexe A — identifiants du glossaire officiel (`/game/rules/?question=N`, connexion requise)

41 Fury · 42 Bonus · 43 Ability · 44 Attack · 47 Life · 48 Pillz · 49 Pillz/Life per Damage · 50 Poison/Care ·
51 Toxin/Regen · 52 Consume/Dope · 53 Recover · 54 Stop Ability/Bonus · 55 Protection · 56 Cancel · 58 Stop ·
59 Copy · 60 Exchange · 61 Courage/Reprisal · 62 Trust/Revenge · 63 Support/Brawl · 64 Growth/Degrowth ·
65 Equalizer · 66 Per Pillz/Life Left · 67 Per Opp. Power/Damage · 68 Killshot · 69 Backlash · 70 Day/Night ·
172 Impose · 173 Versus · 174 Symmetry/Asymmetry · 175 Infiltration · 76 Basics · 77 The classic game system ·
196 How to play · 197 Special symbols and bonus modes.

Le contenu est servi par `POST /ajaxcontent/faq/blockcontent.php` (`id_category=10`, `id_question=N`) avec le cookie de
session ; une fois connecté, ces 35 textes officiels sont récupérables en quelques minutes et devraient être
confrontés à ce document (en particulier 54 Stop Ability/Bonus, 53 Recover, 175 Infiltration, 41 Fury).

## Annexe B — pages du wiki consultées

Ability, Bonus, Attack, Power, Damage, Pillz, Fury, Life, KO, Stop, Stop Opp. Ability, Stop Opp Bonus, Stop All,
Protection, Protection: Ability, Protection: Bonus, Cancel Opp. Modif., Cancel Opp. Attack Modif., Cancel Opp. Life
Modif., Copy, Copy: Opp. Bonus, Copy: Opp. Power, Power = Opp. Power, Reanimate, Reanimate: +X Life, Recover X Pillz
Out Of X, Victory Or Defeat: Recover X Pillz Out Of X, Infiltrated, Oculus, Team, Leader, Bet Under X Pillz: +Y Life,
Bet Over X Pillz: Copy Opp. Ability, Zenith, Killshot, Fatal Killshot, Poison, Heal, Regen, Toxin, Dope, Consume,
Combust, Players Combust, Mindwipe, Xantiax, Corrosion, Corrupt, Growth, Degrowth, Support, Brawl, Equalizer, Damage
Exchange, Courage, Reprisal, Revenge, Confidence, Symmetry, Asymmetry, Defeat, Victory Or Defeat, Backlash, Versus,
Day/Night, Unison, Disunion, After (Clan X), After (Clan X): −X Opp Power, Tolvack, Tune Out, Cosmohnuts, Perfect,
Damage Impose, Power Impose, Support: −X Cards Damage, Beyond, Sinister Symmetry, Limitless, Solomon, Ashigaru,
Vortex, Oblivion, Damage reducer, Pussycats, Terminology Slang and Abbreviation, Rules.
