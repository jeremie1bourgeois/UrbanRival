# IA — plan de construction (document vivant)

Objectif : une IA qui gagne un maximum de parties d'Urban Rivals, capable de faire face à n'importe quelle situation
que le moteur sait jouer. Le projet est aussi un projet d'apprentissage : **chaque étape doit être comprise avant de
passer à la suivante**, même si cela ralentit le projet. Cette exigence ne doit jamais brider la force de l'IA : la
méthode choisie est celle qui donne l'IA la plus forte, et on prend le temps de la comprendre.

Ce document est fait pour être relu à chaque doute sur la manière de faire, et pour évoluer : chaque étape porte un
statut (⬜ à faire · 🟨 en cours · ✅ fait), un critère de fin, et une rubrique « ce que tu dois savoir expliquer ».
Les décisions, mesures et questions ouvertes sont tenues à jour en fin de document (§ 8 à 10). Les scripts de
démonstration cités ont été joués le 2026-09-18 ; les chiffres sont ceux de cette date.

---

## 1. Analyse du jeu : ce qui dicte l'approche

Avant de choisir un outil, quatre propriétés du jeu, et leurs conséquences.

### 1.1 Un jeu à somme nulle, court, à petit espace d'actions
Deux joueurs, 4 rounds, une carte par round. Une action = (carte parmi ≤ 4, pillz misées de 0 à ce qu'il reste,
fury ou non) : au plus ~100 actions par coup. La difficulté n'est pas la taille de l'arbre.

### 1.2 Une information presque parfaite, sauf un point
Tout est public — les deux mains, les vies, les pillz, les effets persistants — **sauf la mise du premier joueur
pendant le round**. Un round se déroule ainsi :

1. le premier joueur **F** choisit sa carte : **publique** ;
2. F choisit sa mise (pillz + fury) : **cachée** ; le second joueur **S** choisit carte + mise en connaissant la carte
   de F, mais pas sa mise — en pratique les deux mises sont **simultanées** ;
3. tout est révélé et résolu par le moteur ; entre les rounds, l'état est entièrement public.

Le premier joueur du round 1 est tiré au sort dans le vrai jeu, puis l'ordre alterne (dans le moteur : `Game.turn`,
`True` = l'allié joue en premier, inversé à chaque round ; en cas d'égalité d'attaque et d'étoiles, celui qui a joué en
premier gagne).

