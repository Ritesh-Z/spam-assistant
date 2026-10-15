// ---------------------------------------------------------------------------
// Sieve landing (one screen). Runs after sieve.js and strike.js (concatenated in ui/components.py).
// data = { brand: {...}, metrics: {...}, hero: [{label, color}], game: [{from, subject, truth}] }
// Clicking a [data-nav] element sends the page name back to Python.
// ---------------------------------------------------------------------------
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function fillBrand(root, b) {
  root.querySelectorAll("[data-b]").forEach((n) => { n.textContent = b[n.dataset.b] ?? ""; });
  const list = root.querySelector("[data-crew]");
  list.replaceChildren();
  for (const m of b.members) {
    const c = el("span", "member");
    if (m.role) c.title = m.role;
    c.append(el("span", "ini", m.initials), el("b", null, m.name), el("small", null, "roll " + m.roll));
    list.append(c);
  }
  if (b.guide) {                       // the guide: same chip, amber badge
    const g = el("span", "member guide");
    g.title = "Project guide";
    g.append(el("span", "ini", b.guide.initials), el("b", null, b.guide.name), el("small", null, b.guide.tag));
    list.append(g);
  }
}

function fillStats(root, m) {
  const box = root.querySelector("[data-stats]");
  box.replaceChildren();
  if (!m) return;
  const r = m.results[m.system || m.best_model];
  const c = r.confusion || {};
  const items = [
    [(r.accuracy * 100).toFixed(1) + "%", "accuracy"],
    [(r.f1 * 100).toFixed(1) + "%", "f1 score"],
    [String((c.fp ?? 0) + (c.fn ?? 0)), "mistakes"],
    [m.n_test.toLocaleString(), "test emails"],
  ];
  for (const [v, k] of items) {
    const s = el("div", "stat");
    s.append(el("b", null, v), el("span", null, k));
    box.append(s);
  }
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector(".sv");
  const cleanups = [];

  fillBrand(root, data.brand);
  fillStats(root, data.metrics);

  const onClick = (e) => {
    const nav = e.target.closest("[data-nav]");
    if (nav) { e.preventDefault(); setTriggerValue("nav", nav.dataset.nav); }
  };
  root.addEventListener("click", onClick);
  cleanups.push(() => root.removeEventListener("click", onClick));

  // three.js arcade
  let scene = null, dead = false;
  createSieveScene(root.querySelector("[data-scene]"), { variant: "hero", cards: data.hero, seed: 11 })
    .then((s) => { if (dead) s.dispose(); else scene = s; })
    .catch((err) => console.warn("Sieve: 3D scene unavailable", err));
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

  // Spam Strike (strike.js)
  cleanups.push(createStrike(root, data.game || [], data.metrics));

  return () => cleanups.forEach((f) => f());
}
