// Takes the Catalogue row and the "what it asks for" panel of each plug-in from Starboard's example server (made-up
// data only). Runs in the Playwright image (tools/plugin-shots.sh). Writes catalogue-<id>.png and install-<id>.png.
import { chromium } from "playwright";
import fs from "fs";

const base = process.env.BASE, out = process.env.OUT || "/out";
const password = fs.readFileSync(process.env.PASSWORD_FILE, "utf8").trim();
const plugins = JSON.parse(fs.readFileSync(process.env.PLUGINS, "utf8"));
const only = (process.env.ONLY || "").split(",").filter(Boolean);
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
await context.addInitScript(() => { try { sessionStorage.setItem("starboard.setup-wizard", JSON.stringify({ opened: true })); } catch { /* fine */ } });
const login = await context.newPage();
await login.goto(`${base}/login.html`);
await login.fill("input[type=password]", password);
await login.keyboard.press("Enter");
await login.waitForURL(/dashboard|index/);
await login.close();
const problems = [], done = [];
for (const p of plugins) {
  if (only.length && !only.includes(p.id)) continue;
  const page = await context.newPage();
  page.on("pageerror", (e) => problems.push(`${p.id}: ${e.message}`));
  try {
    await page.goto(`${base}/settings-plugins-catalogue.html`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    const find = () => page.locator("main li.row", { has: page.locator(`text="${p.name}"`) }).first();
    let row = find();
    await row.waitFor({ timeout: 10000 });
    const btn = row.locator("button", { hasText: /^Install/ }).first();
    if (await btn.count()) {
      await btn.click();
      await page.waitForSelector("#side-panel li", { timeout: 8000 });
      await page.waitForTimeout(1200);
      await page.screenshot({ path: `${out}/install-${p.id}.png` });
      done.push(`install-${p.id}`);
      await page.goto(`${base}/settings-plugins-catalogue.html`, { waitUntil: "networkidle" });
      await page.waitForTimeout(1500);
      row = find();
    }
    await row.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    const bb = await row.boundingBox();
    await page.screenshot({ path: `${out}/catalogue-${p.id}.png`, clip: { x: Math.max(0, bb.x - 12), y: Math.max(0, bb.y - 8), width: Math.min(bb.width + 24, 1280), height: Math.min(bb.height + 16, 1000 - Math.max(0, bb.y - 8)) } });
    done.push(`catalogue-${p.id}`);
  } catch (e) { problems.push(`${p.id}: ${String(e.message).split("\n")[0]}`); await page.screenshot({ path: `${out}/fail-${p.id}.png` }).catch(() => {}); }
  await page.close();
}
await browser.close();
console.log("TAKEN", done.length);
if (problems.length) { console.log("PROBLEMS\n" + problems.join("\n")); process.exit(1); }
