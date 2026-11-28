// The accessibility and behaviour checks. Runs inside the Playwright image (tools/run.sh check):
//   env SITE=/site/site (the built site), AXE=/axe/axe.min.js, OUT=/out, MODE=check|shots
// Serves the built site at /stallboard/ (as GitHub Pages does) and fails (exit 1) on any violation.
import { chromium } from "playwright";
import fs from "fs";
import http from "http";
import path from "path";

const SITE = process.env.SITE || "/site/site";
const AXE = fs.readFileSync(process.env.AXE || "/axe/axe.min.js", "utf8");
const OUT = process.env.OUT || "/out";
const MODE = process.env.MODE || "check";
const PREFIX = "/stallboard/";
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2", ".xml": "application/xml", ".txt": "text/plain" };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (!p.startsWith(PREFIX)) { res.writeHead(404); res.end("not found"); return; }
  p = p.slice(PREFIX.length) || "index.html";
  let file = path.join(SITE, p);
  if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { "content-type": TYPES[".html"] }); res.end(fs.readFileSync(path.join(SITE, "404.html"))); return;
  }
  res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" }); res.end(fs.readFileSync(file));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}${PREFIX}`;

const pages = [
  ["home", "index.html"], ["plugin", "plugins/audio-description.html"], ["plugin-measured", "plugins/direct-play.html"], ["plugin-app", "plugins/calibre-web.html"],
  ["starboard", "starboard.html"], ["reelix", "reelix.html"], ["category", "category/jellyfin.html"], ["categories", "category/index.html"], ["plugin-gallery", "plugins/library-cleanup.html"], ["submit", "submit.html"], ["reviewed", "what-reviewed-means.html"],
  ["accessibility", "accessibility.html"], ["privacy", "privacy.html"], ["not-found", "no-such-page.html"],
];
const browser = await chromium.launch();
const results = [];
const failures = [];
const tags = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"];
const fail = (m) => { failures.push(m); };

async function open(ctx, file, theme) {
  const page = await ctx.newPage();
  const errs = [], reqs = [];
  page.on("pageerror", (e) => errs.push(String(e)));
  page.on("console", (m) => m.type() === "error" && !(file.startsWith("no-such") && /404/.test(m.text())) && errs.push(m.text()));
  page.on("request", (r) => { const u = r.url(); if (!u.startsWith(BASE) && !u.startsWith("data:") && !u.startsWith("blob:")) reqs.push(u); });
  const resp = await page.goto(BASE + file);
  await page.evaluate((t) => { document.documentElement.dataset.theme = t; }, theme);
  if (MODE === "shots") { await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 40)); } window.scrollTo(0, 0); }); await page.waitForTimeout(300); }
  await page.waitForTimeout(250);
  page._errs = errs; page._reqs = reqs; page._status = resp.status();
  return page;
}
async function axeRun(page) {
  await page.evaluate(AXE);
  return await page.evaluate(async (tags) => {
    const r = await axe.run(document, { runOnly: { type: "tag", values: tags } });
    return { v: r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, nodes: v.nodes.slice(0, 4).map((n) => n.target.join(" ") + " :: " + (n.failureSummary || "").split("\n").slice(0, 3).join(" | ")) })), passes: r.passes.length, incomplete: r.incomplete.map((i) => i.id + ":" + i.nodes.length) };
  }, tags);
}
const record = (cfg, name, r, page, extra = {}) => {
  results.push({ cfg, page: name, violations: r.v, passes: r.passes, incomplete: r.incomplete, errors: page._errs, external: page._reqs, ...extra });
  for (const v of r.v) fail(`axe ${cfg} / ${name}: ${v.id} (${v.n}) ${v.nodes[0]}`);
  if (page._errs.length) fail(`page errors ${cfg} / ${name}: ${page._errs.slice(0, 2).join(" ; ")}`);
  if (page._reqs.length) fail(`outside requests ${cfg} / ${name}: ${page._reqs.slice(0, 3).join(" ")}`);
};

