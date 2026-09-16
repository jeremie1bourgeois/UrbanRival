# L'IA : comment elle marche, comment l'entraîner, comment la guider

Ce document s'adresse à toi, pas à un spécialiste. Aucun prérequis en apprentissage automatique : tout est
expliqué au fur et à mesure, et le vocabulaire technique n'apparaît qu'entre parenthèses, pour que tu puisses
chercher plus loin si tu veux.

**État actuel** : l'ébauche apprend pour de vrai et **bat l'adversaire heuristique — 56,2 % ± 3,4 %** sur 800
parties fraîches, là où le jeu aléatoire plafonne à 20,7 %. Mais elle a appris à battre *cet adversaire-là* plus
qu'à bien jouer en général : contre le jeu aléatoire elle ne fait que 63,9 %, quand l'heuristique en fait 81,3 %.
Le § « Où ça coince » explique ce paradoxe, qui est l'enseignement le plus utile de cette première ébauche.

---

## 1. En deux minutes

L'IA doit, à chaque round, choisir trois choses : **quelle carte** jouer, **combien de pillz** miser, et si elle
met la **fury**. C'est tout. Le reste — les pouvoirs, les bonus de clan, les poisons — est géré par le moteur du
jeu, l'IA n'a pas à les connaître.

Sa méthode de décision est volontairement simple à lire :

1. Elle liste tous les coups qu'elle a le droit de jouer (typiquement une centaine).
2. Pour chacun, elle calcule une poignée de **critères** : la puissance de la carte, les pillz que ça coûte,
   l'avance en vie, la menace que représente la main adverse… (24 critères en tout).
3. Elle donne une **note** à chaque coup : `note = poids₁ × critère₁ + poids₂ × critère₂ + …`
4. Elle **tire au sort** un coup, en favorisant fortement les mieux notés.

Les **poids** sont les seuls nombres que l'entraînement modifie. Il y en a 24. Tout l'apprentissage consiste à
chercher les 24 bonnes valeurs.

C'est un choix assumé face à un réseau de neurones : moins puissant, mais **lisible**. À la fin d'un
entraînement, on peut ouvrir le fichier et lire « l'IA a appris à éviter de dépenser ses pillz ». Un réseau de
neurones jouerait probablement mieux et ne dirait rien de ce qu'il a compris — impossible pour toi de le guider.

### Pourquoi elle tire au sort au lieu de jouer son meilleur coup

Deux raisons, dont la seconde a décidé de toute la conception.

**Parce que le jeu l'exige.** Les deux joueurs choisissent **en même temps**, sans voir le coup d'en face. Une
IA parfaitement prévisible se fait démonter : il suffit de savoir ce qu'elle va jouer. « Souvent le bon coup,
mais pas toujours le même » est la bonne réponse, et c'est un résultat classique de théorie des jeux.

**Parce que sans ça, rien n'apprend.** Mesuré sur ce projet, contre l'heuristique :

| | Taux de victoire |
|---|---|
| Formule au hasard qui joue **toujours** son coup préféré | **8,8 %** |
| Formule au hasard qui **tire au sort** | **17,9 %** |
| Jeu complètement aléatoire | 20,7 % |
| Poids tous à zéro (= tirage uniforme) | 20,9 % |

Une mauvaise formule déterministe répète la même erreur à chaque partie — par exemple vider ses 12 pillz au
round 1 — et perd donc deux fois plus souvent que le hasard. En tirant au sort, la même mauvaise formule joue
aussi bien que le hasard. L'entraînement démarre ainsi d'un niveau correct au lieu de patauger dans une zone
plate où tout se vaut, sans direction à suivre. **Ça a été le déblocage principal de ce projet** : avec le jeu
de critères initial, l'écart était encore plus brutal (1,2 % contre 18,7 %).

Détail technique : la probabilité de jouer un coup est proportionnelle à `exp(note)` (un *softmax*). Des poids
tous à zéro donnent un tirage uniforme, c'est-à-dire le jeu aléatoire ; plus les poids grandissent, plus l'IA
devient tranchée. Elle apprend donc à la fois **quoi** préférer et **à quel point** y tenir.

---

## 2. L'entraînement, expliqué simplement

La méthode s'appelle la **méthode des élites** (*cross-entropy method*). Elle tient en quatre étapes, répétées
en boucle. Un tour de boucle s'appelle une **génération**.

1. On fabrique 40 IA en tirant leurs poids au hasard, autour du meilleur réglage connu.
2. Chacune joue 80 parties contre l'adversaire d'entraînement.
3. On garde les 10 meilleures : les **élites**.
4. Le nouveau « meilleur réglage connu » devient la moyenne des élites, et on recommence.

