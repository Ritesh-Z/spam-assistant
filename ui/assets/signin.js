// ---------------------------------------------------------------------------
// "Connect Gmail" button: opens Google's sign-in in a centred popup and
// waits on this page. src/oauth_popup.py receives Google's reply on a local
// port; we poll its /status and tell Python when the sign-in is done.
// data = { auth_url, status_url }
// ---------------------------------------------------------------------------
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector(".signin");
  const btn = root.querySelector("[data-go]");
  const msg = root.querySelector("[data-msg]");
  let popup = null, timer = 0;

  const say = (text, kind = "") => { msg.textContent = text; msg.className = "msg " + kind; };

  function poll() {
    clearInterval(timer);
    timer = setInterval(async () => {
      try {
        const r = await fetch(data.status_url, { cache: "no-store" });
        const s = await r.json();
        if (s.status === "done") {
          clearInterval(timer);
          try { popup?.close(); } catch (e) { /* closed already */ }
          say("Signed in. Loading your inbox…", "ok");
          root.classList.remove("busy");
          setTriggerValue("done", Date.now());
        } else if (s.status === "error") {
          clearInterval(timer);
          root.classList.remove("busy");
          say("Sign-in did not complete (" + (s.error || "cancelled") + "). Try again.", "err");
          setTriggerValue("retry", Date.now());
        }
      } catch (e) { /* listener restarting; keep polling */ }
    }, 900);
  }

  btn.addEventListener("click", () => {
    const w = 500, h = 640;
    const left = window.screenX + Math.max(0, (window.outerWidth - w) / 2);
    const top = window.screenY + Math.max(0, (window.outerHeight - h) / 2);
    popup = window.open(data.auth_url, "sieve_google_signin",
      `popup=yes,width=${w},height=${h},left=${left},top=${top}`);
    root.classList.add("busy");
    if (!popup) {
      say("Your browser blocked the popup. Allow popups for this page, or ", "err");
      const a = document.createElement("a");
      a.href = data.auth_url; a.target = "_blank"; a.rel = "noopener"; a.textContent = "open sign-in in a new tab";
      msg.append(a);
    } else {
      popup.focus();
      say("Waiting for you to finish signing in in the popup…");
    }
    poll();
  });

  return () => clearInterval(timer);
}
