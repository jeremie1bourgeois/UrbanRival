# UrbanRival — consignes pour Claude

Réimplémentation d'Urban Rivals : moteur de règles Python/FastAPI (`UrbanPy/Backend_fastAPI`)
et front Vue 3 + TypeScript (`UrbanVue`). Structure, commandes et état du projet : voir `README.md`.
Règles du jeu : `docs/REGLES.md` et `docs/REGLES-glossaire-officiel.md`. Feuille de route : `docs/ROADMAP.md`.

## Façon de travailler

- **Granulaire** : une demande = un changement ciblé, le plus petit qui résout le problème.
  Pas de refactoring opportuniste, pas de « pendant que j'y suis ». Un problème hors périmètre
  se signale en une phrase, il ne se corrige pas dans la même passe.
- **Explicite** : avant de modifier, dire quels fichiers et pourquoi. Après, dire ce qui a changé
  et ce qui a été vérifié (commande lancée, résultat réel). Aucune hypothèse implicite : si une
  interprétation est choisie, la nommer.
- **Simple** : la solution la plus directe qui passe les tests. Pas d'abstraction pour un seul
  usage, pas de paramètre « au cas où », pas d'indirection sans lecteur. Une fonction =
  une responsabilité, courte, nommée d'après ce qu'elle fait.
- **Par petits pas vérifiables** : découper une tâche en étapes qui laissent chacune les tests verts.
  Lancer les tests concernés après chaque étape, pas seulement à la fin.
- Quand deux lectures d'une demande mènent à un travail différent, poser la question avant
  de coder. Sinon, décider et le dire.

## Code

- Backend : Python 3.12, FastAPI, pytest. Front : Vue 3, TypeScript, Tailwind, vitest.
- Suivre le style du fichier ouvert (nommage, densité de commentaires, idiomes) plutôt qu'un style idéal.
- Nommer par le rôle, jamais `data`, `tmp`, `helper`, `utils2`.
- Pas de commentaire qui répète le code ; un commentaire explique un *pourquoi* non évident.
- `data/jsonData_officiel.json` est la seule source de vérité sur les cartes : ne jamais l'éditer à la main.
- Toute règle ou capacité ajoutée au moteur s'accompagne d'un test de bout en bout
  (texte d'ability → résultat du round) dans `UrbanPy/Backend_fastAPI/tests/`.

## Vérification

```bash
cd UrbanPy/Backend_fastAPI && .venv/bin/python -m pytest -q
cd UrbanVue && npm test && npm run lint && npm run build
```

## Commits

Un commit = un changement cohérent et relisible seul. Message en français,
`type(scope): description` (ex. `feat(moteur): …`, `fix(front): …`, `docs(oracle): …`).
Ne committer que sur demande.
