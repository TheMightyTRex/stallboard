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
  ["starboard", "starboard.html"], ["category", "category/jellyfin.html"], ["submit", "submit.html"], ["reviewed", "what-reviewed-means.html"],
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
        await page.click('#kind-chips button[data-kind="Jellyfin"]'); await page.waitForTimeout(100);
        record(cname, "home-filtered", await axeRun(page), page);
        await page.selectOption("#sort", "mem"); await page.waitForTimeout(100);
        record(cname, "home-sorted", await axeRun(page), page);
        const first = await page.evaluate(() => [...document.querySelectorAll("#all-list > li:not([hidden])")].slice(0, 3).map((l) => l.dataset.id));
        if (!first.length) fail("home sorted by memory: nothing shown");
        await page.selectOption("#mysb", "0.20.0"); await page.waitForTimeout(100);
        const marked = await page.evaluate(() => document.querySelectorAll('.sb-need[data-tone="danger"]').length);
        if (!marked) fail("home: no plug-in is marked as needing a newer Starboard than 0.20.0");
        record(cname, "home-marked", await axeRun(page), page);
      }
      if (pname === "plugin") {
        await page.click('[data-dialog="install-dialog"]'); await page.waitForTimeout(200);
        record(cname, "plugin-dialog", await axeRun(page), page, { focus: await page.evaluate(() => document.activeElement.getAttribute("aria-label") || document.activeElement.textContent.trim().slice(0, 30)) });
      }
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
  const defs = [["home", "index.html"], ["plugin", "plugins/direct-play.html"], ["plugin-unmeasured", "plugins/kavita.html"], ["starboard", "starboard.html"], ["submit", "submit.html"], ["privacy", "privacy.html"], ["not-found", "missing.html"]];
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