### 1.3 Conséquence décisive : la stratégie optimale est mixte
Si l'IA mise toujours la même chose dans une situation donnée, l'adversaire mise une pillz de plus. Le cœur du jeu est
le **bluff sur les pillz**, et une stratégie non exploitable est nécessairement **probabiliste** : dans un état donné,
« 60 % de miser 2, 30 % de miser 4, 10 % de miser 1 ». Ceci exclut tout ce qui produit une seule action déterministe
(minimax, MCTS classique, un réseau dont on prend l'argmax).

### 1.4 Le jeu est petit pour une paire de mains : on peut le résoudre exactement
Une fois les deux mains connues, le nombre d'états (cartes restantes, vies, pillz, effets, premier joueur) est fini et
modéré. On peut calculer la **stratégie optimale exacte** (équilibre de Nash) par induction à rebours. C'est un luxe
rare (impossible au poker) et c'est notre **référence** : tout ce qu'on construira ensuite se mesurera contre elle.

Ce qui reste grand : l'espace des **2 497 cartes** et de leurs combinaisons. Le solveur exact ne généralise pas d'une
main à l'autre ; c'est pour généraliser qu'on apprendra une fonction de valeur (étape 3).

### 1.5 La force de l'IA est bornée par la fidélité du moteur
L'IA joue « les règles du moteur ». Un écart entre moteur et jeu réel est une faille que l'IA exploitera à tort.
L'oracle de combats réels (`docs/ORACLE.md`) est donc un investissement pour l'IA, pas seulement pour le moteur.
De même, une capacité non gérée par le parseur (`Capacity = None`, 10 descriptions sur 1 396) est jouée « à vide » par
l'IA.

### 1.6 Vocabulaire utilisé dans ce document
| Terme | Sens ici |
|---|---|
| **Carte** | un **(nom, niveau)** : chaque carte existe à plusieurs niveaux d'étoiles, **tous jouables**, avec puissance, dégâts et parfois ability différents à chaque niveau (`Card(name, nb_stars)`). Une main peut contenir **plusieurs exemplaires** de la même carte, de niveaux identiques ou non ; les exemplaires **comptent pour un seul** dans le décompte du bonus de clan |
| **État** | tout ce qui détermine la suite de la partie : round, premier joueur, vies, pillz, cartes jouées / restantes, effets persistants, et ce que le moteur lit du round précédent (voir § 3.1) |
| **Action** | (indice de carte, `pillz_fight` = 1 + mise, fury) |
| **F / S** | premier / second joueur du round en cours |
| **V(état)** | probabilité de gagner la partie depuis cet état, si les deux joueurs jouent parfaitement (nul = 0,5) ; toujours exprimée pour l'allié, puis convertie (`1 − V`) quand il faut le point de vue de l'ennemi |
| **Politique** | distribution de probabilité sur les actions dans un état |
| **Jeu matriciel** | tableau des gains `M[action de F][action de S]` d'un round ; **équilibre de Nash** = couple de politiques dont aucun joueur ne peut s'écarter avec profit ; **valeur du jeu** = gain garanti en jouant l'équilibre |
| **LP** (programme linéaire) | maximiser une quantité sous des contraintes toutes linéaires ; c'est ainsi qu'on calcule l'équilibre de Nash d'un jeu matriciel (§ 4.3 : maximiser la valeur `v` sous « chaque colonne rapporte au moins `v` »), avec `scipy.optimize.linprog` |
| **Induction à rebours** | calculer les valeurs du dernier round d'abord, puis remonter |
| **Mémoïsation** | table `état → V` pour ne jamais résoudre deux fois le même état |
| **Heuristique de feuille** | score approximatif d'un état qu'on ne résout pas plus loin |
| **Réseau de valeur** | fonction apprise `état → V` qui remplace l'heuristique de feuille |
| **Exploitabilité** | de combien une politique fixe peut être battue par la meilleure réponse à cette politique ; 0 pour Nash |

---

## 2. Vue d'ensemble

| Étape | Produit | Concept appris | Mesure de succès | Statut |
|---|---|---|---|---|
| 0. Infrastructure | API moteur pure, arène, mains réalistes, joueurs étalons | évaluation statistique, variance, symétrie | l'arène distingue deux joueurs avec un intervalle de confiance | ⬜ |
| 1. Nash à un round | IA « Nash-1 » (profondeur 1 + heuristique) | jeu matriciel, minimax, stratégie mixte, programme linéaire | bat nettement les étalons ; stratégies pures au round 4, mixtes avant | ⬜ |
| 2. Solveur exact | IA « Nash-exact » (référence), valeur d'un match-up, exploitabilité | induction à rebours, programmation dynamique, fonction de valeur | reproduit le jouet ; résout rounds 4 et 3 ; coût mesuré et réduit | ⬜ |
| 3. Fonction de valeur apprise | IA « Nash-1/2 + réseau » jouable sur toute main | encodage, généralisation, distillation, bootstrapping | erreur contre V exacte sur des mains jamais vues ; arène contre Nash-exact et étalons | ⬜ |
| 4. Exploitation et usages | modèle d'adversaire, meilleure réponse, évaluation de decks, intégration | meilleure réponse vs Nash, modélisation d'adversaire | gain contre les joueurs modélisés sans exploitabilité excessive | ⬜ |

Chaque étape reprend la précédente en changeant **une seule chose** :
étape 2 = étape 1 dont l'heuristique est remplacée par un appel récursif ;
étape 3 = étape 1 dont l'heuristique est remplacée par un réseau entraîné sur les valeurs de l'étape 2.

---

## 3. Étape 0 — Infrastructure ⬜

Sans elle, on avance à l'aveugle : on ne saurait pas si une modification est un progrès ou du bruit.

### 3.1 API moteur pure
Le moteur (`process_round`) est déjà une fonction ; il manque une façade stable pour l'IA :

- `legal_actions(state, side) → [(card_index, pillz_fight, fury)]` — cartes non jouées × mises 0..pillz × fury si
  `mise + 3 ≤ pillz`.
- `step(state, action_ally, action_enemy) → state'` — sans effet de bord sur `state` (copie).
- `terminal(state) → 1 | 0,5 | 0 | None` du point de vue de l'allié : KO (vie ≤ 0) ou fin des 4 rounds (plus de vie
  gagne, égalité = nul).
- `first_player(state) → "ally" | "enemy"` — `Game.turn`. Le premier joueur du round 1 doit pouvoir être l'un ou
  l'autre (aujourd'hui `create_game` met toujours l'allié) : l'IA doit savoir jouer **les deux rôles**.
- `key(state)` — clé hashable pour la mémoïsation. Elle doit contenir **tout ce que le moteur lit** :
  `nb_turn`, `turn`, vies, pillz, drapeaux `played` des 8 cartes, effets persistants des deux joueurs, et du round
  précédent : les deux indices de cartes jouées et le vainqueur (`history[-1]`, lu par Revenge / Confidence / After).
  Oublier un élément = deux états différents confondus = valeurs fausses.