Pas de gradient, pas de réseau de neurones, aucune bibliothèque à installer. Sur 24 poids, ça suffit largement,
et surtout chaque étape est compréhensible — donc pilotable.

### Le piège qui a été évité, et qui compte

À une génération donnée, **tous les candidats jouent exactement les mêmes parties** : mêmes decks, même hasard.

Sans cette précaution, un candidat pourrait gagner parce qu'il a tiré de meilleures cartes, et non parce qu'il
joue mieux. On sélectionnerait alors le plus chanceux à chaque génération, et l'entraînement tournerait en rond
en donnant l'illusion de progresser. C'est l'erreur classique de ce genre de code.

Conséquence à connaître pour lire les courbes : **les decks changent d'une génération à l'autre**. Le score
monte donc en dents de scie (35 % puis 28 % puis 33 %…). Ce n'est pas un bug — une génération peut simplement
être tombée sur des decks plus difficiles. Ce qui compte est la tendance sur dix générations, pas l'écart entre
deux lignes voisines.

---

## 3. Lancer un entraînement

```bash
cd UrbanPy/Backend_fastAPI

# essai rapide (~1 min) : vérifie juste que tout tourne
.venv/bin/python scripts/train_ai.py --generations 10 --population 20 --games 40

# entraînement sérieux (~7 min)
.venv/bin/python scripts/train_ai.py --generations 35 --population 40 --games 80 \
    --opponent heuristic --out data/ai/heuristique.json
```

Pendant que ça tourne, une ligne par génération :

```
génération  12 | meilleur  34.4 % | moyenne  25.0 % | élites  31.2 % | exploration 0.18 |  10.8s
```

| Colonne | Ce que ça veut dire | Ce qui doit t'alerter |
|---|---|---|
| **meilleur** | Le score du meilleur des 40 candidats | S'il ne monte plus du tout sur 10 générations, c'est fini : change quelque chose |
| **moyenne** | La moyenne des 40 | Si elle reste très loin du « meilleur », la recherche tâtonne encore |
| **élites** | La moyenne des 10 retenus | C'est le chiffre le plus fiable des trois (moins sensible au coup de chance) |
| **exploration** | À quel point la recherche cherche encore loin | **Tombée sous 0,15, l'IA a cessé d'explorer** : relancer avec une autre graine |

L'entraînement est **reproductible** : à `--seed` égale, le résultat est identique au poids près. Deux graines
différentes explorent différemment — c'est le moyen le plus simple de tenter sa chance une deuxième fois.

---

## 4. Mesurer ce que ça vaut (à ne pas sauter)

Le score affiché pendant l'entraînement est **optimiste** : c'est celui du candidat retenu, sur les parties qui
ont servi à le retenir. Il faut mesurer sur des parties fraîches.

```bash
.venv/bin/python scripts/evaluate_ai.py data/ai/heuristique.json
```

```
heuristique.json contre aléatoire   : 63.9 % ± 3.3 % (495 V / 273 D / 32 N sur 800) — significatif
heuristique.json contre heuristique : 56.2 % ± 3.4 % (428 V / 328 D / 44 N sur 800) — significatif
```

**L'écart avec l'entraînement est normal et instructif** : pendant l'entraînement, cette même IA affichait
68-70 %. Sur des parties fraîches, elle fait 56,2 %. Les 12 points d'écart sont exactement la raison d'être de
cette étape — le score d'entraînement est celui du candidat retenu **sur les parties qui ont servi à le
retenir**. Ne jamais annoncer un niveau d'après la sortie de `train_ai.py`.

Deux garde-fous y sont intégrés, et il faut les comprendre pour ne pas se mentir :

**La marge d'erreur.** « 52 % ± 4 % » ne veut **pas** dire mieux que 50 %. Ça veut dire « entre 48 % et 56 % » :
indistinguable du hasard. Le script écrit `NON significatif` dans ce cas. Pour départager deux IA proches, il
faut augmenter `--games`, pas relire le chiffre en plissant les yeux.

**Les camps inversés.** Chaque paire de decks est jouée deux fois, les rôles échangés. Sans ça, une IA pourrait
gagner simplement parce qu'elle a tiré les meilleures cartes.

### Les repères

| Affrontement | Taux | À quoi ça sert |
|---|---|---|
| aléatoire contre aléatoire | ~50 % | Contrôle : si ce chiffre dérive, l'arène est cassée |
| heuristique contre aléatoire | **81,3 % ± 2,7 %** | Le niveau de l'adversaire écrit à la main |
| poids à zéro contre heuristique | 20,9 % | Le point de départ de tout entraînement |
| **IA entraînée contre heuristique** | **56,2 % ± 3,4 %** | Où en est l'ébauche : elle le bat |
| IA entraînée contre aléatoire | 63,9 % ± 3,3 % | …mais reste loin des 81 % de l'heuristique (voir § 8) |

