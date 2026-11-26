/* Stallboard: the extras that need a script. Every page already lists everything and reads without this file.
   It adds search, filters, sorting and the "Starboard you have" mark on the home and category pages, the colour switch, tabs and the
   install dialog on a plug-in page, and the checking form on Submit. No requests are made. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
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
  const X = '<svg class="i" aria-hidden="true" focusable="false"><use href="#i-x"/></svg>';

  /* ---------- The shelf: the home page and each category page ----------
     One search, the Works with filter, the Starboard you have, and the sort, over the cards on the page. The categories are links and
     work without this file. On a phone the filters are a sheet that the Filters button opens (Works with first); the filters that
     are on are shown as removable chips under the search, so nothing is hidden behind the sheet. */
  function shelf() {
    const list = $("#all-list") || $("#cat-list");
    if (!list) return;
    const items = $$(":scope > li", list), total = items.length, original = [...items];
    const q = $("#q"), status = $("#results-status"), none = $("#none"), sortBox = $("#sort"), mySb = $("#mysb"), active = $("#active");
    const panel = $("#filters"), openBtn = $("#filters-open"), closeBtn = $("#filters-close"), count = $("#filters-n"), heading = $("#all-h") || $("#results-h");
    const radios = $$('input[name="media"]');
    const text = new Map(items.map((li) => [li, words(li)]));
    const media = () => (radios.find((r) => r.checked) || { value: "" }).value;
    const mediaName = () => { const r = radios.find((x) => x.checked); return r && r.value ? r.nextElementSibling.textContent : ""; };

    const mark = () => {
      const mine = mySb.value;
      $$(".sb-need", list).forEach((chip) => {
        const li = chip.closest("li");
        if (!chip.dataset.plain) chip.dataset.plain = chip.textContent;
        const need = li.dataset.sb;
        const tooOld = mine && need && cmp(mine, need) < 0;
        chip.textContent = tooOld ? "Needs a newer Starboard: " + chip.dataset.plain.replace(/^Needs Starboard /, "") : chip.dataset.plain;
        if (tooOld) chip.setAttribute("data-tone", "danger"); else chip.removeAttribute("data-tone");
      });
    };
    const num = (v) => (v === "" || v === undefined ? Infinity : +v);
    const order = () => {
      const how = sortBox.value, sorted = [...original];
      if (how === "mem" || how === "testmem") sorted.sort((a, b) => { const x = num(a.dataset[how]), y = num(b.dataset[how]); return (x === y ? 0 : x - y) || a.dataset.name.localeCompare(b.dataset.name); });
      if (how === "new") sorted.sort((a, b) => (b.dataset.date || "").localeCompare(a.dataset.date || "") || a.dataset.name.localeCompare(b.dataset.name));
      sorted.forEach((li) => list.appendChild(li));
    };
    const sortWords = { name: "", mem: " Sorted by memory at rest, lowest first; those not measured yet come last.", testmem: " Sorted by memory on the test server, lowest first; those not measured yet come last.", new: " Sorted newest first." };
    const chips = () => {
      const t = q.value.trim(), m = mediaName(), s = mySb.value;
      const c = [];
      if (t) c.push(["q", `Search: ${t}`]);
      if (m) c.push(["media", `Works with ${m}`]);
      if (s) c.push(["sb", `Starboard ${s}`]);
      active.innerHTML = c.map(([k, w]) => `<li><button type="button" data-clear="${k}" aria-label="Remove filter: ${esc(w)}">${esc(w)} ${X}</button></li>`).join("");
      active.hidden = !c.length;
      count.textContent = c.length ? ` (${c.length})` : "";
      return c.length;
    };
    const run = (announceSort) => {
      const t = q.value.trim().toLowerCase(), m = media();
      let n = 0;
      items.forEach((li) => { const hit = matches(text.get(li), t) && (!m || li.dataset.media.split(" ").includes(m)); li.hidden = !hit; if (hit) n++; });
      const on = chips();
      const where = m ? ` that work with ${mediaName()}` : "";
      status.textContent = (on ? (n ? `Showing ${n} of ${total} plug-ins${where}${t ? ` matching "${q.value.trim()}"` : ""}.` : `No plug-ins${where} match${t ? ` "${q.value.trim()}"` : ""}. Clear the search or the filters.`) : `Showing all ${total} plug-ins.`) + (announceSort ? sortWords[sortBox.value] : "");
      none.hidden = n > 0;
      if (closeBtn) closeBtn.textContent = n ? `Show ${n} plug-in${n === 1 ? "" : "s"}` : "Show results";
    };

    /* The sheet (a phone): it is a dialog only while it is open, focus goes in and comes back, Tab stays inside, Escape closes. */
    const narrow = window.matchMedia("(max-width: 55.99rem)");
    const outside = () => $$(".top, .foot, .banner, .store-layout__main, .catnav, .skip-link");
    let backdrop = null;
    const openSheet = () => {
      if (!narrow.matches) return;
      panel.classList.add("is-open");
      panel.setAttribute("role", "dialog"); panel.setAttribute("aria-modal", "true");
      openBtn.setAttribute("aria-expanded", "true");
      backdrop = document.createElement("div"); backdrop.className = "sheet-backdrop"; backdrop.addEventListener("click", () => closeSheet());
      panel.before(backdrop);
      outside().forEach((e) => { e.inert = true; });
      (radios.find((r) => r.checked) || radios[0]).focus();
    };
    const closeSheet = (noFocus) => {
      if (!panel.classList.contains("is-open")) return;
      panel.classList.remove("is-open");
      panel.removeAttribute("role"); panel.removeAttribute("aria-modal");
      openBtn.setAttribute("aria-expanded", "false");
      if (backdrop) { backdrop.remove(); backdrop = null; }
      outside().forEach((e) => { e.inert = false; });
      if (!noFocus) openBtn.focus();
    };
    openBtn.addEventListener("click", openSheet);
    closeBtn.addEventListener("click", () => closeSheet());
    panel.addEventListener("keydown", (e) => {
      if (!panel.classList.contains("is-open")) return;
      if (e.key === "Escape") { e.preventDefault(); closeSheet(); return; }
      if (e.key !== "Tab") return;
      const f = $$("input, select, button", panel).filter((x) => !x.disabled && x.offsetParent !== null && !(x.type === "radio" && !x.checked));
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    narrow.addEventListener("change", () => closeSheet(true));
    /* The category list is open on a wide screen and folded on a phone. */
    const fold = $("#cat-fold"), wide = window.matchMedia("(min-width: 56rem)");
    const setFold = () => { if (fold) fold.open = wide.matches; };
    wide.addEventListener("change", setFold); setFold();

    const clear = (what) => {
      if (what === "q" || what === "all") q.value = "";
      if (what === "media" || what === "all") radios[0].checked = true;
      if (what === "sb" || what === "all") { mySb.value = ""; mark(); }
    };
    active.addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      clear(b.dataset.clear); run();
      const next = $("button", active); (next || heading).focus();
    });
    q.addEventListener("input", () => run());
    radios.forEach((r) => r.addEventListener("change", () => run()));
    sortBox.addEventListener("change", () => { order(); run(true); });
    mySb.addEventListener("change", () => { mark(); run(); status.textContent = mySb.value ? `Plug-ins that need a newer Starboard than ${mySb.value} are marked in words.` : "The marks for Starboard versions are off."; });
    $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); run(); heading.scrollIntoView(); heading.focus(); });
    $("#clear").addEventListener("click", () => { clear("all"); run(); q.focus(); });
    $("#clear-filters").addEventListener("click", () => { clear("all"); run(); status.textContent += " The filters are cleared."; });
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
  if (page === "home" || page === "category") shelf();
  if (page === "plugin") plugin();
  if (page === "submit") submit();
})();