Le tout doit rester **indépendant des valeurs de départ** (vies, pillz) : l'IA doit faire face à n'importe quelle
situation que le moteur sait jouer ; aucune constante « 12 » dans le code de l'IA.

**Doublons et bonus de clan.** Une main peut contenir plusieurs exemplaires d'une même carte (même niveau ou non) ;
ils comptent **pour un seul** dans le « ≥ 2 cartes du clan » qui active le bonus (règle confirmée par l'utilisateur,
cohérente avec le wiki : « This doesn't apply to the same Characters »). Le moteur compte les **noms distincts** par
clan (`is_clan_bonus_active`, test « deux exemplaires seuls de leur clan → bonus inactif »). Le pouvoir `Support`, lui,
compte **chaque exemplaire** (combat réel 1347602, `docs/REGLES.md` § 3.6). Cas voisins non tranchés : Oculus
infiltré avec doublons, Unison (§ 9). Deux exemplaires du même Leader s'annulent (confirmé par l'utilisateur le 2026-09-21).

### 3.2 Générateur de mains
Des mains de 4 cartes au hasard parmi 2 497 n'activent presque jamais un bonus de clan (≥ 2 cartes du clan) : elles
ne ressemblent pas au jeu. Le générateur doit produire des mains **réalistes et variées** : mono-clan, 2 + 2, 3 + 1,
avec ou sans Leader, **tous les niveaux de chaque carte** (une carte de niveau 2 et la même au niveau 5 sont deux
objets de jeu différents : stats, ability, étoiles pour le départage des égalités), et **des doublons** (même carte
deux fois, de niveaux identiques ou non — certains modes le permettent, et le bonus de clan ne les compte qu'une
fois), plus une part de mains uniformément aléatoires pour la couverture. Paramétrable par graine pour la
reproductibilité. Le tirage 4 parmi 8 n'est pas modélisé (décision § 8).

### 3.3 Arène d'évaluation
`arena(joueur_A, joueur_B, N, graine)` : N parties sur des mains tirées par le générateur, **chaque paire de mains
jouée deux fois en échangeant les côtés** et le premier joueur, score = 1 victoire / 0,5 nul / 0 défaite.

Sortie : score moyen p̂ et intervalle de confiance à 95 % ≈ p̂ ± 1,96·√(p̂(1 − p̂)/N). Ordres de grandeur : N = 400
parties → ± 5 points ; N = 2 500 → ± 2 points. **Deux joueurs ne sont départagés que si les intervalles ne se
recouvrent pas.** Un Elo interne (optionnel) résume un tournoi entre plusieurs versions.

Les joueurs sont des fonctions pures `politique(state, side, rng) → action` ; les joueurs probabilistes reçoivent le
générateur aléatoire en paramètre (reproductibilité).

### 3.4 Joueurs étalons
- **Aléatoire** : action uniforme parmi les légales.
- **Glouton** : une règle fixe et simple, par exemple « carte de meilleur produit puissance × dégâts, mise =
  pillz restantes / rounds restants, tout au dernier round ». Le zéro de l'échelle ; sa seule qualité est d'être
  déterministe et documenté.

### 3.5 Garde-fous du moteur
- `scripts/engine_crash_sweep.py` : aucune action légale ne doit lever d'exception (l'IA explorera *toutes* les
  actions, y compris absurdes).
- Déterminisme : `step` appliqué deux fois au même état et aux mêmes actions donne le même état.
- Mesure de vitesse de `step` (journal § 10) : elle conditionne les étapes 2 et 3.

### Critère de fin
L'arène donne, en une commande, le score aléatoire contre glouton avec son intervalle, reproductible à graine égale.

### Ce que tu dois savoir expliquer
Pourquoi on joue chaque paire de mains dans les deux sens ; pourquoi 100 parties ne suffisent pas à départager deux
joueurs proches ; pourquoi la clé d'état doit contenir le round précédent.

---

## 4. Étape 1 — Nash à un round (profondeur 1) ⬜

### 4.1 Principe
À chaque round, quel qu'il soit, l'IA :
1. énumère ses actions et celles de l'adversaire ;
2. simule chaque couple d'actions avec `step` → un état « après le round » ;
3. donne un **score** à cet état : exact au round 4 (`terminal`), heuristique avant ;
4. résout le jeu matriciel des scores → une politique mixte ; tire son action au sort dedans.