---

## 5. Les réglages, et lequel toucher quand

Tous se passent en ligne de commande. Voici lesquels bougent quoi.

| Réglage | Par défaut | Ce que ça change | Quand y toucher |
|---|---|---|---|
| `--generations` | 20 | Durée de la recherche | Le premier à augmenter si le score monte encore à la fin |
| `--population` | 30 | Nombre de candidats par génération | Augmente si « moyenne » reste très loin de « meilleur » |
| `--games` | 60 | Parties pour noter **chaque** candidat | **Augmente si les scores sautent dans tous les sens** : les notes sont trop bruitées |
| `--elite-fraction` | 0.25 | Part des candidats conservés | Baisse (0,1) pour une recherche plus agressive, monte (0,4) pour plus de prudence |
| `--opponent` | heuristic | Contre qui elle s'entraîne | Voir ci-dessous |
| `--spread` | 0.5 | Dispersion du tirage initial | Rarement utile |
| `--seed` | 0 | La graine du hasard | **Change-la pour retenter un entraînement qui a stagné** |

Le coût total se calcule : `générations × population × games` parties, à environ **1 300 parties par seconde**.
Le réglage par défaut, c'est donc 36 000 parties, une trentaine de secondes.

### Choisir l'adversaire d'entraînement

- **`--opponent random`** — facile. L'IA y atteint vite 55-60 %. Utile pour vérifier que la mécanique marche,
  mais elle y apprend de mauvaises habitudes (contre un adversaire qui joue n'importe quoi, écraser tout au
  round 1 fonctionne).
