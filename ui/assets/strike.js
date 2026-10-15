// ---------------------------------------------------------------------------
// Spam Strike: a 2D shooter inside the landing CRT window.
// Emails fall as targets; shoot the spam, let real mail land.
// The player picks a model as the jet's targeting computer. Its weapons come
// from that model's real test results (models/metrics.json):
//   fire rate <- accuracy   power <- F1   lock-on <- recall
//   safety    <- 1 - false-alarm rate     scan time <- ms per email
// Each email is labelled SPAM, REAL or UNSURE; weaker models are unsure more often.
// SPACE (or holding the mouse) fires; the gun overheats. Every shot can hit real mail.
// Hacks are open to every jet but cost energy, earned only by playing well.
// Fire rate, power and the unsure rate are scaled across the models (the real gaps are small);
// lock-on and false alarms use the real rates, unscaled.
// ---------------------------------------------------------------------------
const STRIKE_BEST = "sieve-strike-best-v2";   // v2: manual fire (scores from the auto-fire version do not compare)
const MISSION_S = 45;
const SHIELDS = 3;
const TARGET_HP = 3;
const RANGE = 0.3;     // shots fade above this fraction of the screen: time to read each email

function strikeEl(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
const pct = (v, d = 1) => (v * 100).toFixed(d) + "%";
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/** One jet per model in metrics.json, plus a "no model" jet for comparison. */
function buildJets(metrics) {
  const res = metrics?.results || {};
  const names = Object.keys(res);
  const spec = (r) => { const c = r.confusion || {}; return c.tn != null ? c.tn / (c.tn + c.fp) : r.precision; };
  const rows = names.map((n) => ({ name: n, acc: res[n].accuracy, f1: res[n].f1, recall: res[n].recall,
    spec: spec(res[n]), ms: res[n].ms_per_email || 0.01 }));
  const span = (k) => { const v = rows.map((r) => r[k]); return [Math.min(...v), Math.max(...v)]; };
  const norm = (v, [lo, hi]) => (hi > lo ? (v - lo) / (hi - lo) : 1);
  const sAcc = span("acc"), sF1 = span("f1"), sRec = span("recall"), sSpec = span("spec");
  const best = (k) => rows.reduce((a, b) => (b[k] > a[k] ? b : a), rows[0])?.name;
  const tags = { [best("acc")]: "most accurate", [best("recall")]: "best lock-on", [best("spec")]: "fewest false alarms" };
  const fastest = rows.reduce((a, b) => (b.ms < a.ms ? b : a), rows[0])?.name;
  if (fastest && !tags[fastest]) tags[fastest] = "fastest scan";

  const jets = rows.map((r) => {
    const nA = norm(r.acc, sAcc), nF = norm(r.f1, sF1);
    return {
      ...r, scanner: true, tag: tags[r.name] || "",
      cooldown: 170 - 85 * nA,                  // ms between shots
      dmg: 1 + 0.9 * nF,                        // 1 .. 1.9 (target hp 3)
      falseRate: 1 - r.spec,
      scanDelay: clamp(0.15 + 0.25 * Math.log10(r.ms / 0.004), 0.15, 1.2),  // seconds
      unsure: 0.06 + 0.24 * (1 - nA),           // share of mail it can't call
      bars: { fire: 0.3 + 0.7 * nA, power: 0.3 + 0.7 * nF, lock: 0.3 + 0.7 * norm(r.recall, sRec),
        safe: 0.3 + 0.7 * norm(r.spec, sSpec) },
    };
  });
  jets.sort((a, b) => b.acc - a.acc);
  // every model jet gets every hack; the 2nd opinion only where the real system has one
  jets.forEach((j) => {
    j.hacks = ["lock", "spread", "slow", "emp", ...(/\+.*DistilBERT/.test(j.name) ? ["second"] : [])];
  });
  jets.push({ name: "No model", scanner: false, tag: "you read every email", cooldown: 200, dmg: 1, hacks: ["spread", "slow"],
    recall: 0, falseRate: 0, scanDelay: 0, unsure: 1, bars: { fire: 0.15, power: 0.15, lock: 0, safe: 0 } });
  return jets;
}

const HACKS = {
  lock: { name: "lock-on", glyph: "◎", tip: "shots curve toward mail labelled spam", note: "always on", off: "needs a model" },
  spread: { name: "spread", glyph: "⁂", key: "R", cost: 30, dur: 6, tip: "3-way shots for 6 s" },
  slow: { name: "slow-mo", glyph: "◷", key: "Q", cost: 40, dur: 3, tip: "slows the mail for 3 s" },
  emp: { name: "emp", glyph: "✷", key: "E", cost: 70, tip: "blasts all mail labelled spam (mislabels too)", off: "needs labels" },
  second: { name: "2nd opinion", glyph: "⧉", tip: "re-checks unsure mail, like the real SVM + DistilBERT", note: "always on",
    off: "SVM + DistilBERT only" },
};
const ENERGY = { kill: 12, deliver: 8, friendly: -30, leak: -20 };
const HEAT = { shot: 8, cool: 38, jam: 1.4 };   // per shot, per second, seconds jammed
const HACK_ORDER = ["lock", "spread", "slow", "emp", "second"];

function readStrikeBest() { try { return JSON.parse(localStorage.getItem(STRIKE_BEST) || "{}") || {}; } catch (e) { return {}; } }
function saveStrikeBest(v) { try { localStorage.setItem(STRIKE_BEST, JSON.stringify(v)); } catch (e) { /* storage off */ } }

function createStrike(root, pool, metrics) {
  const box = root.querySelector("[data-game]");
  const screen = root.querySelector(".screen");
  const canvas = root.querySelector("[data-strike]");
  const ctx = canvas.getContext("2d");
  const $ = (k) => root.querySelector(`[data-${k}]`);
  const jets = buildJets(metrics);
  let jet = jets[0];
  let W = 0, H = 0, dpr = 1, raf = 0, last = 0;
  let g = null;                       // the running mission
  const keys = {};
  const setState = (st) => { box.dataset.state = st; };

  // ---- hangar: model list + loadout ---------------------------------------------
  function stat(k, v, text, cls) {
    const r = strikeEl("div", "st" + (cls ? " " + cls : ""));
    const bar = strikeEl("i"); bar.style.setProperty("--v", (clamp(v, 0, 1) * 100).toFixed(0) + "%");
    r.append(strikeEl("span", null, k), bar, strikeEl("b", null, text));
    return r;
  }
  function renderHangar() {
    const list = $("jets");
    list.replaceChildren();
    jets.forEach((j, i) => {
      const b = strikeEl("button", "jrow");
      b.type = "button"; b.setAttribute("role", "radio"); b.dataset.jet = i;
      b.setAttribute("aria-checked", String(j === jet));
      b.append(strikeEl("span", "jr-n", String(i + 1)), strikeEl("span", "jr-name", j.name),
        strikeEl("span", "jr-v", j.scanner ? pct(j.acc) : "--"));
      list.append(b);
    });
    $("jname").textContent = jet.name;
    $("jtag").textContent = jet.tag;
    const st = $("jstats");
    st.replaceChildren(
      stat("fire rate", jet.bars.fire, jet.scanner ? `${pct(jet.acc)} accuracy` : "slow"),
      stat("power", jet.bars.power, jet.scanner ? `${pct(jet.f1)} F1` : "weak"),
      stat("lock-on", jet.bars.lock, jet.scanner ? `${pct(jet.recall)} of spam` : "none"),
      stat("safe", jet.bars.safe, jet.scanner ? `${pct(jet.falseRate)} false alarms` : "--"),
      stat("unsure", jet.unsure, jet.scanner ? `${pct(jet.unsure, 0)} of mail` : "every email", "unsure"),
    );
    const hk = $("jhacks");
    hk.replaceChildren();
    for (const h of HACK_ORDER) {
      const info = HACKS[h], on = jet.hacks.includes(h);
      const c = strikeEl("div", "hs" + (on ? "" : " off"));
      c.title = on ? info.tip : info.off;
      const name = strikeEl("b", null, info.name);
      if (info.key && on) name.append(strikeEl("kbd", null, info.key));
      const sub = !on ? info.off : info.cost ? `${info.cost} energy` : info.note;
      c.append(strikeEl("span", "gl", on ? info.glyph : "🔒"), name, strikeEl("small", null, sub));
      hk.append(c);
    }
    const best = readStrikeBest()[jet.name];
    $("best").textContent = best != null ? `best: ${best}` : "";
  }
  function pick(i) { if (jets[i]) { jet = jets[i]; renderHangar(); } }

  // ---- canvas ----------------------------------------------------------------
  function resize() {
    const r = screen.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(1, r.width); H = Math.max(1, r.height);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (g) g.jx = clamp(g.jx, 30, W - 30);
  }
  const ro = new ResizeObserver(resize);
  ro.observe(screen);
  resize();

  // ---- mission -----------------------------------------------------------------
  let bag = [];
  function nextEmail() {
    if (!bag.length) bag = pool.slice().sort(() => Math.random() - 0.5);
    return bag.pop();
  }
  function launch() {
    g = { t: 0, left: MISSION_S, score: 0, shield: SHIELDS, maxShield: SHIELDS,
      combo: 0, energy: 0, heat: 0, jam: 0, slowUntil: 0, spreadUntil: 0, emp: null, jx: W / 2, aimX: null, cool: 0, spawn: 0.4,
      targets: [], bullets: [], parts: [], pops: [], stars: Array.from({ length: 60 }, () => [Math.random(), Math.random(), Math.random()]),
      st: { killed: 0, spam: 0, delivered: 0, real: 0, ff: 0, leaked: 0, scanWrong: 0, scanWrongSeen: 0, unsure: 0, rechecked: 0 } };
    renderHackbar(); setState("play"); hud();
    canvas.focus({ preventScroll: true });
    last = performance.now();
    cancelAnimationFrame(raf); raf = requestAnimationFrame(frame);
  }
  function spawn() {
    const e = nextEmail();
    const w = Math.min(230, W * 0.46), h = 48;
    let x = 0;
    for (let k = 0; k < 8; k++) {   // avoid stacking on a recent target
      x = 12 + Math.random() * (W - w - 24);
      if (!g.targets.some((t) => t.y < h * 1.6 && Math.abs(t.x - x) < w)) break;
    }
    const mark = !jet.scanner ? null : Math.random() < jet.unsure ? "unsure" : callFor(e.truth);
    const wrong = isWrong(mark, e.truth);
    if (wrong) g.st.scanWrong++;
    if (mark === "unsure") g.st.unsure++;
    e.truth ? g.st.spam++ : g.st.real++;
    const p = g.t / MISSION_S;
    g.targets.push({ ...e, x, y: -h, w, h, hp: TARGET_HP, mark, wrong, scanAt: g.t + jet.scanDelay, vy: H / (5.5 - 2.5 * p), hit: 0 });
  }
  // a confident call at the model's real rates: recall on spam, false alarms on real mail
  function callFor(truth) { return truth ? (Math.random() < jet.recall ? "spam" : "real") : (Math.random() < jet.falseRate ? "spam" : "real"); }
  function isWrong(mark, truth) { return (mark === "spam" || mark === "real") && (mark === "spam") !== truth; }
  function pop(x, y, text, color) { g.pops.push({ x, y, text, color, life: 1.3 }); }
  function burst(x, y, color, n = 22) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, s = 60 + Math.random() * 220;
      g.parts.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 0.5 + Math.random() * 0.5, color });
    }
  }
  function resolve(t, destroyed) {
    const cx = t.x + t.w / 2, cy = t.y + t.h / 2;
    if (destroyed) {
      burst(cx, cy, t.truth ? "#FF5A5A" : "#4BE08F");
      if (t.truth) {
        g.st.killed++; g.combo++;
        const m = Math.min(5, 1 + Math.floor(g.combo / 3)), pts = 100 * m;
        g.score += pts; energy(ENERGY.kill); pop(cx, cy, m > 1 ? `+${pts}  x${m} combo` : `+${pts} spam down`, "#FFE7B0");
      } else { g.st.ff++; g.shield--; g.combo = 0; g.score -= 150; energy(ENERGY.friendly); pop(cx, cy, "friendly fire! real mail", "#FF6B6B"); }
    } else if (t.truth) { g.st.leaked++; g.shield--; g.combo = 0; g.score -= 50; energy(ENERGY.leak); pop(cx, H - 70, "spam got through", "#FF6B6B"); }
    else { g.st.delivered++; g.score += 50; energy(ENERGY.deliver); pop(cx, H - 70, "+50 delivered", "#4BE08F"); }
    if (t.wrong) { g.st.scanWrongSeen++; pop(cx, cy - 20, "model was wrong here", "#FFB000"); }
  }

  function energy(d) { g.energy = clamp(g.energy + d, 0, 100); }
  function useHack(h) {
    const info = HACKS[h];
    if (box.dataset.state !== "play" || !jet.hacks.includes(h) || !info.cost) return;
    if (g.energy < info.cost) { pop(g.jx, H - 90, `need ${info.cost} energy`, "#B8E86A"); return; }
    energy(-info.cost);
    if (h === "slow") { g.slowUntil = g.t + info.dur; pop(W / 2, H * 0.55, "SLOW-MO", "#B8E86A"); }
    if (h === "spread") { g.spreadUntil = g.t + info.dur; pop(g.jx, H - 90, "SPREAD", "#B8E86A"); }
    if (h === "emp") {
      g.emp = { t: g.t, x: g.jx, y: H - 46 };
      for (const t of g.targets) {
        if (!t.dead && t.y > -t.h / 2 && g.t >= t.scanAt && t.mark === "spam") { t.dead = true; resolve(t, true); }
      }
      g.targets = g.targets.filter((t) => !t.dead);
    }
    hud();
  }
  function renderHackbar() {
    const bar = $("hackbar");
    bar.replaceChildren();
    const en = strikeEl("div", "en");
    en.append(strikeEl("span", null, "energy"), strikeEl("i", null), strikeEl("b", null, "0"));
    bar.append(en);
    for (const h of jet.hacks.filter((h) => HACKS[h].key)) {   // passive hacks are listed in the hangar
      const info = HACKS[h];
      const b = strikeEl("button", "hk act");
      b.type = "button"; b.dataset.hack = h; b.title = info.tip;
      b.append(strikeEl("b", null, info.key), strikeEl("span", null, `${info.name} ${info.cost}`));
      bar.append(b);
    }
  }

  function update(dt) {
    g.t += dt; g.left = Math.max(0, MISSION_S - g.t);
    // fly
    const speed = 780;
    if (keys.left) g.jx -= speed * dt;
    if (keys.right) g.jx += speed * dt;
    if (g.aimX != null && !keys.left && !keys.right) g.jx += (g.aimX - g.jx) * Math.min(1, dt * 18);
    g.jx = clamp(g.jx, 24, W - 24);
    const jy = H - 46;
    // fire: SPACE or a held mouse button. Every shot heats the gun; at 100 it jams.
    g.cool -= dt * 1000;
    g.jam = Math.max(0, g.jam - dt);
    g.heat = Math.max(0, g.heat - HEAT.cool * dt);
    if ((keys.fire || g.mouseFire) && !g.jam && g.cool <= 0) {
      for (const vx of g.t < g.spreadUntil ? [-150, 0, 150] : [0]) g.bullets.push({ x: g.jx, y: jy - 22, vx, vx0: vx });
      g.cool = jet.cooldown;
      g.heat += HEAT.shot;
      if (g.heat >= 100) { g.heat = 100; g.jam = HEAT.jam; pop(g.jx, H - 90, "OVERHEAT", "#FF6B6B"); }
    }
    // spawn
    g.spawn -= dt;
    if (g.spawn <= 0 && g.left > 2) { spawn(); g.spawn = 0.95 - 0.5 * (g.t / MISSION_S); }
    // bullets: lock on to targets the model marked as spam
    for (const b of g.bullets) {
      if (jet.hacks.includes("lock")) {
        let best = null, bd = 1e9;
        for (const t of g.targets) {
          if (t.mark !== "spam" || g.t < t.scanAt) continue;
          const tx = t.x + t.w / 2, dy = b.y - (t.y + t.h / 2), dx = tx - b.x;
          if (dy > 0 && dy < 320 && Math.abs(dx) < t.w / 2 + 70 && Math.abs(dx) + dy < bd) { bd = Math.abs(dx) + dy; best = tx; }
        }
        b.vx = best != null ? clamp((best - b.x) * 6, -480, 480) : b.vx0;
      }
      b.x += b.vx * dt; b.y -= 900 * dt;
    }
    // hits
    for (const b of g.bullets) {
      for (const t of g.targets) {
        if (t.hp > 0 && b.x > t.x && b.x < t.x + t.w && b.y > t.y && b.y < t.y + t.h) {
          t.hp -= jet.dmg; t.hit = 0.12; b.dead = true;
          if (t.hp <= 0) { t.dead = true; resolve(t, true); }
          break;
        }
      }
    }
    if (jet.hacks.includes("second")) {
      for (const t of g.targets) {
        if (t.mark === "unsure" && g.t >= t.scanAt + 0.8) {
          t.mark = callFor(t.truth); t.wrong = isWrong(t.mark, t.truth); g.st.rechecked++;
          if (t.wrong) g.st.scanWrong++;
          pop(t.x + t.w / 2, t.y - 18, "2nd opinion: " + t.mark, "#B8E86A");
        }
      }
    }
    for (const t of g.targets) {
      t.y += t.vy * dt * (g.t < g.slowUntil ? 0.35 : 1); t.hit = Math.max(0, t.hit - dt);
      if (!t.dead && t.y > H) { t.dead = true; resolve(t, false); }
    }
    g.bullets = g.bullets.filter((b) => !b.dead && b.y > H * RANGE);
    g.targets = g.targets.filter((t) => !t.dead);
    for (const p of g.parts) { p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= 0.96; p.vy *= 0.96; p.life -= dt; }
    g.parts = g.parts.filter((p) => p.life > 0);
    for (const p of g.pops) { p.y -= 28 * dt; p.life -= dt; }
    g.pops = g.pops.filter((p) => p.life > 0);
    hud();
    if (g.shield <= 0 || (g.left <= 0 && !g.targets.length)) end();
  }

  // ---- drawing -------------------------------------------------------------------
  function fitText(text, max) {
    if (ctx.measureText(text).width <= max) return text;
    let s = text;
    while (s.length > 3 && ctx.measureText(s + "…").width > max) s = s.slice(0, -1);
    return s + "…";
  }
  function drawBg() {
    ctx.fillStyle = "#0B0805"; ctx.fillRect(0, 0, W, H);
    for (const s of g.stars) {   // drifting stars
      const y = (s[1] * H + g.t * (20 + s[2] * 50)) % H;
      ctx.fillStyle = `rgba(255,220,160,${0.25 + s[2] * 0.5})`;
      ctx.fillRect(s[0] * W, y, 1.5, 1.5);
    }
    // perspective grid floor
    const hz = H * 0.62;
    ctx.strokeStyle = "rgba(255,176,0,.16)"; ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = -10; i <= 10; i++) { ctx.moveTo(W / 2 + i * W * 0.02, hz); ctx.lineTo(W / 2 + i * W * 0.16, H); }
    const off = (g.t * 0.6) % 1;
    for (let k = 0; k < 9; k++) { const y = hz + (H - hz) * Math.pow((k + off) / 9, 2.2); ctx.moveTo(0, y); ctx.lineTo(W, y); }
    ctx.stroke();
    // weapon range: emails above this line can't be hit yet
    ctx.save();
    ctx.setLineDash([3, 7]); ctx.strokeStyle = "rgba(255,176,0,.22)";
    ctx.beginPath(); ctx.moveTo(0, H * RANGE); ctx.lineTo(W, H * RANGE); ctx.stroke();
    ctx.fillStyle = "rgba(255,176,0,.4)"; ctx.font = "10px 'Share Tech Mono', monospace";
    ctx.fillText("WEAPON RANGE", 10, H * RANGE - 5);
    ctx.restore();
  }
  function drawTarget(t) {
    const scanned = jet.scanner && g.t >= t.scanAt;
    const col = !jet.scanner ? "#B8A47E" : !scanned ? "#FFB000"
      : t.mark === "spam" ? "#FF5A5A" : t.mark === "unsure" ? "#FFD23F" : "#4BE08F";
    ctx.save();
    ctx.fillStyle = t.hit > 0 ? "rgba(255,240,210,.95)" : "rgba(24,18,11,.94)";
    ctx.strokeStyle = col; ctx.lineWidth = 1.5;
    if (jet.scanner && !scanned) ctx.setLineDash([5, 4]);
    ctx.beginPath(); ctx.roundRect(t.x, t.y, t.w, t.h, 4); ctx.fill(); ctx.stroke();
    ctx.setLineDash([]);
    // envelope flap
    ctx.globalAlpha = 0.35; ctx.beginPath(); ctx.moveTo(t.x, t.y); ctx.lineTo(t.x + t.w / 2, t.y + 14); ctx.lineTo(t.x + t.w, t.y); ctx.stroke();
    ctx.globalAlpha = 1;
    // chip
    const chip = !jet.scanner ? "?" : !scanned ? "scan…" : t.mark === "spam" ? "SPAM" : t.mark === "unsure" ? "UNSURE ?" : "REAL";
    ctx.font = "600 10px 'Share Tech Mono', monospace";
    const cw = ctx.measureText(chip).width + 10;
    ctx.fillStyle = col; ctx.fillRect(t.x + t.w - cw, t.y - 14, cw, 14);
    ctx.fillStyle = "#120D07"; ctx.fillText(chip, t.x + t.w - cw + 5, t.y - 3.5);
    // text
    ctx.fillStyle = t.hit > 0 ? "#120D07" : "#FFF3DC";
    ctx.font = "600 13px system-ui, 'Segoe UI', sans-serif";
    ctx.fillText(fitText(t.subject, t.w - 14), t.x + 7, t.y + 22);
    ctx.fillStyle = t.hit > 0 ? "#5A4A30" : "#A88B5A";
    ctx.font = "11px 'Share Tech Mono', monospace";
    ctx.fillText(fitText(t.from, t.w - 14), t.x + 7, t.y + 39);
    // lock-on brackets
    if (scanned && t.mark === "spam") {
      ctx.strokeStyle = col; ctx.lineWidth = 2;
      const p = 5 + Math.sin(g.t * 8) * 2, L = 10, x0 = t.x - p, y0 = t.y - p, x1 = t.x + t.w + p, y1 = t.y + t.h + p;
      ctx.beginPath();
      ctx.moveTo(x0, y0 + L); ctx.lineTo(x0, y0); ctx.lineTo(x0 + L, y0);
      ctx.moveTo(x1 - L, y0); ctx.lineTo(x1, y0); ctx.lineTo(x1, y0 + L);
      ctx.moveTo(x0, y1 - L); ctx.lineTo(x0, y1); ctx.lineTo(x0 + L, y1);
      ctx.moveTo(x1 - L, y1); ctx.lineTo(x1, y1); ctx.lineTo(x1, y1 - L);
      ctx.stroke();
    }
    // damage
    if (t.hp < TARGET_HP) {
      ctx.fillStyle = "rgba(255,255,255,.12)"; ctx.fillRect(t.x + 6, t.y + t.h - 5, t.w - 12, 2);
      ctx.fillStyle = col; ctx.fillRect(t.x + 6, t.y + t.h - 5, (t.w - 12) * Math.max(0, t.hp) / TARGET_HP, 2);
    }
    ctx.restore();
  }
  function drawJet() {
    const x = g.jx, y = H - 46;
    ctx.save();
    ctx.shadowColor = "#FFB000"; ctx.shadowBlur = 14;
    ctx.strokeStyle = "#FFB000"; ctx.fillStyle = "rgba(255,176,0,.18)"; ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, y - 24); ctx.lineTo(x + 7, y - 6); ctx.lineTo(x + 24, y + 8); ctx.lineTo(x + 24, y + 13);
    ctx.lineTo(x + 7, y + 8); ctx.lineTo(x + 9, y + 17); ctx.lineTo(x - 9, y + 17); ctx.lineTo(x - 7, y + 8);
    ctx.lineTo(x - 24, y + 13); ctx.lineTo(x - 24, y + 8); ctx.lineTo(x - 7, y - 6); ctx.closePath();
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = `rgba(255,${120 + Math.random() * 80},0,.9)`;   // exhaust
    ctx.fillRect(x - 3, y + 18, 6, 6 + Math.random() * 8);
    ctx.restore();
    // heat gauge
    const hw = 54, hx = x - hw / 2, hy = y + 30;
    ctx.fillStyle = "rgba(255,255,255,.12)"; ctx.fillRect(hx, hy, hw, 4);
    ctx.fillStyle = g.jam ? "#FF5A5A" : g.heat > 70 ? "#FF9A3A" : "#FFB000";
    ctx.fillRect(hx, hy, hw * g.heat / 100, 4);
    if (g.jam) { ctx.textAlign = "center"; ctx.font = "11px 'Share Tech Mono', monospace"; ctx.fillText("JAMMED", x, hy + 15); ctx.textAlign = "left"; }
  }
  function draw() {
    drawBg();
    for (const t of g.targets) drawTarget(t);
    ctx.save();
    ctx.shadowColor = "#FFB000"; ctx.shadowBlur = 8; ctx.strokeStyle = "#FFE7B0"; ctx.lineWidth = 2;
    ctx.beginPath();
    for (const b of g.bullets) { ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - b.vx * 0.02, b.y + 10); }
    ctx.stroke(); ctx.restore();
    for (const p of g.parts) { ctx.globalAlpha = clamp(p.life * 1.6, 0, 1); ctx.fillStyle = p.color; ctx.fillRect(p.x, p.y, 3, 3); }
    ctx.globalAlpha = 1;
    drawJet();
    if (g.emp && g.t - g.emp.t < 0.6) {
      const k = (g.t - g.emp.t) / 0.6;
      ctx.save(); ctx.strokeStyle = `rgba(184,232,106,${1 - k})`; ctx.lineWidth = 6 * (1 - k) + 1;
      ctx.beginPath(); ctx.arc(g.emp.x, g.emp.y, k * Math.hypot(W, H), 0, Math.PI * 2); ctx.stroke(); ctx.restore();
    }
    if (g.t < g.slowUntil) { ctx.fillStyle = "rgba(184,232,106,.08)"; ctx.fillRect(0, 0, W, H); }
    ctx.textAlign = "center";
    for (const p of g.pops) {
      ctx.globalAlpha = clamp(p.life, 0, 1); ctx.fillStyle = p.color;
      ctx.font = "600 13px 'Share Tech Mono', monospace"; ctx.fillText(p.text, p.x, p.y);
    }
    ctx.globalAlpha = 1;
    if (g.t < 5) {   // controls tip
      ctx.globalAlpha = clamp(5 - g.t, 0, 1);
      ctx.font = "14px 'Share Tech Mono', monospace";
      const tip = ["shoot SPAM · let REAL mail land", "← → or mouse to fly · SPACE to fire",
        "don't hold it down: the gun overheats",
        jet.hacks.includes("emp") ? "earn energy → R spread · Q slow-mo · E emp" : "earn energy → R spread · Q slow-mo",
        jet.scanner ? "UNSURE (yellow) is your call · P pause" : "no labels: read every email · P pause"];
      tip.forEach((line, k) => { ctx.fillStyle = k ? "#E6D3AE" : "#FFE7B0"; ctx.fillText(line, W / 2, H * 0.5 + k * 22); });
      ctx.globalAlpha = 1;
    }
    ctx.textAlign = "left";
  }
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (box.dataset.state !== "play" || !g) return;
    update(dt);
    if (box.dataset.state === "play") { draw(); raf = requestAnimationFrame(frame); }
  }
  function hud() {
    $("h-time").textContent = g ? Math.ceil(g.left) : MISSION_S;
    $("h-score").textContent = g ? g.score : 0;
    $("h-shield").textContent = g ? "■".repeat(Math.max(0, g.shield)) + "□".repeat(Math.max(0, g.maxShield - Math.max(0, g.shield))) : "■■■";
    if (g) {
      $("h-combo").textContent = g.combo >= 3 ? `x${Math.min(5, 1 + Math.floor(g.combo / 3))}` : "";
      const en = root.querySelector(".hackbar .en");
      if (en) { en.querySelector("i").style.setProperty("--v", g.energy + "%"); en.querySelector("b").textContent = Math.floor(g.energy); }
      root.querySelectorAll("[data-hack]").forEach((b) => {
        b.classList.toggle("ready", g.energy >= HACKS[b.dataset.hack].cost);
      });
    }
    $("h-jet").textContent = jet.name;
  }

  // ---- pause / end -----------------------------------------------------------------
  function pause() { if (box.dataset.state === "play") { setState("pause"); cancelAnimationFrame(raf); } }
  function resume() {
    if (box.dataset.state !== "pause") return;
    setState("play"); last = performance.now(); raf = requestAnimationFrame(frame);
    canvas.focus({ preventScroll: true });
  }
  function end() {
    cancelAnimationFrame(raf);
    const s = g.st;
    $("verdict").textContent = g.shield > 0 ? "Mission complete" : "Shields down";
    $("final").textContent = g.score;
    const rows = $("tally");
    rows.replaceChildren();
    for (const [k, v, good] of [
      ["spam shot down", `${s.killed}`, true], ["real mail delivered", `${s.delivered}`, true],
      ["friendly fire", `${s.ff}`, s.ff === 0], ["spam got through", `${s.leaked}`, s.leaked === 0]]) {
      const r = strikeEl("div", "tl" + (good ? "" : " bad"));
      r.append(strikeEl("b", null, v), strikeEl("span", null, k));
      rows.append(r);
    }
    $("scannote").textContent = jet.scanner
      ? `${jet.name} labelled ${s.spam + s.real} emails: ${s.unsure} unsure`
        + (s.rechecked ? ` (${s.rechecked} settled by the 2nd opinion)` : "") + `, ${s.scanWrong} wrong. `
        + `On ${metrics.n_test.toLocaleString()} real test emails it is right ${pct(jet.acc)} of the time.`
      : "You flew without a model: no labels, no lock-on. Try a model jet and compare scores.";
    const best = readStrikeBest();
    const prev = best[jet.name];
    if (prev == null || g.score > prev) { best[jet.name] = g.score; saveStrikeBest(best); }
    const board = Object.entries(best).sort((a, b) => b[1] - a[1]).slice(0, 4);
    $("board").textContent = board.length ? "your best: " + board.map(([n, v]) => `${n} ${v}`).join(" · ") : "";
    setState("end");
    root.querySelector('.g-end [data-act="launch"]').focus({ preventScroll: true });
  }

  // ---- input ---------------------------------------------------------------------------
  const KEY = { arrowleft: "left", a: "left", arrowright: "right", d: "right", " ": "fire" };
  const onKey = (ev) => {
    if (ev.target.closest?.("input, textarea, select") || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    const st = box.dataset.state, k = ev.key.toLowerCase();
    if (st === "play") {
      if (KEY[k]) { keys[KEY[k]] = true; g.aimX = null; ev.preventDefault(); }
      else if (k === "p" || k === "escape") { ev.preventDefault(); pause(); }
      else if (k === "q") useHack("slow");
      else if (k === "e") useHack("emp");
      else if (k === "r") useHack("spread");
    } else if (st === "pause") {
      if (k === "p" || k === "escape" || k === "enter" || k === " ") { ev.preventDefault(); resume(); }
    } else if (st === "hangar") {
      if (/^[1-9]$/.test(k)) pick(Number(k) - 1);
      else if (k === "enter" && !ev.target.closest?.("button:not(.jet)")) { ev.preventDefault(); launch(); }
    } else if (st === "end") {
      if (k === "enter" && !ev.target.closest?.("button")) { ev.preventDefault(); launch(); }
      else if (k === "h") renderHangarAndShow();
    }
  };
  const onKeyUp = (ev) => { const k = KEY[ev.key.toLowerCase()]; if (k) keys[k] = false; };
  const onMove = (ev) => {
    if (box.dataset.state !== "play") return;
    g.aimX = ev.clientX - canvas.getBoundingClientRect().left;
  };
  const onDown = (ev) => { onMove(ev); if (g && box.dataset.state === "play") g.mouseFire = true; };
  const onUp = () => { if (g) g.mouseFire = false; };
  const onClick = (ev) => {
    const j = ev.target.closest("[data-jet]");
    if (j) { pick(Number(j.dataset.jet)); return; }
    const b = ev.target.closest("[data-act]");
    if (!b || !box.contains(b)) return;
    ({ launch, resume, hangar: renderHangarAndShow })[b.dataset.act]?.();
  };
  const onHack = (ev) => { const b = ev.target.closest("[data-hack]"); if (b) { useHack(b.dataset.hack); canvas.focus({ preventScroll: true }); } };
  const onHide = () => { if (document.hidden) pause(); };
  const onBlur = () => { for (const k in keys) keys[k] = false; onUp(); };   // no stuck keys
  function renderHangarAndShow() { renderHangar(); setState("hangar"); hud(); }

  box.addEventListener("click", onClick);
  $("hackbar").addEventListener("click", onHack);
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerdown", onDown);
  window.addEventListener("pointerup", onUp);
  canvas.addEventListener("pointerleave", onUp);
  window.addEventListener("keydown", onKey);
  window.addEventListener("keyup", onKeyUp);
  window.addEventListener("blur", onBlur);
  document.addEventListener("visibilitychange", onHide);
  renderHangarAndShow();

  return () => {
    cancelAnimationFrame(raf); ro.disconnect();
    box.removeEventListener("click", onClick);
    $("hackbar").removeEventListener("click", onHack);
    canvas.removeEventListener("pointermove", onMove);
    canvas.removeEventListener("pointerdown", onDown);
    window.removeEventListener("pointerup", onUp);
    canvas.removeEventListener("pointerleave", onUp);
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("keyup", onKeyUp);
    window.removeEventListener("blur", onBlur);
    document.removeEventListener("visibilitychange", onHide);
  };
}