C'est une recherche à profondeur 1. Ce qui change d'un round à l'autre n'est pas *où* on calcule Nash mais *comment on
score les cases* : la faiblesse de l'étape est l'heuristique des rounds 1-3, que l'étape 2 supprime.

### 4.2 Les deux rôles
- **Je suis F** : pour chacune de mes cartes, lignes = mes mises (pillz × fury), colonnes = **toutes** les paires
  (carte, mise) de S, puisqu'il choisira sa carte après avoir vu la mienne. Une matrice par carte ; je joue la carte
  dont la matrice a la meilleure valeur, avec la politique mixte de cette matrice.
- **Je suis S** : la carte de F est connue ; lignes = mes paires (carte, mise), colonnes = les mises de F pour cette
  carte. Une seule matrice.

Dans les deux cas la matrice contient des scores **pour moi** (si je suis l'ennemi, `1 − V`).

### 4.3 Résoudre un jeu matriciel : le programme linéaire
Pour une matrice `M` (lignes = moi, je maximise), on cherche les probabilités `p` et la valeur `v` :

```
maximiser v
sous  Σ_i p_i · M[i, j] ≥ v   pour chaque colonne j      (quoi que fasse l'adversaire, je garantis v)
      Σ_i p_i = 1,  p_i ≥ 0
```

```python
import numpy as np
from scipy.optimize import linprog

def solve_zero_sum(M):
    """Politique mixte des lignes (maximise) et valeur du jeu."""
    n, m = M.shape
    c = np.zeros(n + 1); c[-1] = -1                      # linprog minimise : on minimise -v
    A_ub = np.hstack([-M.T, np.ones((m, 1))])            # -Σ_i p_i M[i,j] + v <= 0
    b_ub = np.zeros(m)
    A_eq = np.append(np.ones(n), 0).reshape(1, -1)       # Σ p_i = 1
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1], bounds=[(0, 1)] * n + [(None, None)])
    return res.x[:n], res.x[-1]
```

La politique de l'adversaire s'obtient avec `solve_zero_sum(-M.T)`. Vérification d'inexploitabilité : `p @ M` doit
valoir au moins `v` sur chaque colonne.

### 4.4 Exemple de référence (à reproduire)
Round 3, deux cartes de puissance 8, 3 pillz à miser chacun (mises 1-4), égalité à S. Heuristique : +2 si je gagne le
round, +1 par pillz économisée par rapport à l'adversaire.

|         | S=1 | S=2 | S=3 | S=4 |
|---------|-----|-----|-----|-----|
| **F=1** | −2  | −1  |  0  |  1  |
| **F=2** |  1  | −2  | −1  |  0  |
| **F=3** |  0  |  1  | −2  | −1  |
| **F=4** | −1  |  0  |  1  | −2  |

Aucune ligne ne domine : c'est un pierre-feuille-ciseaux. Solution : 25 % sur chaque mise pour les deux joueurs,
valeur −0,5 pour F, et `p @ M = [−0,5, −0,5, −0,5, −0,5]` — S ne peut rien faire de mieux.

### 4.5 Heuristique de feuille (provisoire)
Un score dans [0, 1] à partir de l'état après le round, par exemple
`0,5 + a · (vie_moi − vie_adv) / vie_max + b · (pillz_moi − pillz_adv) / pillz_max`, borné à [0, 1], avec 1 / 0 si
la partie est finie. `a` et `b` sont arbitraires : c'est le point faible assumé de l'étape, pas un sujet à optimiser
(l'étape 2 le rend caduc). Question ouverte § 9.

### 4.6 Points d'attention
- Les valeurs de `M` doivent être dans une échelle cohérente (des probabilités : [0, 1]).
- Le LP renvoie parfois `−0.0` ou `1e-12` : arrondir / borner les probabilités avant de tirer au sort.
- Au round 4, la politique est le plus souvent **pure** (tout miser, ou exactement ce qu'il faut) : c'est un bon
  test de cohérence. Le bluff apparaît aux rounds 1-3 parce que les pillz gardées y ont une valeur.
- Une action à probabilité nulle ne doit jamais être jouée ; une action à probabilité 1 l'est toujours.

### Critère de fin
Nash-1 bat l'aléatoire et le glouton avec des intervalles disjoints ; l'exemple § 4.4 est un test unitaire ; sur des
états de round 4 réels, la politique est pure dans la grande majorité des cas.

### Ce que tu dois savoir expliquer
Pourquoi une politique déterministe est exploitable ; ce que garantit la valeur du jeu ; pourquoi la matrice de F
a plus de colonnes que celle de S ; pourquoi l'heuristique est le maillon faible.

---

## 5. Étape 2 — Solveur exact par induction à rebours ⬜

### 5.1 L'idée unique
Remplacer l'heuristique de feuille par la vraie valeur :

> V(état) = valeur du jeu matriciel de son round, dont chaque case vaut V(état suivant).

Récursion jusqu'au round 4, où `terminal` donne 1 / 0,5 / 0. Les valeurs sont exactes au round 4, donc au round 3,
donc au round 2, donc au round 1 : aucune heuristique nulle part, et **la politique de chaque round est la politique
optimale de la partie entière** — l'IA « sait » ce que vaut une pillz gardée parce qu'elle a calculé ce qu'elle en
fera ensuite.

```
V(état) :
    si terminal(état) : renvoyer 1 / 0,5 / 0
    si état dans la mémo : renvoyer la valeur mémorisée
    F = premier joueur de l'état
    pour chaque carte de F :
        M[mise de F][(carte, mise) de S] = V(step(état, …)), exprimée pour F
        valeur_carte = solve_zero_sum(M)
    V = max des valeur_carte, reconvertie pour l'allié ; mémoriser ; renvoyer
```

`V(état initial)` est la **valeur du match-up** (« cette main contre celle-là = 62 % »).

### 5.2 Exemple de référence : le jeu jouet
2 rounds, cartes de puissance 8, 2 pillz à miser sur l'ensemble des deux rounds, égalité à F, victoire = gagner les
deux rounds, un partout = nul. Résultats attendus (script de démonstration du 2026-09-18) :

- matrice du round 1 : cases = V des états du round 2, toutes exactes (1,000 ou 0,500), calculées en résolvant le
  round 2 ;
- politique de F au round 1 : (1/3, 1/3, 1/3) — **mixte** ; toutes les politiques du round 2 : **pures** ;
- valeur du match-up : 0,667 pour F (jouer en premier gagne les égalités) ;
- 23 états distincts résolus grâce à la mémo.

Ce jouet est le test unitaire de la récursion : il doit être reproduit avant de brancher le vrai moteur.

### 5.3 Coût sur le vrai moteur — mesures du 2026-09-18
Prototype branché sur `process_round` (deepcopy + `ProcessRoundInput`), mains réalistes aléatoires, 12 pillz :

| Résolution exacte depuis… | Temps | Appels à `step` | États distincts |
|---|---|---|---|
| round 4 | 0,2 – 0,5 s | 200 – 450 | 1 |
| round 3 (11/11 pillz) | 45 – 75 s | 44 000 – 78 000 | ~650 états de round 4 |
| round 2 (11/12 pillz) | ~4 h extrapolées (3 lignes sur 69 en 594 s, 552 000 `step`, 4 258 états de round 4) | — | — |
| round 1 (partie entière) | ~3 jours extrapolés (~250 millions de `step`) | — | — |

Le moteur fait ~1 000 `step`/s (~1 ms : deepcopy + `process_round`) et **99 % du temps est dans `step`** ; les LP
sont négligeables tant que le moteur est lent.

Conclusion : à ce coût, la résolution complète d'une partie est un outil de laboratoire (référence, étiquettes) ;
elle ne devient un outil de jeu que si les réductions ci-dessous la ramènent dans le temps qu'on accepte par coup
(question § 9). Le solveur exact reste l'IA la plus forte possible : tout ce qui suit n'est qu'une façon de s'en
approcher là où il est trop lent.

### 5.4 Réductions de coût, dans l'ordre
1. **Vitesse du moteur** (décision § 8 : à optimiser, chiffres cibles) : à 10 µs par `step`, la partie entière tombe
   à ~40 min ; à 1 µs, ~4 min. Moyens : état compact (entiers, tableaux), pas de deepcopy ni de re-parsing des
   capacités, code compilé (numba / Rust / C++). Le moteur Python actuel reste l'**oracle de non-régression** du
   moteur rapide (mêmes fixtures, mêmes combats réels).
2. **Le LP devient alors le goulot** (~1 million de matrices par partie × 1-3 ms). Parades : tester d'abord un
   **équilibre pur** (point-selle : max des minima de lignes = min des maxima de colonnes, en O(n·m)), très fréquent
   au round 4 ; supprimer les lignes / colonnes **dominées** ; résoudre en lot sur GPU (regret matching matriciel)
   plutôt qu'avec scipy.
3. **Abstractions d'état sans perte** : les vies au-delà des dégâts maximum encore possibles sont équivalentes ; les
   pillz au-delà de ce qui peut servir aussi.
4. **Troncature** : résoudre exactement jusqu'à une profondeur (2 rounds) et scorer les feuilles — avec le réseau de
   l'étape 3, c'est l'IA de jeu.

### 5.5 Ce que le solveur permet, au-delà de jouer
- **Référence** : sur un échantillon de mains, comparer toute IA à Nash-exact en arène.
- **Exploitabilité** d'une politique π : fixer π pour un camp et calculer la **meilleure réponse** de l'autre (même
  récursion, avec un `max` à la place du LP) ; la différence avec la valeur du jeu mesure de combien π est battable.
  C'est la mesure la plus honnête d'un joueur : 0 pour Nash.
- **Étiquettes** pour l'étape 3 : `(état, V, politique)`.
- **Valeur d'un match-up** : base de l'évaluation de decks (étape 4).

### Critère de fin
Le jouet § 5.2 est reproduit ; sur le vrai moteur, rounds 4 et 3 sont résolus et testés (cohérence : V dans [0, 1],
symétrie en échangeant les camps) ; le coût est journalisé (§ 10) avant et après chaque réduction de § 5.4 ;
Nash-exact bat Nash-1 en arène sur des états de round 3.

### Ce que tu dois savoir expliquer
Pourquoi les valeurs sont exactes sans heuristique ; d'où vient la valeur des pillz ; ce que la mémo évite ; pourquoi
le coût explose au round 1 et quels leviers le réduisent ; ce qu'est l'exploitabilité.

---

## 6. Étape 3 — Fonction de valeur apprise (réseau + recherche) ⬜

### 6.1 Le problème et l'idée
Le solveur calcule mais n'apprend rien : changer une carte remet tout à zéro. On veut une fonction `f(état) ≈ V(état)`
instantanée, valable pour des cartes jamais vues. **On l'apprend par régression à partir d'exemples résolus** : le
solveur est le professeur, le réseau l'élève. Puis on rejoue l'étape 1 avec le réseau à la place de l'heuristique :
matrice exacte du round en cours (ou des deux prochains rounds), réseau aux feuilles. C'est la recette AlphaZero
(recherche + évaluation apprise), avec un professeur exact au lieu de parties bruitées.

### 6.2 Encoder un état en nombres
- **Une carte** : puissance, dégâts, étoiles, clan (one-hot, 36), et ses deux capacités (ability, bonus) sous la
  forme **structurée** du parseur (`Capacity` : `target`, `types`, `value`, `borne`, `how`, `effect_conditions`,
  `lvl_priority`) → catégories en one-hot, nombres tels quels, drapeau « capacité gérée ». Aucun texte, et **jamais le
  nom** : le réseau voit la carte **au niveau joué** (ses stats et son ability à ce niveau), ce qui traite d'un coup
  les niveaux multiples et les doublons — deux exemplaires sont deux vecteurs, identiques si même niveau.
- **Une main** : 4 cartes + drapeau `played` chacune + bonus de clan actif ou non (calculé sur les **noms distincts**,
  règle § 3.1). Une main est un **ensemble** : soit on trie les cartes selon un ordre canonique, soit on agrège de
  façon invariante à l'ordre.
- **L'état** : les deux mains, vies, pillz, round, premier joueur, effets persistants, informations du round
  précédent (les mêmes que dans `key`). Toujours du point de vue « moi / adversaire », pour qu'un seul réseau serve
  aux deux camps.

### 6.3 Données
- **Quels états ?** Ceux que l'IA rencontre : états visités en **self-play** (parties jouées par l'IA courante contre
  elle-même et contre les étalons), avec une part d'états aléatoires pour la couverture. Mains du générateur § 3.2.
- **Quelles étiquettes ?** V exacte et politique Nash. D'abord sur les **rounds 4 et 3** (résolution exacte peu
  coûteuse, § 5.3), puis rounds 2 et 1 résolus **tronqués** avec le réseau courant aux feuilles : les cibles
  s'approfondissent à mesure que le réseau s'améliore (*bootstrapping* avec cibles exactes à l'horizon).
- **Découpage** : les mains de test ne doivent **jamais** apparaître à l'entraînement ; test encore plus exigeant :
  des **cartes** entières tenues à l'écart.

### 6.4 Modèle et entraînement
- Sortie **valeur** : un nombre dans [0, 1] (sigmoïde ; perte MSE ou entropie croisée binaire).
- Sortie **politique** (optionnelle mais utile) : logits sur une grille d'actions fixe (4 cartes × 13 mises × fury),
  masquée par les actions légales, perte = entropie croisée contre la politique Nash. Sert à élaguer le solveur
  (mises à probabilité ~0) et à jouer sans recherche.
- Architecture : commencer petit (MLP sur l'encodage concaténé) ; attention entre cartes seulement si la mesure le
  justifie. PyTorch, GPU (disponibles : décision § 8).
- Mesures : erreur moyenne |f − V| sur les mains de test ; **arène contre Nash-exact** sur des états de round 3-4 ;
  arène contre Nash-1 et les étalons.

### 6.5 Jouer avec le réseau
Profondeur 1 (~8 500 `step` au round 1 : instantané) ou 2 (~12 millions de `step` et autant d'appels réseau, en lot
GPU : minutes avec un moteur à 10 µs — mode « conseiller »). La matrice exacte du round en cours **corrige** une partie
des erreurs du réseau aux feuilles ; plus on résout de rounds exactement, moins elles pèsent (curseur
profondeur / vitesse).

### 6.6 La boucle d'amélioration (expert iteration)
réseau vₙ → élagage + feuilles pour le solveur → étiquettes plus profondes, plus proches des vraies parties → réseau
vₙ₊₁. **Une version n'est conservée que si elle bat la précédente en arène** (intervalles disjoints).

### 6.7 Exemple de référence
Jouet à cartes variables (puissance 2-8, dégâts 1-5, 2 rounds, KO possible) : 2 500 match-ups résolus exactement en
25 s (40 278 états), MLP (64, 64) entraîné sur 2 000, testé sur 500 **jamais vus** : erreur moyenne 0,056 (contre
0,363 en répondant toujours 0,5). Le réseau se trompe sur certains cas (0,913 prédit pour 0,750 exact) : c'est
pourquoi on joue avec recherche + réseau, pas réseau seul.

### Critère de fin
Erreur sur mains jamais vues journalisée et décroissante avec la quantité de données ; l'IA « Nash-1 + réseau » bat
Nash-1 (heuristique) en arène, et n'est pas distinguable de Nash-exact sur les états de round 3 ; elle joue sur
n'importe quelle main dans le temps par coup fixé par l'usage (§ 9).

### Ce que tu dois savoir expliquer
Pourquoi l'encodage structuré vaut mieux que le texte ; pourquoi le découpage se fait par mains et non par états ;
ce que la recherche corrige ; pourquoi on n'a pas besoin de résoudre des parties entières pour entraîner.

---

## 7. Étape 4 — Exploitation et usages ⬜

- **Nash vs meilleure réponse.** Nash garantit de ne pas perdre en espérance contre un adversaire parfait ; contre
  un adversaire réel, on gagne davantage en s'écartant de Nash pour exploiter ses biais. Outil : la meilleure réponse
  du § 5.5, contre un **modèle d'adversaire**.
- **Modèle d'adversaire** : à partir des combats réels capturés (`data/ur_battles/`), estimer la distribution des
  mises humaines selon le contexte (round, carte, vies, pillz). Exploitation **dosée** : mélange Nash / meilleure
  réponse, en surveillant l'exploitabilité de l'IA qui en résulte.
- **Évaluation de decks** : espérance de la valeur de match-up sur des adversaires typiques ; le tirage 4 parmi 8
  entre ici comme une espérance sur les tirages (décision § 8).
- **Intégration** : l'IA devient une stratégie sélectionnable dans l'interface (endpoint de choix de coup) ; un mode
  « conseiller » affiche la politique et la valeur.
- **Prudence** : faire jouer l'IA sur le serveur officiel relève des CGU du jeu (les bots y sont en général
  interdits) ; l'usage conseiller est le plus sûr.

---

## 8. Journal des décisions

| Date | Décision | Pourquoi |
|---|---|---|
| 2026-09-18 | **Pas d'apprentissage par renforcement par essais-erreurs** (PPO / DQN / Gymnasium, comme l'envisageait `ROADMAP.md` § E) : la voie est Nash exact + fonction de valeur apprise sur des cibles exactes. Aucune expérience « pour montrer que ça ne marche pas ». | Le jeu est résoluble exactement par round ; un signal exact (V) vaut mieux qu'un bit par partie ; la référence Nash rend chaque progrès mesurable. |
| 2026-09-18 | **Aucun mode de jeu ciblé** : l'IA doit faire face à toute situation que le moteur sait jouer. | Conséquence : l'état est paramétrique (vies, pillz de départ sont des valeurs, pas des constantes) ; les modes à règles différentes relèvent du moteur, pas de l'IA. |
| 2026-09-18 | **Mains données** (4 cartes par joueur, comme le moteur) ; le tirage 4 parmi 8 sera traité plus tard (étape 4, espérance sur les tirages). | Séparer le jeu de la main du choix de la main. |
| 2026-09-18 | **La vitesse du moteur n'est pas un sujet bloquant** : elle sera optimisée (cibles § 5.4) ; GPU disponibles pour l'étape 3. | Les étapes 0-1 tournent avec le moteur actuel ; les mesures § 5.3 fixent les objectifs de l'optimisation. |
| 2026-09-18 | L'ancienne IA (adversaire heuristique, `ia_old/`) n'est pas reprise : l'étape 0 repart de zéro. | Repartir sur une base pensée pour la recherche (pureté, clé d'état, arène). |
| 2026-09-18 | **Le budget de temps par coup n'est pas fixé maintenant.** Ordre : finir le moteur Python → le porter en Rust et l'optimiser à fond → résoudre une partie entière par Nash exact et mesurer le temps → trancher le budget sur ce chiffre réel. | Le budget décide où s'arrête l'exact et où commence l'approximation (§ 5.3, § 6) ; le fixer avant de connaître le coût réel du solveur, c'est risquer de brider l'IA pour rien. |
| 2026-09-18 | **Tous les niveaux de chaque carte sont jouables ; les doublons sont possibles** (même carte plusieurs fois, niveaux identiques ou non, selon le mode) **et comptent pour un seul dans le bonus de clan**. | Règle du jeu confirmée par l'utilisateur. Conséquences : identité de carte = (nom, niveau) ; le générateur de mains produit niveaux et doublons ; le réseau encode la carte au niveau joué, sans le nom ; le moteur compte les noms distincts (`is_clan_bonus_active`, § 3.1). |

