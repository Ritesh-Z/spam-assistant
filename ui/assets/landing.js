// ---------------------------------------------------------------------------
// Sieve landing. Runs after sieve.js (concatenated in ui/components.py).
// data = { demo: [...], metrics: {...}, hero: [{label, color}], colors: {...} }
// Clicking a [data-nav] element sends the page name back to Python.
// ---------------------------------------------------------------------------
const LABEL_TEXT = { spam: "SPAM", suspicious: "SUSPICIOUS", promotion: "PROMOTION", update: "UPDATE", safe: "SAFE" };

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function badge(label, confidence, colors) {
  const b = el("span", "badge");
  b.style.setProperty("--c", colors[label]);
  b.append(el("i"), document.createTextNode(LABEL_TEXT[label] + " "), el("b", null, Math.round(confidence * 100) + "%"));
  return b;
}

function renderCard(card, ex, colors) {
  card.replaceChildren();
  const c = colors[ex.label];
  card.style.setProperty("--c", c);

  const head = el("div", "rc-head");
  const left = el("div");
  left.append(el("div", "from", "from · " + ex.sender), el("div", "subject", ex.subject));
  head.append(left, badge(ex.label, ex.confidence, colors));

  const meter = el("div", "meter");
  const track = el("div", "meter-track");
  const fill = el("div", "meter-fill");
  const dot = el("div", "meter-dot");
  fill.style.width = "0%"; dot.style.left = "0%";
  track.append(fill, dot);
  const scale = el("div", "meter-scale");
  for (const v of [0, 60, 85, 100]) {
    const s = el("span", null, v === 0 ? "0" : v + "%");
    s.style.left = v + "%";
    if (v === 0) s.style.transform = "none";
    if (v === 100) s.style.transform = "translateX(-100%)";
    scale.append(s);
  }
  const cap = el("div", "meter-cap",
    `spam probability ${(ex.spam_prob * 100).toFixed(1)}%` + (ex.is_list ? " · mailing-list mail needs 95% to count as spam" : ""));
  meter.append(track, scale, cap);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const p = (ex.spam_prob * 100).toFixed(1) + "%";
    fill.style.width = p; dot.style.left = p;
  }));

  const grid = el("div", "rc-grid");
  const w = el("div");
  w.append(el("h4", null, "warning signs"));
  const ul = el("ul", "warn");
  if (ex.warnings.length) ex.warnings.forEach((t) => ul.append(el("li", null, t)));
  else ul.append(el("li", "none", "No warning signs found"));
  w.append(ul);

  const t = el("div");
  const pushSpam = ex.label === "spam" || ex.label === "suspicious";
  const terms = pushSpam ? ex.spam_terms : ex.safe_terms;
  t.append(el("h4", null, pushSpam ? "words pushing toward spam" : "words pushing toward safe"));
  const max = Math.max(...terms.map((x) => Math.abs(x[1])), 1e-9);
  terms.slice(0, 6).forEach(([term, wgt]) => {
    const row = el("div", "wbar");
    const tr = el("span", "t"), i = el("i");
    i.style.width = (Math.abs(wgt) / max * 100).toFixed(0) + "%";
    tr.append(i);
    row.append(el("span", null, term), tr);
    t.append(row);
  });
  if (!terms.length) t.append(el("div", "small", "none"));
  grid.append(w, t);

  const mail = el("div", "mail");
  mail.innerHTML = ex.html;          // escaped + <mark> added in Python (predict.highlight_html)
  card.append(head, meter, grid, mail);
}

function renderModels(root, m, data) {
  if (!m) return;
  const shown = m.system || m.best_model;            // the system the app actually runs
  const best = m.results[shown];
  root.querySelector("[data-testset]").textContent =
    `${shown}${best.note ? " *" : ""} · tested on ${m.n_test.toLocaleString()} held-out emails`;
  const kpis = root.querySelector("[data-kpis]");
  for (const [k, name] of [["accuracy", "accuracy"], ["precision", "precision"], ["recall", "recall"], ["f1", "f1 score"]]) {
    const d = el("div", "kpi");
    const v = el("div", "v", (best[k] * 100).toFixed(1));
    v.append(el("small", null, "%"));
    d.append(v, el("div", "k", name));
    kpis.append(d);
  }
  // Built in Python (theme.mistakes_chart) so the app and landing share it.
  root.querySelector("[data-models]").innerHTML = data.mistakes_html || "";
  const bestEl = root.querySelector("[data-best]");
  if (bestEl) bestEl.textContent = m.best_model;
  const nt = root.querySelector("[data-ntrain]");
  if (nt) nt.textContent = m.n_train.toLocaleString();
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector(".sv");
  const colors = data.colors;
  const cleanups = [];

  // navigation into the app + smooth scroll inside the page
  const onClick = (e) => {
    const nav = e.target.closest("[data-nav]");
    if (nav) { e.preventDefault(); setTriggerValue("nav", nav.dataset.nav); return; }
    const sc = e.target.closest("[data-scroll]");
    if (sc) {
      e.preventDefault();
      root.querySelector("#" + sc.dataset.scroll)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };
  root.addEventListener("click", onClick);
  cleanups.push(() => root.removeEventListener("click", onClick));

  // demo
  const list = root.querySelector("[data-demo-list]");
  const card = root.querySelector("[data-demo-card]");
  list.replaceChildren();
  const items = data.demo.map((ex, i) => {
    const b = el("button", "demo-item");
    b.setAttribute("role", "tab");
    b.style.setProperty("--c", colors[ex.label]);
    const who = el("div", "who");
    who.append(el("span", null, ex.sender), el("span", null, LABEL_TEXT[ex.label].toLowerCase()));
    b.append(who, el("div", "what", ex.subject));
    b.addEventListener("click", () => select(i));
    list.append(b);
    return b;
  });
  function select(i) {
    items.forEach((b, j) => { b.classList.toggle("on", i === j); b.setAttribute("aria-selected", i === j); });
    renderCard(card, data.demo[i], colors);
  }
  if (items.length) select(0);

  root.querySelector("[data-kpis]").replaceChildren();
  root.querySelector("[data-models]").replaceChildren();
  renderModels(root, data.metrics, data);

  // reveal-on-scroll
  const targets = root.querySelectorAll(".sec-head, .steps li, .demo, .lab, .model, .foot");
  targets.forEach((t) => t.classList.add("rv"));
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }, { threshold: 0.12 });
  targets.forEach((t) => io.observe(t));
  cleanups.push(() => io.disconnect());

  // three.js hero
  let scene = null, dead = false;
  createSieveScene(root.querySelector("[data-scene]"), { variant: "hero", cards: data.hero, seed: 11 })
    .then((s) => { if (dead) s.dispose(); else scene = s; })
    .catch((err) => console.warn("Sieve: 3D hero unavailable", err));
  const legend = root.querySelector("[data-legend]");
  let pinned = null;
  const setFocus = (label) => {
    scene?.focus(label);
    legend.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.focus === label));
  };
  legend.addEventListener("pointerover", (e) => { const b = e.target.closest("button"); if (b) setFocus(b.dataset.focus); });
  legend.addEventListener("pointerleave", () => setFocus(pinned));
  legend.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    pinned = pinned === b.dataset.focus ? null : b.dataset.focus;
    setFocus(pinned);
  });
  cleanups.push(() => { dead = true; scene?.dispose(); });

  return () => cleanups.forEach((f) => f());
}
