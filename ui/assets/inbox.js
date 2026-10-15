// ---------------------------------------------------------------------------
// Inbox email list: all rows drawn by one component instead of ~250
// Streamlit widgets, so page changes stay fast. Clicking a row sends its id
// back to Python as the "open" trigger.
// data = { rows: [{id, subject, sender, label, confidence, note, alert}], colors: {...} }
// ---------------------------------------------------------------------------
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const list = parentElement.querySelector(".inbox");
  list.replaceChildren();
  if (!data.rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No emails match this filter.";
    list.append(empty);
  }
  list.onkeydown = (e) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    const rows = [...list.querySelectorAll(".row")];
    const i = rows.indexOf(parentElement.activeElement ?? document.activeElement);
    const next = rows[Math.max(0, Math.min(rows.length - 1, (i < 0 ? -1 : i) + (e.key === "ArrowDown" ? 1 : -1)))];
    if (next) { e.preventDefault(); next.focus(); next.scrollIntoView({ block: "nearest" }); }
  };
  for (const r of data.rows) {
    const row = document.createElement("button");
    row.className = "row";
    row.style.setProperty("--c", data.colors[r.label]);
    row.innerHTML =
      '<span class="bar"></span><span class="txt"><span class="s"></span><span class="f"></span></span>' +
      '<span class="tags"><span class="flag" hidden></span>' +
      '<span class="badge"><i></i><span class="l"></span> <b></b></span></span><span class="go">open ↗</span>';
    if (r.alert) {
      const f = row.querySelector(".flag");
      f.hidden = false;
      f.textContent = "⚑ " + r.alert.toUpperCase();
      row.classList.add("alert");
    }
    row.querySelector(".s").textContent = r.subject;
    row.querySelector(".f").textContent = r.sender;
    row.querySelector(".l").textContent = r.label.toUpperCase();
    row.querySelector("b").textContent =
      r.confidence == null ? (r.note || "") : Math.round(r.confidence * 100) + "%";
    row.addEventListener("click", () => setTriggerValue("open", r.id));
    list.append(row);
  }
}