## 9. Questions ouvertes

| Question | Où elle se pose | Piste |
|---|---|---|
| Coefficients `a`, `b` de l'heuristique de feuille | étape 1 | provisoires ; caducs à l'étape 2 |
| Temps acceptable par coup (jeu en direct, conseiller, hors ligne ?) | étapes 2-3 | ce budget décide où s'arrête la résolution exacte et où commence l'approximation ; tranché après la mesure d'une partie entière sur le moteur Rust (décision § 8), jamais pour avoir une IA jouable plus tôt |
| Que faut-il exactement dans `key` ? (effets persistants, `cancelled_modifs`, conditions lisant l'historique) | étape 0 | lire `process_round` et les niveaux 1-4 ; test : deux états de clés égales donnent les mêmes résultats pour toutes les actions |
| Premier joueur du round 1 tiré au sort : à ajouter à `create_game` ? | étape 0 | oui, avec option de le fixer |
| Distribution des mains pour l'arène et l'entraînement (mono-clan, 2+2, niveaux) | étapes 0, 3 | paramètres du générateur ; mesurer la sensibilité des résultats |
| Solveur de jeux matriciels : scipy suffit-il une fois le moteur rapide ? | étape 2 | point-selle d'abord, puis regret matching en lot |
| Encodage des capacités non gérées (`Capacity = None`) | étape 3 | drapeau « non gérée » ; l'IA les joue à vide, comme le moteur |
| Invariance à l'ordre des cartes dans une main | étape 3 | tri canonique d'abord |
| Modes à règles spéciales (vies ≠ 12, bonus modifiés) | moteur | hors périmètre de l'IA tant que le moteur ne les modélise pas |
| Doublons et cas voisins : `Support` compte-t-il les exemplaires ou les noms distincts (même mécanique que le bonus de clan ?) ; un Oculus infiltré compte-t-il les exemplaires ou les noms (« carte seule ») ? Unison avec doublons ? | moteur (étape 0) | hypothèse : même règle que le bonus de clan (noms distincts) ; à confirmer en combat réel (`docs/ORACLE.md`). Deux exemplaires du même Leader s'annulent : confirmé par l'utilisateur (2026-09-21), testé |
| Mémo et doublons : deux exemplaires identiques non joués rendent des états équivalents par permutation | étape 2 | canonicaliser la clé (trier les cartes restantes) — optimisation, pas une nécessité |

## 10. Journal des mesures

| Date | Mesure | Valeur |
|---|---|---|
| 2026-09-17 | Moteur Python : deepcopy d'une partie / deepcopy + `process_round` | 0,7 ms / 1,4 ms (~700 rounds/s) |
| 2026-09-18 | Solveur exact prototype : `step`/s en résolution | ~1 000 |
| 2026-09-18 | Résolution exacte depuis le round 4 / round 3 | 0,2-0,5 s / 45-75 s (voir § 5.3) |
| 2026-09-18 | Résolution exacte depuis le round 2 (extrapolée après 3 lignes sur 69) | ~4 h |
| 2026-09-18 | Jouet 2 rounds (§ 5.2) : états distincts / valeur du match-up | 23 / 0,667 |
| 2026-09-18 | Jouet à cartes variables (§ 6.7) : erreur du réseau sur 500 match-ups jamais vus | 0,056 (référence 0,363) |
