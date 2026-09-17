// Capture d'un combat réel Urban Rivals depuis le client web (urban-rivals.com/game/play/, session connectée).
// Voir docs/ur-abilitydata-modele.md et docs/ROADMAP.md § 2.B.
//
// 1. Avant de lancer le combat, coller ce fichier entier dans la console du navigateur (ou l'exécuter via un outil
//    d'automatisation) : il intercepte les réponses de POST /api/private/v2/ (fetch et XHR) dans window.__urCapture.
// 2. Jouer les 4 rounds.
// 3. Enchaîner autant de combats que voulu sans recharger la page (sinon : recoller le script puis urRestore()).
// 4. Exécuter `urRecords()` : un tableau d'enregistrements au format de data/ur_battles/*.json (p0 = joueur 0 du
//    serveur, p1 = joueur 1) ; `scripts/import_ur_battles.py` les éclate en fichiers. `urAbilities()` : le modèle
//    abilityData de chaque pouvoir vu.

if (!window.__urCapture) {
  window.__urCapture = [];
  const push = (kind, url, res) => { try { window.__urCapture.push({ t: Date.now(), kind, url: String(url), res }); } catch (e) {} };
  const origOpen = XMLHttpRequest.prototype.open, origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__url = u; return origOpen.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (body) {
    const xhr = this;
    xhr.addEventListener("load", () => { if (String(xhr.__url).includes("/api/")) push("xhr", xhr.__url, xhr.responseText); });
    return origSend.apply(this, arguments);
  };
  const origFetch = window.fetch;
  window.fetch = async function (input, init) {
    const r = await origFetch.apply(this, arguments);
    try {
      const url = typeof input === "string" ? input : input.url;
      if (String(url).includes("/api/")) r.clone().text().then((txt) => push("fetch", url, txt));
    } catch (e) {}
    return r;
  };
}

// Sauvegarde continue dans localStorage (clé ur_capture) : survit à un rechargement de page ; urRestore() recharge.
if (!window.__urSaver) {
  window.__urSaver = setInterval(() => { try { localStorage.setItem("ur_capture", JSON.stringify(window.__urCapture.filter((c) => c.res && c.res.startsWith('{"battles.status"')))); } catch (e) {} }, 5000);
}
function urRestore() { const saved = JSON.parse(localStorage.getItem("ur_capture") || "[]"); window.__urCapture = saved.concat(window.__urCapture); return window.__urCapture.length; }

function urStatuses() {
  const out = [];
  let prev = null;
  for (const c of window.__urCapture) {
    if (!c.res || !c.res.startsWith('{"battles.status"')) continue;
    const b = JSON.parse(c.res)["battles.status"].data.battle;
    const sig = JSON.stringify([b.id, b.round, b.status, b.turnPlayerId, b.player0.life, b.player1.life, b.player0.pillz, b.player1.pillz,
      b.player0.characters.map((x) => [x.roundPlayed, x.pillzUsed, x.roundAttack]), b.player1.characters.map((x) => [x.roundPlayed, x.pillzUsed, x.roundAttack])]);
    if (sig !== prev) { out.push(b); prev = sig; }
  }
  return out;
}

// Camp qui joue en premier au round r : celui dont une carte est déjà posée dans le premier statut du round (un
// adversaire qui joue instantanément — bot — a déjà joué quand le premier statut arrive et turnPlayerId pointe alors
// sur nous) ; sinon turnPlayerId du premier statut où personne n'a joué.
function urFirstOf(sts, r, p0id) {
  for (const b of sts.filter((b) => b.round === r)) {
    const a = b.player0.characters.some((x) => x.roundPlayed === r), c = b.player1.characters.some((x) => x.roundPlayed === r);
    if (a && !c) return "p0";
    if (c && !a) return "p1";
    if (!a && !c) return b.turnPlayerId === p0id ? "p0" : "p1";
  }
  return null;
}

function urRecordOf(sts) {
  const first = sts[0];
  const pl = (p) => ({ name: p.player.name, base_life: p.baseLife, base_pillz: p.basePillz, cards: p.characters.map((x) => ({ id: x.id, level: x.level })) });
  const rounds = [];
  for (let r = 0; r < 4; r++) {
    const start = sts.find((b) => b.round === r);
    const resolved = sts.filter((b) => b.round === r && [b.player0, b.player1].every((p) => p.characters.some((x) => x.roundPlayed === r && x.roundAttack >= 0))).slice(-1)[0];
    const next = sts.find((b) => b.round === r + 1);
    if (!start || !resolved) continue;
    const side = (p) => { const x = p.characters.find((x) => x.roundPlayed === r); return { index: x.index, pillz: x.pillzUsed, fury: !!x.isFury, power: x.roundPower, damage: x.roundDamage, attack: x.roundAttack, won: x.roundWon }; };
    rounds.push({ round: r + 1, first: urFirstOf(sts, r, first.player0.player.id),
      before: { life: [start.player0.life, start.player1.life], pillz: [start.player0.pillz, start.player1.pillz] },
      p0: side(resolved.player0), p1: side(resolved.player1),
      post_round: [resolved.player0.postRoundAbilities, resolved.player1.postRoundAbilities],
      after: next ? { life: [next.player0.life, next.player1.life], pillz: [next.player0.pillz, next.player1.pillz] } : { life: null, pillz: null } });
  }
  return { _comment: "Combat réel Urban Rivals capturé via battles.status (voir scripts/ur_capture.js).", battle_id: first.id, rule_id: first.battleRuleId,
    p0: pl(first.player0), p1: pl(first.player1), rounds };
}

// Tous les combats capturés depuis le chargement du script (ou urRestore()), un enregistrement par combat.
function urRecords() {
  const byBattle = {};
  for (const b of urStatuses()) (byBattle[b.id] = byBattle[b.id] || []).push(b);
  return JSON.stringify(Object.values(byBattle).map(urRecordOf).filter((r) => r.rounds.length), null, 1);
}
function urRecord() { return urRecords(); }

function urAbilities() {
  const abilities = {};
  for (const b of urStatuses()) for (const p of [b.player0, b.player1]) for (const x of p.characters) for (const k of ["ability", "bonus"]) if (x[k]) abilities[x[k].id] = x[k];
  return JSON.stringify(abilities, null, 1);
}
