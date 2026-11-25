/* Stallboard: the extras that need a script. Every page already lists everything and reads without this file.
   It adds search, filters, sorting and the "Starboard you have" mark on the home page, the colour switch, tabs and the
   install dialog on a plug-in page, and the checking form on Submit. No requests are made. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const list = (a) => (a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]);
  const ver = (s) => String(s || "").split(".").map((x) => parseInt(x, 10) || 0);
  const cmp = (a, b) => { const x = ver(a), y = ver(b); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0); } return 0; };

  /* Everything marked js-only is hidden until a script runs. */
  $$(".js-only").forEach((el) => { el.hidden = false; });

  /* ---------- Display and accessibility ----------
     The design system's components.js applies each choice at once and keeps the set in this browser (localStorage,
     inside try/catch). This adds a spoken line for each change, in the panel's live region. */
  function initDisplay() {
    const form = $("#display-form"), say = $("#display-status");
    if (!form || !say) return;
    const names = { theme: "Theme", text: "Text size", motion: "Reduce motion", contrast: "High contrast", underline: "Underline links", spacing: "Wider text spacing", shadows: "Remove drop shadows" };
    const words = { system: "Match device", light: "Light", dark: "Dark", device: "Match device", on: "Active", off: "Inactive" };
    form.addEventListener("change", (e) => {
      const el = e.target.closest("[data-display]"); if (!el) return;
      const k = el.dataset.display;
      say.textContent = el.type === "checkbox" ? `${names[k]} ${el.checked ? "on" : "off"}.` : `${names[k]}: ${k === "text" ? el.value + "%" : words[el.value] || el.value}.`;
    });
    const reset = $("[data-display-reset]");
    if (reset) reset.addEventListener("click", () => { say.textContent = "All display choices are back to the defaults."; });
  }

  /* ---------- Search: every word typed must appear in a plug-in's name, summary, category or tags ---------- */
  const words = (li) => (li.dataset.search || li.textContent).toLowerCase().replace(/\s+/g, " ");
  const matches = (hay, t) => !t || t.split(/\s+/).every((w) => hay.includes(w));

  /* ---------- A category page: the same search, over this category only ---------- */
  function category() {
    const mediaSel = $("#media");
    const items = $$("#cat-list > li"), q = $("#q"), status = $("#results-status"), none = $("#none"), total = items.length;
    const text = new Map(items.map((li) => [li, words(li)]));
    const run = () => {
      const t = q.value.trim().toLowerCase();
      let n = 0;
      const m = mediaSel.value, mt = m ? ` that work with ${mediaSel.options[mediaSel.selectedIndex].text}` : "";
      items.forEach((li) => { const hit = matches(text.get(li), t) && (!m || li.dataset.media.split(" ").includes(m)); li.hidden = !hit; if (hit) n++; });
      status.textContent = t || m ? (n ? `Showing ${n} of ${total} plug-ins${mt}${t ? ` matching "${q.value.trim()}"` : ""}.` : `No plug-ins${mt} match${t ? ` "${q.value.trim()}"` : ""}.`) : `Showing all ${total} plug-ins.`;
      none.hidden = n > 0;
    };
    const sortBox = $("#sort"), list = $("#cat-list"), original = [...items];
    const order = () => {
      const how = sortBox.value, key = how === "mem" ? "mem" : "testmem";
      const sorted = [...original];
      if (how !== "name") sorted.sort((a, b) => { const x = a.dataset[key] === "" ? Infinity : +a.dataset[key], y = b.dataset[key] === "" ? Infinity : +b.dataset[key]; return (x === y ? 0 : x - y) || a.dataset.name.localeCompare(b.dataset.name); });
      sorted.forEach((li) => list.appendChild(li));
    };
    sortBox.addEventListener("change", () => { order(); run(); status.textContent += { name: "", mem: " Sorted by memory at rest, lowest first; those not measured yet come last.", testmem: " Sorted by memory on the test server, lowest first; those not measured yet come last." }[sortBox.value]; });
    q.addEventListener("input", run);
    mediaSel.addEventListener("change", run);
    $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
    $("#clear").addEventListener("click", () => { q.value = ""; mediaSel.value = ""; run(); q.focus(); });
    run();
  }

  /* ---------- Home ---------- */
  function home() {
    const all = $("#all-list"), items = $$("#all-list > li");
    const total = items.length;
    const mediaSel = $("#media");
    const q = $("#q"), status = $("#results-status"), chipsBox = $("#kind-chips"), sortBox = $("#sort"), mySb = $("#mysb");
    const text = new Map(items.map((li) => [li, words(li)]));
    const original = [...items];
    let kind = "";

    const mark = () => {
      const mine = mySb.value;
      $$(".tile").forEach((li) => {
        const chip = $(".sb-need", li); if (!chip) return;
        if (!chip.dataset.plain) chip.dataset.plain = chip.textContent;
        const need = li.dataset.sb;
        const tooOld = mine && need && cmp(mine, need) < 0;
        chip.textContent = tooOld ? "Needs a newer Starboard than yours: " + chip.dataset.plain.replace(/^Needs /, "") : chip.dataset.plain;
        if (tooOld) chip.setAttribute("data-tone", "danger"); else chip.removeAttribute("data-tone");
      });
    };
    const order = () => {
      const how = sortBox.value;
      const sorted = [...original];
      if (how === "mem") sorted.sort((a, b) => { const x = a.dataset.mem === "" ? Infinity : +a.dataset.mem, y = b.dataset.mem === "" ? Infinity : +b.dataset.mem; return (x === y ? 0 : x - y) || a.dataset.name.localeCompare(b.dataset.name); });
      if (how === "testmem") sorted.sort((a, b) => { const x = a.dataset.testmem === "" ? Infinity : +a.dataset.testmem, y = b.dataset.testmem === "" ? Infinity : +b.dataset.testmem; return (x === y ? 0 : x - y) || a.dataset.name.localeCompare(b.dataset.name); });
      if (how === "new") sorted.sort((a, b) => (b.dataset.date || "").localeCompare(a.dataset.date || "") || a.dataset.name.localeCompare(b.dataset.name));
      sorted.forEach((li) => all.appendChild(li));
    };
    const run = (announceSort) => {
      const t = q.value.trim().toLowerCase();
      let n = 0;
      items.forEach((li) => {
        const hit = (!kind || li.dataset.kind === kind) && matches(text.get(li), t) && (!mediaSel.value || li.dataset.media.split(" ").includes(mediaSel.value));
        li.hidden = !hit; if (hit) n++;
      });
      $$("button", chipsBox).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.kind === kind)));
      const sortWords = { name: "", mem: " Sorted by memory at rest, lowest first; those not measured yet come last.", testmem: " Sorted by memory on the test server, lowest first; those not measured yet come last.", new: " Sorted newest first." }[sortBox.value];
      status.textContent = (n ? `Showing ${n} of ${total} plug-ins${kind ? " in " + kind : ""}${mediaSel.value ? " that work with " + mediaSel.options[mediaSel.selectedIndex].text : ""}${t ? ` matching "${q.value.trim()}"` : ""}.` : `No plug-ins match${t ? ` "${q.value.trim()}"` : ""}${kind ? " in " + kind : ""}. Clear the search or choose All.`) + (announceSort ? sortWords : "");
      $("#none").hidden = n > 0;
    };
    chipsBox.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { kind = b.dataset.kind; run(); } });
    q.addEventListener("input", () => run());
    mediaSel.addEventListener("change", () => run());
    sortBox.addEventListener("change", () => { order(); run(true); });
    mySb.addEventListener("change", () => { mark(); status.textContent = mySb.value ? `Plug-ins that need a newer Starboard than ${mySb.value} are marked in words.` : "The marks for Starboard versions are off."; });
    $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); run(); $("#all-plug-ins").scrollIntoView(); $("#all-h").focus(); });
    $("#clear").addEventListener("click", () => { q.value = ""; kind = ""; mediaSel.value = ""; run(); q.focus(); });

    /* Made for you (a demo): the tiles are copies of the ones in the list below. */
    const checks = $("#apps-run"), mfyList = $("#mfy-list"), mfyStatus = $("#mfy-status");
    const draw = () => {
      const sel = $$("input", checks).filter((i) => i.checked).map((i) => i.value);
      const hits = original.map((li) => ({ li, w: li.dataset.works.split("|").filter((a) => a && sel.includes(a)) })).filter((x) => x.w.length)
        .sort((a, b) => b.w.length - a.w.length || a.li.dataset.name.localeCompare(b.li.dataset.name));
      mfyList.innerHTML = "";
      hits.slice(0, 6).forEach((x) => {
        const c = x.li.cloneNode(true); c.hidden = false; c.removeAttribute("data-id");
        $(".tile__pitch", c).insertAdjacentHTML("afterend", `<p class="tile__why"><svg class="i" aria-hidden="true" focusable="false"><use href="#i-plug"/></svg><span>Works with ${esc(list(x.w))}</span></p>`);
        mfyList.appendChild(c);
      });
      mfyStatus.textContent = sel.length ? (hits.length ? `Showing ${Math.min(6, hits.length)} of ${hits.length} plug-ins that work with ${list(sel)}.` : "No plug-ins work with those apps yet.") : "Choose at least one app to get plug-ins for it.";
      mark();
    };
    checks.addEventListener("change", draw);
    order(); run(); mark();
  }

  /* ---------- A plug-in's page ---------- */
  function plugin() {
    const box = $(".tabs");
    if (box) {
      $$(".nojs-h", box).forEach((h) => { h.hidden = true; });
      $('[role="tablist"]', box).hidden = false;
    }
    $$("a[data-dialog]").forEach((a) => a.addEventListener("click", (e) => e.preventDefault()));
    const copy = $("#copy-manifest");
    if (copy) copy.addEventListener("click", async () => {
      let ok = false;
      try { await navigator.clipboard.writeText($("#manifest").textContent); ok = true; } catch (e) { /* clipboard may be blocked */ }
      $("#copy-status").textContent = ok ? "Copied." : "Select the address and copy it.";
    });
  }

  /* ---------- Submit ---------- */
  function submit() {
    const form = $("#submit-form");
    const SC = window.SharedComponents;
    if (!form || !SC) return;
    const check = () => {
      const errors = [];
      const addr = $("#address").value.trim();
      if (!addr) errors.push({ field: "address", message: "Enter the address of your plug-in." });
      else if (!/^https:\/\/[^\s/]+\.[^\s/]+\/?\S*$/i.test(addr)) errors.push({ field: "address", message: "Start the address with https:// and give the whole web address, such as https://raw.githubusercontent.com/your-name/your-plug-in/main/starboard-plugin.json." });
      if (!$("#mine").checked) errors.push({ field: "mine", message: "Tick the box to say the plug-in is yours to share." });
      return errors;
    };
    form.addEventListener("submit", (e) => {
      const errors = check();
      if (errors.length) { e.preventDefault(); SC.showErrors(form, errors); return; }
      SC.clearErrors(form);
      /* The form itself opens GitHub's own form in a new tab, with the address filled in. Nothing is sent from here. */
      const name = $("#who").value.trim();
      $("#success-name").textContent = name ? `Thank you, ${name}` : "Thank you";
      $("#success-addr").textContent = $("#address").value.trim();
      $("#form-area").hidden = true;
      $("#success").hidden = false;
      const first = $("#next li");
      first.setAttribute("aria-current", "step");
      if (!first.querySelector(".chip")) first.insertAdjacentHTML("beforeend", '<span class="chip"><svg class="i" aria-hidden="true" focusable="false"><use href="#i-clock"/></svg>You are here</span>');
      document.title = "Ready to post: Submit a plug-in | Stallboard";
      $("#success-h").focus();
    });
    $("#again").addEventListener("click", () => { form.reset(); $("#success").hidden = true; $("#form-area").hidden = false; document.title = "Submit a plug-in | Stallboard"; $("#address").focus(); });
  }

  initDisplay();
  const page = document.body.dataset.page;
  if (page === "home") home();
  if (page === "category") category();
  if (page === "plugin") plugin();
  if (page === "submit") submit();
})();
