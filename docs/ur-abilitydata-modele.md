# Modèle de règles `abilityData` du client Urban Rivals

Observé le 2026-09-16 dans les réponses `battles.status` de `POST /api/private/v2/` (client web, session connectée).
Chaque pouvoir/bonus d'une carte en combat est décrit par un objet **structuré** — c'est la représentation interne des
règles du jeu, bien plus fiable que le texte. Champs vus :

| Champ | Valeurs vues | Sens probable |
|---|---|---|
| `value`, `valueMin`, `valueMax`, `valueCondition` | entiers | valeur, minimum, maximum, seuil (Bet, etc.) |
| `positionRequirement` | `both` | courage / reprisal (`first` / `second` attendus) |
| `previousRoundRequirement` | `any` | confidence / revenge (`win` / `lose` attendus) |
| `currentRoundRequirement` | `any`, `lose` | victoire / défaite / les deux (« Victory or Defeat ») |
| `indexRequirement` | `any`, `asymmetry` | symétrie / asymétrie |
| `clanRequirement`, `oppClanRequirement`, `previousClanRequirement` | `""` | Unison ?, Versus, After |
| `betPillzLink` | `no` | Bet (`over` / `under` attendus) |
| `sideAffected` | `player`, `opponent` | cible |
| `attributeAffected` | `pwr&dmg`, `dmg`, `pillz`, `none` | stat touchée (`pwr`, `atk`, `life` attendus) |
| `attributeAction` | `increase`, `copy`, `none` | sens de l'effet (`decrease`, `exchange` attendus) |
| `specialAction` | `none`, `copy_ability`, `stop_ability`, `recover_pillz` | mécaniques spéciales |
| `isSupport`, `isAntiSupport` (Brawl), `isOverdrive`, `isDivide`, `isLifeLinked`, `isPillzLinked`, `isLostLifeLinked`, `isLostPillzLinked`, `isOppStarsLinked` (Equalizer), `isClanmatesCountLinked`, `isAntiClanmatesCountLinked` | booléens | multiplicateurs |
| `isPermanent`, `isImmediatePermanent` | booléens | effet persistant (Poison/Heal) ; persistant à effet immédiat (Toxin/Regen/Dope/Consume) |
| `isInverted` | booléen | ? |

## Exemples capturés (combat 1181426)

| id | description | abilityData notable |
|---|---|---|
| 38 | Dégâts +2 (bonus La Junta) | `dmg` / `increase` / value 2 |
| 329, 3719 | Support : Dégâts +1 | `isSupport: true` |
| 729 | Défaite : Récup. 2 Pillz Sur 3 | `currentRoundRequirement: lose`, `specialAction: recover_pillz`, value 2, valueMin 3 ; longDescription : « au début du tour suivant […] 2 / 3 Pillz misées […], arrondie à l'unité inférieure, **minimum 1** » |
| 2918 | Copie : Pouvoir Adv. (bonus Oblivion) | `specialAction: copy_ability` ; « Les pouvoirs des Leader et de Genesis ne peuvent être copiés » |
| 2921 | Impose Dégâts | `sideAffected: opponent`, `attributeAffected: dmg`, `attributeAction: copy` |
| 2923 | Stop Pouvoir Adv. | `specialAction: stop_ability` |
| 3015 | Puis. Et Dégâts +2 | `pwr&dmg` / `increase` |
| 3311 | Défaite : +1 Pillz | `currentRoundRequirement: lose`, `pillz` / `increase` |
| 3355 | Asymétrie : Copie : Pouvoir Adv. | `indexRequirement: asymmetry`, `specialAction: copy_ability` |

## Autres champs de `battles.status` utiles

- `round` (0-based), `turnPlayerId` (joueur qui doit jouer : au début du round = celui qui joue en premier), `status`
  (`playing` / `done`), `battleRuleId`.
- Par joueur : `life`, `pillz`, `baseLife`, `basePillz`, `postRoundAbilities` (effets de fin de round appliqués :
  `{playerId, attributeAffected, attributeAction, isPermanent, quantity}`), `preRoundAbilities`.
- Par carte : `id` (= id iclintz), `level`, `index`, `roundPlayed` (-1 = pas jouée), `pillzUsed` (**gratuite comprise**),
  `isFury`, `roundWon`, `roundPower` / `roundDamage` / `roundAttack` : **valeurs finales** dans l'état de résolution
  (les deux cartes jouées, avant le passage au round suivant) ; ensuite `roundAttack` repasse à -1 et
  `roundPower`/`roundDamage` reviennent à la valeur de base (+ fury).
- L'état `done` ne reflète pas la dernière perte de vie (KO).

Piste : un scraping systématique de `abilityData` pour les 1 396 descriptions donnerait un parseur exact.