if (MODE === "check") {
  const configs = [
    ["light-1280", { viewport: { width: 1280, height: 900 } }, "light"],
    ["dark-1280", { viewport: { width: 1280, height: 900 } }, "dark"],
    ["forced-1280", { viewport: { width: 1280, height: 900 }, forcedColors: "active" }, "light"],
    ["phone-375-light", { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true }, "light"],
    ["phone-375-dark", { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true }, "dark"],
  ];
  for (const [cname, opts, theme] of configs) {
    const ctx = await browser.newContext(opts);
    for (const [pname, file] of pages) {
      const page = await open(ctx, file, theme);
      if (pname === "not-found" ? page._status !== 404 : page._status !== 200) fail(`status ${page._status} for ${file}`);
      record(cname, pname, await axeRun(page), page);
      if (pname === "submit") {
        await page.click('button[type="submit"]'); await page.waitForTimeout(200);
        const focus = await page.evaluate(() => document.activeElement.className);
        record(cname, "submit-errors", await axeRun(page), page, { focus });
        if (!/error-summary/.test(focus)) fail(`submit errors: focus did not move to the error summary (${focus})`);
        await page.fill("#address", "https://raw.githubusercontent.com/someone/their-plug-in/main/starboard-plugin.json"); await page.check("#mine");
        await page.evaluate(() => { document.getElementById("submit-form").addEventListener("submit", (e) => e.preventDefault(), { once: true }); });
        await page.click('button[type="submit"]'); await page.waitForTimeout(200);
        const f3 = await page.evaluate(() => document.activeElement.id);
        record(cname, "submit-success", await axeRun(page), page, { focus: f3 });
        if (f3 !== "success-h") fail(`submit success: focus is on ${f3}, not the heading`);
      }
      if (pname === "home" || pname.startsWith("plugin") || pname === "starboard") {
        await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 30)); } window.scrollTo(0, 0); });
        await page.waitForTimeout(300);
        const broken = await page.evaluate(() => [...document.images].filter((i) => !(i.complete && i.naturalWidth > 0)).map((i) => i.getAttribute("src")));
        if (broken.length) fail(`${cname} / ${pname}: pictures that did not load: ${broken.slice(0, 4).join(", ")}`);
      }
      if (pname === "home") {
        // Snaglist still works under the Content-Security-Policy: its button opens its window.
        await page.getByRole("button", { name: /Send feedback/ }).first().click(); await page.waitForTimeout(400);
        const snag = await page.evaluate(() => [...document.querySelectorAll("snag-list, [class*=sl-], [role=dialog]")].some((e) => e.offsetParent !== null || e.tagName === "SNAG-LIST") && !!(document.querySelector("snag-list")?.shadowRoot?.querySelector("[role=dialog],dialog,.sl-panel") || document.querySelector("[role=dialog]")));
        if (!snag) fail(`${cname}: Snaglist did not open under the Content-Security-Policy`);
        await page.keyboard.press("Escape"); await page.waitForTimeout(200);
        await page.fill("#q", "blind"); await page.waitForTimeout(100);
        const tagHit = await page.evaluate(() => [...document.querySelectorAll("#all-list > li:not([hidden])")].map((l) => l.dataset.id));
        if (!tagHit.includes("audio-description-tracks") || !tagHit.includes("audio-description")) fail(`${cname}: searching a tag found nothing`);
        if (!/Showing \d+ of \d+/.test(await page.evaluate(() => document.getElementById("results-status").textContent))) fail(`${cname}: home search count not announced`);
        await page.fill("#q", ""); await page.waitForTimeout(100);
        const phone = (page.viewportSize()?.width || 1280) < 896;
        if (phone) {
          // The filter sheet: Filters opens it, focus goes to Works with first, Tab stays inside, Escape closes it and focus returns.
          await page.click("#filters-open"); await page.waitForTimeout(150);
          const sheet = await page.evaluate(() => ({ role: document.getElementById("filters").getAttribute("role"), modal: document.getElementById("filters").getAttribute("aria-modal"), inside: !!document.activeElement.closest("#filters"), name: document.activeElement.name, exp: document.getElementById("filters-open").getAttribute("aria-expanded") }));
          if (sheet.role !== "dialog" || sheet.modal !== "true" || !sheet.inside || sheet.name !== "media" || sheet.exp !== "true") fail(`${cname}: the filter sheet did not open with focus on Works with ${JSON.stringify(sheet)}`);
          record(cname, "home-filter-sheet-open", await axeRun(page), page);
          for (let i = 0; i < 12; i++) await page.keyboard.press("Tab");
          if (!(await page.evaluate(() => !!document.activeElement.closest("#filters")))) fail(`${cname}: Tab left the filter sheet`);
          await page.keyboard.press("Escape"); await page.waitForTimeout(150);
          const back = await page.evaluate(() => ({ id: document.activeElement.id, role: document.getElementById("filters").getAttribute("role"), shown: getComputedStyle(document.getElementById("filters")).display }));
          if (back.id !== "filters-open" || back.role || back.shown !== "none") fail(`${cname}: Escape did not close the filter sheet and return focus ${JSON.stringify(back)}`);
          await page.click("#filters-open"); await page.waitForTimeout(100);
          await page.getByLabel("Plex", { exact: true }).check(); await page.waitForTimeout(100);
          await page.click("#filters-close"); await page.waitForTimeout(150);
          if ((await page.evaluate(() => document.activeElement.id)) !== "filters-open") fail(`${cname}: Show results did not return focus to Filters`);
        } else {
          await page.getByLabel("Jellyfin", { exact: true }).check(); await page.waitForTimeout(100);
        }
        const shownMedia = await page.evaluate(() => [...document.querySelectorAll("#all-list > li:not([hidden])")].every((l) => l.dataset.media.split(" ").includes(document.querySelector('input[name=media]:checked').value)));
        if (!shownMedia) fail(`${cname}: the Works with filter shows a plug-in that does not work with it`);
        const chipsOn = await page.evaluate(() => [...document.querySelectorAll("#active button")].map((b) => b.textContent.trim()));
        if (chipsOn.length !== 1 || !/^Works with /.test(chipsOn[0])) fail(`${cname}: the active filter is not shown as a removable chip ${JSON.stringify(chipsOn)}`);
        if (!/that work with/.test(await page.evaluate(() => document.getElementById("results-status").textContent))) fail(`${cname}: the filtered count is not announced`);
        record(cname, "home-filtered", await axeRun(page), page);
        await page.click("#active button"); await page.waitForTimeout(100);
        if ((await page.evaluate(() => document.querySelectorAll("#all-list > li:not([hidden])").length)) !== 34) fail(`${cname}: removing the chip did not bring every plug-in back`);
        if (!(await page.evaluate(() => document.getElementById("active").hidden))) fail(`${cname}: the chip list is still shown when nothing is filtered`);
        if (phone) { await page.click("#filters-open"); await page.waitForTimeout(100); }
        await page.selectOption("#sort", "mem"); await page.waitForTimeout(100);
        record(cname, "home-sorted", await axeRun(page), page);
        const first = await page.evaluate(() => [...document.querySelectorAll("#all-list > li:not([hidden])")].slice(0, 3).map((l) => l.dataset.id));
        if (!first.length) fail("home sorted by memory: nothing shown");
        // The select lists only the newest releases, so the version to pick comes from the page, never from a fixed number.
        // Pick the oldest one listed and expect exactly the plug-ins whose first working Starboard is newer than it.
        const oldest = await page.evaluate(() => [...document.querySelectorAll("#mysb option")].map((o) => o.value).filter(Boolean).pop());
        if (!oldest) fail("home: the Starboard version select lists no versions");
        await page.selectOption("#mysb", oldest); await page.waitForTimeout(100);
        if (phone) { await page.click("#filters-close"); await page.waitForTimeout(100); }
        const marked = await page.evaluate(() => document.querySelectorAll('.sb-need[data-tone="danger"]').length);
        const expected = await page.evaluate((mine) => {
          const n = (v) => v.split(".").map(Number);
          const older = (a, b) => { const x = n(a), y = n(b); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) < (y[i] || 0); } return false; };
          return [...document.querySelectorAll("#all-list > li[data-sb]")].filter((l) => l.dataset.sb && older(mine, l.dataset.sb)).length;
        }, oldest);
        if (!expected) fail(`home: no plug-in needs a newer Starboard than ${oldest}, so the marking cannot be checked`);
        else if (marked !== expected) fail(`home: ${marked} plug-ins are marked as needing a newer Starboard than ${oldest}, expected ${expected}`);
        record(cname, "home-marked", await axeRun(page), page);
      }
      if (pname === "category") {
        const total = await page.evaluate(() => document.querySelectorAll("#cat-list > li").length);
        const say = async () => page.evaluate(() => document.getElementById("results-status").textContent);
        if (!/^Showing all \d+ plug-ins/.test(await say())) fail(`${cname}: category count not announced at start: ${await say()}`);
        await page.fill("#q", "jellyfin direct"); await page.waitForTimeout(100);
        const shown = await page.evaluate(() => [...document.querySelectorAll("#cat-list > li")].filter((l) => !l.hidden).length);
        if (shown !== 1 || !/Showing 1 of/.test(await say())) fail(`${cname}: category search "jellyfin direct" showed ${shown}: ${await say()}`);
        record(cname, "category-searched", await axeRun(page), page);
        await page.fill("#q", "zzzz"); await page.waitForTimeout(100);
        if (await page.evaluate(() => document.getElementById("none").hidden)) fail(`${cname}: category search with no match shows no message`);
        if (!(await page.evaluate(() => document.getElementById("results-status").getAttribute("role") === "status"))) fail(`${cname}: the count is not a live region`);
        record(cname, "category-none", await axeRun(page), page);
        await page.click("#clear"); await page.waitForTimeout(100);
        if ((await page.evaluate(() => document.activeElement.id)) !== "q") fail(`${cname}: focus did not return to the search box after Clear`);
        if (total < 1) fail("category page lists nothing");
      }
      if (pname === "plugin") {
        await page.click('[data-dialog="install-dialog"]'); await page.waitForTimeout(200);
        record(cname, "plugin-dialog", await axeRun(page), page, { focus: await page.evaluate(() => document.activeElement.getAttribute("aria-label") || document.activeElement.textContent.trim().slice(0, 30)) });
      }
      await page.close();
    }
    await ctx.close();
  }
  // The full matrix the Shelf design is held to: light, dark, high contrast and forced colours, each at 1280, 1280 with 175% text, 320 and 320 with 175% text.
  {
    const modes = [["light", { theme: "light" }, {}], ["dark", { theme: "dark" }, {}], ["high-contrast", { theme: "light", contrast: true }, {}], ["forced", { theme: "light" }, { forcedColors: "active" }]];
    const sizes = [["1280", 1280, 900, false], ["1280-175", 1280, 900, true], ["320", 320, 700, false], ["320-175", 320, 700, true]];
    for (const [mname, prefs, extra] of modes) for (const [sname, w, h, big] of sizes) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, ...extra });
      await ctx.addInitScript((p) => { try { localStorage.setItem("stallboard-display", JSON.stringify(p)); } catch (e) { /* fine */ } }, big ? { ...prefs, text: "175" } : prefs);
      for (const [pname, file] of pages) {
        const page = await ctx.newPage(); const errs = [];
        page.on("pageerror", (e) => errs.push(String(e)));
        await page.goto(BASE + file); await page.waitForTimeout(250);
        page._errs = errs; page._reqs = [];
        record(`matrix-${mname}-${sname}`, pname, await axeRun(page), page);
        const o = await page.evaluate(() => ({ s: document.documentElement.scrollWidth, c: document.documentElement.clientWidth }));
        if (o.s > o.c + 1) fail(`matrix-${mname}-${sname} / ${pname}: sideways scroll ${o.s} > ${o.c}`);
        await page.close();
      }
      await ctx.close();
    }
  }
  // Display and accessibility: the saved choices apply before paint; axe in every theme, at 175% text and on a phone with
  // everything on; and the panel itself: focus in, trap, Escape and return, the live region, saving and Reset.
  {
    const sets = [
      ["display-high-contrast", { theme: "light", contrast: true }, { width: 1280, height: 900 }],
      ["display-high-contrast-dark", { theme: "dark", contrast: true }, { width: 1280, height: 900 }],
      ["display-match-device", { theme: "system" }, { width: 1280, height: 900 }],
      ["display-175-text", { theme: "light", text: "175" }, { width: 1280, height: 900 }],
      ["display-175-text-dark", { theme: "dark", text: "175" }, { width: 1280, height: 900 }],
      ["display-phone-everything", { theme: "dark", text: "175", contrast: true, underline: true, spacing: true, shadows: true, motion: "on" }, { width: 375, height: 812 }],
      ["display-phone-light-175", { theme: "light", text: "175", spacing: true }, { width: 375, height: 812 }],
    ];
    for (const [cname, prefs, viewport] of sets) {
      const ctx = await browser.newContext({ viewport, isMobile: viewport.width < 500, hasTouch: viewport.width < 500 });
      await ctx.addInitScript((p) => { try { localStorage.setItem("stallboard-display", JSON.stringify(p)); } catch (e) { /* fine */ } }, prefs);
      for (const [pname, file] of [["home", "index.html"], ["categories", "category/index.html"], ["category", "category/jellyfin.html"], ["plugin-gallery", "plugins/library-cleanup.html"], ["submit", "submit.html"]]) {
        const page = await ctx.newPage();
        const errs = [], reqs = [];
        page.on("pageerror", (e) => errs.push(String(e)));
        page.on("request", (r) => { const u = r.url(); if (!u.startsWith(BASE) && !u.startsWith("data:") && !u.startsWith("blob:")) reqs.push(u); });
        await page.goto(BASE + file); await page.waitForTimeout(350);
        page._errs = errs; page._reqs = reqs;
        const st = await page.evaluate(() => ({ theme: document.documentElement.dataset.theme, cls: document.documentElement.className }));
        if (prefs.contrast && !/pref-contrast/.test(st.cls)) fail(`${cname}: high contrast was not applied on ${pname}`);
        if (prefs.text && !new RegExp("pref-text-" + prefs.text).test(st.cls)) fail(`${cname}: text size was not applied on ${pname}`);
        record(cname, pname, await axeRun(page), page);
        const o = await page.evaluate(() => ({ s: document.documentElement.scrollWidth, c: document.documentElement.clientWidth }));
        if (o.s > o.c + 1) fail(`${cname} / ${pname}: sideways scroll ${o.s} > ${o.c}`);
        if (pname === "home") {
          await page.click("#display-open"); await page.waitForTimeout(250);
          record(cname, "home-display-panel-open", await axeRun(page), page);
          const o2 = await page.evaluate(() => { const a = document.querySelector("#display-panel .side-panel").getBoundingClientRect(); return { r: a.right, w: window.innerWidth, l: a.left }; });
          if (o2.r > o2.w + 1 || o2.l < -1) fail(`${cname}: the Display panel does not fit the screen (${JSON.stringify(o2)})`);
        }
        await page.close();
      }
      await ctx.close();
    }
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + "index.html"); await page.waitForTimeout(300);
    const w = {};
    w.hiddenBefore = await page.evaluate(() => document.getElementById("display-panel").hidden);
    await page.focus("#display-open"); await page.keyboard.press("Enter"); await page.waitForTimeout(200);
    w.focusIn = await page.evaluate(() => !!document.activeElement.closest("#display-panel"));
    w.expanded = await page.evaluate(() => document.getElementById("display-open").getAttribute("aria-expanded"));
    for (let i = 0; i < 40; i++) await page.keyboard.press("Tab");
    w.trapped = await page.evaluate(() => !!document.activeElement.closest("#display-panel"));
    for (let i = 0; i < 40; i++) await page.keyboard.press("Shift+Tab");
    w.trappedBack = await page.evaluate(() => !!document.activeElement.closest("#display-panel"));
    await page.getByLabel("Dark", { exact: true }).check(); await page.waitForTimeout(100);
    w.dark = await page.evaluate(() => document.documentElement.dataset.theme);
    w.say1 = await page.evaluate(() => document.getElementById("display-status").textContent);
    await page.getByLabel("150%", { exact: true }).check(); await page.waitForTimeout(100);
    w.t150 = await page.evaluate(() => document.documentElement.classList.contains("pref-text-150"));
    w.say2 = await page.evaluate(() => document.getElementById("display-status").textContent);
    await page.getByRole("switch", { name: "High contrast" }).check(); await page.waitForTimeout(100);
    w.contrast = await page.evaluate(() => document.documentElement.classList.contains("pref-contrast"));
    w.say3 = await page.evaluate(() => document.getElementById("display-status").textContent);
    w.liveRole = await page.evaluate(() => document.getElementById("display-status").getAttribute("role"));
    w.saved = await page.evaluate(() => localStorage.getItem("stallboard-display"));
    w.cookies = (await ctx.cookies()).length;
    await page.keyboard.press("Escape"); await page.waitForTimeout(150);
    w.closed = await page.evaluate(() => document.getElementById("display-panel").hidden);
    w.focusBack = await page.evaluate(() => document.activeElement.id);
    await page.reload(); await page.waitForTimeout(300);
    w.persisted = await page.evaluate(() => [document.documentElement.dataset.theme, document.documentElement.classList.contains("pref-text-150"), document.documentElement.classList.contains("pref-contrast")]);
    await page.click("#display-open"); await page.waitForTimeout(200);
    w.restoredRadio = await page.evaluate(() => document.querySelector('input[data-display="text"][value="150"]').checked);
    await page.getByRole("button", { name: "Reset to defaults" }).click(); await page.waitForTimeout(150);
    w.reset = await page.evaluate(() => [document.documentElement.dataset.theme, document.documentElement.className.includes("pref-"), localStorage.getItem("stallboard-display")]);
    w.say4 = await page.evaluate(() => document.getElementById("display-status").textContent);
    await page.click(".side-panel-backdrop", { position: { x: 5, y: 5 } }); await page.waitForTimeout(150);
    w.backdropCloses = await page.evaluate(() => document.getElementById("display-panel").hidden);
    results.push({ cfg: "display-panel", page: "home", ...w });
    if (!w.hiddenBefore || !w.focusIn || w.expanded !== "true" || !w.trapped || !w.trappedBack) fail("Display panel: focus does not move in and stay in " + JSON.stringify(w));
    if (w.dark !== "dark" || !w.t150 || !w.contrast) fail("Display panel: choices do not apply at once " + JSON.stringify(w));
    if (!/Theme: Dark/.test(w.say1) || !/Text size: 150%/.test(w.say2) || !/High contrast on/.test(w.say3) || w.liveRole !== "status") fail("Display panel: the live region does not say what changed " + JSON.stringify([w.say1, w.say2, w.say3]));
    if (!w.saved || w.cookies) fail("Display panel: choices are not saved in the browser only " + JSON.stringify([w.saved, w.cookies]));
    if (!w.closed || w.focusBack !== "display-open") fail("Display panel: Escape does not close it and return focus " + JSON.stringify([w.closed, w.focusBack]));
    if (w.persisted[0] !== "dark" || !w.persisted[1] || !w.persisted[2] || !w.restoredRadio) fail("Display panel: choices are not kept after a reload " + JSON.stringify(w.persisted));
    if (w.reset[0] !== "light" || w.reset[1] || w.reset[2] !== null || !/defaults/.test(w.say4)) fail("Display panel: Reset to defaults does not reset " + JSON.stringify(w.reset));
    if (!w.backdropCloses) fail("Display panel: a press outside does not close it");
    // Storage blocked: the page still works and the panel still changes the page.
    const blocked = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await blocked.addInitScript(() => { Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); });
    const bp = await blocked.newPage(); const berrs = []; bp.on("pageerror", (e) => berrs.push(String(e)));
    await bp.goto(BASE + "index.html"); await bp.waitForTimeout(300);
    await bp.click("#display-open"); await bp.getByLabel("Dark", { exact: true }).check(); await bp.waitForTimeout(100);
    if ((await bp.evaluate(() => document.documentElement.dataset.theme)) !== "dark" || berrs.length) fail("Display panel: it breaks when storage is blocked " + berrs.join(" ; "));
    await blocked.close();
    await ctx.close();
  }
  // WCAG 1.4.12 text spacing: line height 1.5, paragraphs 2em apart, letters 0.12em, words 0.16em must lose nothing (no text cut off by a
  // box, no sideways scroll). Also at 320px wide with 175% text. And focus: a focused control is not cut off by a box with overflow
  // set, and nothing fixed (Snaglist's button, the skip link) sits on top of it.
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, bypassCSP: true }); // only so the test can add its own style
    const tight = [];
    for (const [pname, file] of pages) {
      for (const [label, w] of [["text spacing 1280", 1280], ["text spacing 320 + 175%", 320]]) {
        const page = await ctx.newPage(); await page.setViewportSize({ width: w, height: 900 });
        await page.goto(BASE + file); await page.waitForTimeout(150);
        await page.addStyleTag({ content: "* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; } p { margin-bottom: 2em !important; }" + (w === 320 ? " html { font-size: 175% !important; }" : "") });
        await page.waitForTimeout(150);
        const r = await page.evaluate(() => {
          const cut = [];
          for (const el of document.querySelectorAll("body *")) {
            const cs = getComputedStyle(el);
            if (["hidden", "clip"].includes(cs.overflowY) && el.scrollHeight > el.clientHeight + 2 && el.clientHeight > 0 && !el.closest("svg,.visually-hidden,dialog,snag-list,[class*=sl-]") && el.children.length === 0) cut.push((el.className || el.tagName).toString().slice(0, 40));
          }
          return { cut, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth };
        });
        tight.push({ label, page: pname, ...r });
        if (r.cut.length) fail(`${label} on ${pname}: text is cut off in ${r.cut.slice(0, 3).join(", ")}`);
        if (r.sw > r.cw + 1) fail(`${label} on ${pname}: sideways scroll ${r.sw} > ${r.cw}`);
        await page.close();
      }
    }
    results.push({ cfg: "text-spacing", rows: tight.length });
    for (const [pname, file] of pages) {
      const page = await open(ctx, file, "light");
      const problems = [];
      for (let i = 0; i < 90; i++) {
        await page.keyboard.press("Tab");
        const d = await page.evaluate(() => {
          const e = document.activeElement; if (!e || e === document.body) return null;
          if (e.closest("[class*=sl-],#snaglist-root,snag-list")) return { skip: true };
          const r = (e.getClientRects()[0] || e.getBoundingClientRect()); const out = [];
          for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
            const cs = getComputedStyle(a);
            if (/(hidden|clip)/.test(cs.overflowX + cs.overflowY)) { const b = a.getBoundingClientRect(); if (r.left - 3 < b.left - 1 && r.width < b.width || r.right + 3 > b.right + 1 && r.width < b.width) out.push("clipped by " + (a.className || a.tagName).toString().slice(0, 30)); }
          }
          const cx = Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1), cy = Math.min(Math.max(r.top + Math.min(r.height / 2, 10), 1), innerHeight - 1);
          const top = document.elementFromPoint(cx, cy);
          const covered = top && !(e === top || e.contains(top) || top.contains(e)) ? (top.className || top.tagName).toString().slice(0, 30) : "";
          return { n: (e.getAttribute("aria-label") || e.textContent.trim()).slice(0, 25), out, covered, same: e.id };
        });
        if (!d) break; if (d.skip) continue;
        if (d.out.length) problems.push(`${d.n}: ${d.out[0]}`);
        if (d.covered) problems.push(`${d.n}: covered by ${d.covered}`);
      }
      if (problems.length) fail(`focus on ${pname}: ${problems.slice(0, 4).join(" ; ")}`);
      await page.close();
    }
    await ctx.close();
  }
  // Without JavaScript: every page reads, the home page lists every plug-in, nothing is hidden that should show.
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, javaScriptEnabled: false });
    for (const [pname, file] of pages) {
      const page = await ctx.newPage();
      await page.goto(BASE + file);
      const info = await page.evaluate(() => ({ h1: document.querySelectorAll("h1").length, tiles: document.querySelectorAll("#all-list > li").length, visibleJsOnly: [...document.querySelectorAll(".js-only")].filter((e) => e.offsetParent !== null).length, text: document.body.innerText.length, panels: [...document.querySelectorAll('[role="tabpanel"]')].filter((e) => e.offsetParent !== null).length }));
      results.push({ cfg: "no-javascript", page: pname, ...info });
      if (info.h1 !== 1) fail(`no JS ${pname}: ${info.h1} h1`);
      if (pname === "home" && info.tiles < 30) fail(`no JS home: only ${info.tiles} plug-ins listed`);
      if (info.visibleJsOnly) fail(`no JS ${pname}: ${info.visibleJsOnly} script-only controls are visible`);
      if (pname.startsWith("plugin") && info.panels < 2) fail(`no JS ${pname}: the install steps are hidden`);
      await page.close();
    }
    await ctx.close();
  }
  // Text size and zoom: overflow
  const layout = [];
  for (const [label, w, fs, cls] of [["175% text 1280", 1280, "175%", "pref-text-175"], ["175% text 375", 375, "175%", "pref-text-175"], ["200% zoom (640 wide)", 640, "100%", ""], ["400% zoom (320 wide)", 320, "100%", ""], ["200% zoom plus 175% text (640)", 640, "175%", "pref-text-175"]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    for (const [pname, file] of pages) {
      const page = await open(ctx, file, "light");
      await page.evaluate(([fs, cls]) => { document.documentElement.style.fontSize = fs; if (cls) document.documentElement.classList.add(cls); }, [fs, cls]);
      await page.waitForTimeout(200);
      const o = await page.evaluate(() => {
        const de = document.documentElement; const bad = [];
        for (const el of document.querySelectorAll("body *")) { const r = el.getBoundingClientRect(); if (r.width && r.right > de.clientWidth + 1 && getComputedStyle(el).position !== "fixed" && !el.closest("svg,.visually-hidden,[hidden],#snaglist-root,[class*=sl-],.table-wrap,pre")) { bad.push(el.tagName + "." + String(el.className).slice(0, 30) + "#" + el.id + "[" + (el.textContent || "").trim().slice(0, 20) + "]"); if (bad.length > 4) break; } }
        return { scrollW: de.scrollWidth, clientW: de.clientWidth, bad };
      });
      layout.push({ label, page: pname, ...o, hscroll: o.scrollW > o.clientW + 1 });
      if (o.scrollW > o.clientW + 1) fail(`sideways scroll at ${label} on ${pname}: ${o.scrollW} > ${o.clientW} ${o.bad.join(",")}`);
      await page.close();
    }
    await ctx.close();
  }
  // Target size and keyboard walk
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const walks = [];
  for (const [pname, file] of pages) {
    const page = await open(ctx, file, "light");
    const small = await page.evaluate(() => [...document.querySelectorAll("a[href],button,input,select,textarea,[tabindex='0'],summary")].filter((e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width && cs.visibility !== "hidden" && !e.closest("[hidden],.visually-hidden") && !e.matches(".visually-hidden,.skip-link") && !e.closest("[class*=sl-],#snaglist-root") && (r.height < 43.5 || r.width < 43.5) && !(e.tagName === "A" && getComputedStyle(e).display === "inline") && !(e.type === "checkbox") && !(e.closest("table") && e.tagName === "A"); }).map((e) => e.tagName + ":" + (e.textContent || e.getAttribute("aria-label") || "").trim().slice(0, 30) + " " + Math.round(e.getBoundingClientRect().width) + "x" + Math.round(e.getBoundingClientRect().height)).slice(0, 12));
    if (small.length) fail(`targets under 44px on ${pname}: ${small.join(" ; ")}`);
    const seq = [];
    for (let i = 0; i < 120; i++) {
      await page.keyboard.press("Tab");
      const d = await page.evaluate(() => { const e = document.activeElement; if (!e || e === document.body) return null; const cs = getComputedStyle(e); const sm = e.closest("[class*=sl-],#snaglist-root") || e.tagName === "SNAG-LIST" ? "snaglist" : ""; let ring = false; for (let a = e, i = 0; a && i < 4; a = a.parentElement, i++) { const c = getComputedStyle(a); if ((c.outlineStyle !== "none" && parseFloat(c.outlineWidth) >= 2) || c.boxShadow !== "none") ring = true; } return { n: e.tagName + ":" + (e.getAttribute("aria-label") || e.textContent || e.id).trim().replace(/\s+/g, " ").slice(0, 28), outline: ring ? "ring" : "none", shadow: ring, sm }; });
      if (!d) break; seq.push(d);
      if (seq.length > 3 && seq[0].n === d.n && i > 3) break;
    }
    const noOutline = seq.filter((s) => s.outline.startsWith("none") && !s.shadow && !s.sm).map((s) => s.n);
    if (noOutline.length) fail(`keyboard walk ${pname}: no visible focus on ${noOutline.join(", ")}`);
    if (!/skip/i.test(seq[0]?.n || "")) fail(`keyboard walk ${pname}: the first stop is ${seq[0]?.n}, not the skip link`);
    walks.push({ page: pname, tabs: seq.length, first: seq[0]?.n, last: seq.slice(-2).map((s) => s.n), noOutline });
    await page.close();
  }
  {
    const page = await open(ctx, "plugins/audio-description.html", "light");
    await page.focus('[data-dialog="install-dialog"]'); await page.keyboard.press("Enter"); await page.waitForTimeout(150);
    const inDialog = await page.evaluate(() => !!document.activeElement.closest("dialog"));
    for (let i = 0; i < 6; i++) await page.keyboard.press("Tab");
    const trapped = await page.evaluate(() => !!document.activeElement.closest("dialog"));
    await page.keyboard.press("Escape"); await page.waitForTimeout(150);
    const back = await page.evaluate(() => document.activeElement.getAttribute("data-dialog"));
    await page.focus("#t-1"); await page.keyboard.press("ArrowRight"); await page.keyboard.press("Enter");
    const tab2 = await page.evaluate(() => [document.getElementById("t-2").getAttribute("aria-selected"), document.getElementById("tp-2").hidden]);
    const f = { dialogFocusIn: inDialog, trapped, escapeReturnsFocusTo: back, tabsArrowEnter: tab2 };
    walks.push({ functional: f });
    if (!inDialog || !trapped || back !== "install-dialog" || tab2[0] !== "true" || tab2[1] !== false) fail("plug-in page: dialog or tabs keyboard behaviour is wrong " + JSON.stringify(f));
    await page.close();
  }
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(`${OUT}/check-results.json`, JSON.stringify({ results, layout, walks, failures }, null, 1));
  let total = 0; for (const r of results) total += (r.violations || []).reduce((a, v) => a + v.n, 0);
  const axeRuns = results.filter((r) => r.violations).length;
  console.log(`AXE ${tags.join("+")}: ${axeRuns} runs, ${total} violating nodes; passes per run about ${Math.round(results.filter((r) => r.passes).reduce((a, r) => a + r.passes, 0) / axeRuns)}`);
  console.log(`LAYOUT rows without sideways scroll: ${layout.filter((l) => !l.hscroll).length} of ${layout.length}`);
  console.log(`KEYBOARD pages walked: ${walks.filter((w) => w.page).length}`);
  console.log(`NO-JAVASCRIPT pages read: ${results.filter((r) => r.cfg === "no-javascript").length}`);
  console.log(failures.length ? "FAILURES\n" + failures.map((f) => " - " + f).join("\n") : "ALL CHECKS PASSED");
}
if (MODE === "shots") {
  fs.mkdirSync(OUT, { recursive: true });
  const defs = [["home", "index.html"], ["plugin", "plugins/direct-play.html"], ["plugin-unmeasured", "plugins/kavita.html"], ["starboard", "starboard.html"], ["reelix", "reelix.html"], ["submit", "submit.html"], ["privacy", "privacy.html"], ["not-found", "missing.html"]];
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    for (const [n, f] of defs) { const p = await open(ctx, f, theme); await p.screenshot({ path: `${OUT}/${n}-${theme}-1280.jpg`, type: "jpeg", quality: 72, fullPage: true }); await p.close(); }
    const p = await open(ctx, "submit.html", theme);
    await p.click('button[type="submit"]'); await p.waitForTimeout(200); await p.screenshot({ path: `${OUT}/submit-errors-${theme}-1280.jpg`, type: "jpeg", quality: 72, fullPage: true });
    await p.fill("#address", "https://raw.githubusercontent.com/example-maker/example-plug-in/main/starboard-plugin.json"); await p.check("#mine");
    await p.evaluate(() => { document.getElementById("submit-form").addEventListener("submit", (e) => e.preventDefault(), { once: true }); });
    await p.click('button[type="submit"]'); await p.waitForTimeout(200); await p.screenshot({ path: `${OUT}/submit-success-${theme}-1280.jpg`, type: "jpeg", quality: 72, fullPage: true });
    await ctx.close();
  }
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
    for (const [n, f] of defs.slice(0, 5)) { const p = await open(ctx, f, theme); await p.screenshot({ path: `${OUT}/${n}-${theme}-375.jpg`, type: "jpeg", quality: 72, fullPage: true }); await p.close(); }
    await ctx.close();
  }
}
if (MODE === "shots") {
  for (const [theme, w, h, mobile] of [["light", 1280, 900, false], ["dark", 1280, 900, false], ["light", 375, 812, true]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, deviceScaleFactor: mobile ? 2 : 1 });
    for (const [n, f] of [["category", "category/jellyfin.html"], ["categories", "category/index.html"], ["plugin-gallery", "plugins/library-cleanup.html"]]) {
      if (theme === "dark" && n !== "category") continue;
      const p = await open(ctx, f, theme); await p.screenshot({ path: `${OUT}/${n}-${theme}-${w}.jpg`, type: "jpeg", quality: 72, fullPage: true }); await p.close();
    }
    const p = await open(ctx, "index.html", theme);
    await p.click("#display-open"); await p.waitForTimeout(400);
    await p.screenshot({ path: `${OUT}/display-panel-${theme}-${w}.jpg`, type: "jpeg", quality: 80 });
    await ctx.close();
  }
}
if (MODE === "social") {
  // The social image and the icons, drawn from the logo files: node check.mjs with MODE=social
  fs.mkdirSync(OUT, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 630 } });
  const page = await ctx.newPage();
  await page.goto(BASE + "assets/logo/social-source.html");
  await page.screenshot({ path: `${OUT}/social.png` });
  for (const [name, size] of [["favicon-32", 32], ["apple-touch-icon", 180], ["icon-512", 512]]) {
    const p2 = await ctx.newPage(); await p2.setViewportSize({ width: size, height: size });
    await p2.setContent(`<body style="margin:0"><img src="${BASE}assets/logo/stallboard-mark-light.svg" width="${size}" height="${size}" style="display:block"></body>`);
    await p2.waitForTimeout(200);
    await p2.screenshot({ path: `${OUT}/${name}.png`, omitBackground: true });
    await p2.close();
  }
}
server.close();
await browser.close();
if (MODE === "check" && failures.length) process.exit(1);
