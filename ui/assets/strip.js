// ---------------------------------------------------------------------------
// Inbox sorting strip. Runs after sieve.js.
// data = { cards: [{label, color}], counts: {spam: n, ...}, colors: {...} }
// One card per scanned email, sorted into one lane per label.
// ---------------------------------------------------------------------------
// LANES comes from sieve.js

export default function (component) {
  const { data, parentElement } = component;
  const root = parentElement.querySelector(".strip");
  const lanes = root.querySelector("[data-lanes]");
  lanes.replaceChildren();
  LANES.forEach((k, i) => {
    const row = document.createElement("div");
    row.className = "lane";
    row.style.setProperty("--c", data.colors[k]);
    row.style.top = (16 + 17 * i) + "%";      // = (1 - laneY / halfH) / 2
    row.innerHTML = '<i></i><span class="k"></span><span class="v"></span>';
    row.querySelector(".k").textContent = k;
    row.querySelector(".v").textContent = data.counts[k] ?? 0;
    row.addEventListener("pointerenter", () => scene?.focus(k));
    row.addEventListener("pointerleave", () => scene?.focus(null));
    lanes.append(row);
  });
  root.querySelector("[data-total]").textContent = data.cards.length;

  let scene = null, dead = false;
  createSieveScene(root.querySelector("[data-scene]"), { variant: "strip", cards: data.cards, seed: 3 })
    .then((s) => { if (dead) s.dispose(); else scene = s; })
    .catch((err) => console.warn("Sieve: 3D strip unavailable", err));
  return () => { dead = true; scene?.dispose(); };
}