- **`--opponent heuristic`** — le vrai test. C'est le réglage recommandé.
- **`--opponent self`** — **auto-apprentissage** : l'IA affronte sa propre version courante. C'est la voie qui
  mène le plus loin à terme (c'est ainsi que les IA de go ont dépassé les humains), mais c'est aussi la plus
  capricieuse : deux IA médiocres peuvent se conforter mutuellement dans leur médiocrité et progresser en
  apparence sans jamais devenir bonnes. **À évaluer impérativement contre l'heuristique** après coup, sans quoi
  on ne sait rien de son vrai niveau.

---

## 6. Lire ce que l'IA a appris

C'est là que le choix d'une formule lisible paie. Après entraînement :

```bash
.venv/bin/python scripts/evaluate_ai.py data/ai/heuristique.json --explain
```

```
  +1.258  rapport_attaque    l'IA recherche ce critère — Mon attaque rapportée à l'attaque maximale
                             qu'il peut sortir. Au-dessus de 0,5 je suis favori.
  -0.636  pillz_misees       l'IA évite ce critère — Pillz dépensées sur ce coup, fury comprise.
```

Ces deux lignes se lisent : *« l'IA cherche à avoir l'attaque la plus forte, mais rechigne à dépenser ses pillz
pour ça »* — autrement dit elle a découvert toute seule l'économie de pillz, qui est le nerf du jeu. C'est bon
signe.

Inversement, un poids **négatif sur `coup_fatal`** (= elle évite le coup qui gagne la partie) est un signal
d'alarme : cela veut dire que l'entraînement a sélectionné du bruit, pas de la compétence. C'est arrivé
pendant la mise au point, avec trop peu de parties par candidat.

Le fichier `data/ai/*.json` est du JSON lisible : tu peux l'ouvrir, modifier un poids à la main, réévaluer.
C'est un moyen tout à fait légitime d'injecter ton intuition de joueur dans l'IA.

---

## 7. Jouer contre elle

```bash
.venv/bin/python scripts/train_ai.py --out data/ai/policy.json   # le nom compte
```

Redémarre le backend : l'adversaire « IA entraînée » devient disponible dans le jeu, au même titre que
« aléatoire » et « heuristique ». L'endpoint `GET /ai_strategies` dit lesquels sont disponibles — tant qu'aucune
IA n'est entraînée, « trained » est annoncé indisponible plutôt que proposé puis en échec.

---

## 8. Où ça coince, et les pistes

L'ébauche bat l'heuristique (56,2 %). Mais un chiffre doit t'empêcher de crier victoire :

| | contre l'aléatoire | contre l'heuristique |
|---|---|---|
| Heuristique | **81,3 %** | — |
| IA entraînée | **63,9 %** | **56,2 %** |

L'IA bat l'heuristique, et pourtant l'heuristique écrase bien mieux qu'elle un joueur au hasard. Ce n'est pas
une contradiction : **« être meilleur que » n'est pas transitif** dans un jeu. L'IA n'a pas appris à bien jouer
— elle a appris à **contrer ce joueur-là**, dont elle a vu 112 000 parties. Elle a trouvé sa faille, pas la
bonne stratégie générale.

C'est l'enseignement principal de cette première ébauche, et il est facile à vérifier dans les poids appris :
`juste_suffisant` (+2,95) et `rapport_attaque_probable` (+2,28) dominent tout le reste. Or
`rapport_attaque_probable` suppose précisément que l'adversaire **étale ses pillz sur les rounds restants**…
ce qui est la règle exacte de l'heuristique. L'IA a appris à miser une pillz de plus que ce que l'heuristique
allait miser. Redoutable contre elle, sans valeur contre quelqu'un d'autre.

**Ce qu'il faut en retenir pour la suite : s'entraîner contre un adversaire unique et prévisible produit un
contre-exemple sur mesure, pas un bon joueur.** C'est un piège classique, et il se soigne.

### Les pistes, de la moins à la plus lourde

- **Varier l'adversaire d'entraînement** (le plus rentable, et pas encore fait) : alterner aléatoire,
  heuristique et versions précédentes de l'IA au fil des générations. L'IA ne peut alors plus se contenter
  d'exploiter une seule faille. C'est le remède direct au problème ci-dessus.
- **`--opponent self`** va dans le même sens, mais avec sa propre fragilité : deux IA médiocres peuvent se
  conforter mutuellement. À évaluer impérativement contre l'heuristique après coup.
- **Plus de parties par candidat** (`--games 200`) : à 80 parties, la marge d'erreur est d'environ ±11 %, donc
  deux candidats séparés de 5 points sont départagés à pile ou face. Une partie du « progrès » est du bruit.
- **Ajouter des critères** — le levier le plus rentable sur le code. Chaque critère bien choisi donne à la
  formule un moyen d'exprimer une idée qu'elle ne pouvait pas dire. Deux exemples vécus dans ce projet :
  - sans critère sur la main adverse, l'IA plafonnait à ~20 % ;
  - la note étant une somme, elle préférait mécaniquement toujours *plus* de pillz ; le critère
    `juste_suffisant` (« je passe devant lui de peu ») a débloqué le passage de 35 % à 56 %. C'est aujourd'hui
    le poids le plus fort de toute l'IA.

  Le fichier à toucher est `src/core/ai/features.py` : une liste et une fonction. (Changer les critères rend
  illisibles les IA déjà entraînées — c'est détecté et signalé proprement, il faut ré-entraîner.)
- **Un adversaire glouton à 1 coup** (il simule tous ses coups et garde le meilleur) : meilleur étalon que
  l'heuristique, et surtout moins facile à contrer bêtement.
- **La vraie marche suivante** : remplacer la somme pondérée par un réseau de neurones et la méthode des élites
  par du PPO/DQN (PyTorch + Stable-Baselines3). Le moteur est déjà prêt — `src/core/ai/engine_api.py` fournit
  exactement le `step` / `legal_actions` qu'attend un environnement Gymnasium. Plus fort, mais plus lourd à
  installer et **impossible à relire**. À ne faire que quand la version lisible aura donné tout ce qu'elle peut,
  pour savoir ce qu'on gagne vraiment.

---

## 9. Les fichiers

| Fichier | Rôle |
|---|---|
| `src/core/ai/engine_api.py` | Le moteur en version « pure » : `new_game`, `legal_actions`, `step`. Ne touche à aucun fichier, ne modifie rien sur place |
| `src/core/ai/features.py` | Les 24 critères, avec l'explication de chacun. **Le fichier à modifier pour rendre l'IA plus fine** |
| `src/core/ai/policy.py` | L'IA : la note, le tirage au sort, la sauvegarde en JSON |
| `src/core/ai/train.py` | La méthode des élites |
| `src/core/ai/arena.py` | L'évaluation honnête : camps inversés, marge d'erreur |
| `src/core/ai/trained.py` | Le branchement dans le jeu (stratégie « trained ») |
| `src/core/ai/opponent.py` | Les adversaires de référence : aléatoire, heuristique |
| `scripts/train_ai.py` | Entraîner |
| `scripts/evaluate_ai.py` | Mesurer |
| `data/ai/*.json` | Les IA entraînées (ignorées par git : ça se régénère) |

Les tests : `tests/test_ai_engine_api.py` (la fondation) et `tests/test_ai_learning.py` (critères, politique,
arène, entraînement). Ils vérifient la mécanique, pas le niveau de jeu — mesurer un niveau demande des milliers
de parties, c'est le travail de `evaluate_ai.py`.
