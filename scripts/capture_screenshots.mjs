#!/usr/bin/env node
/**
 * Capture screenshots of the CV Tailor app for the README.
 *
 * Prerequisites:
 *   - docker compose up -d
 *   - python manage.py seed_demo_data
 *   - cd frontend && npm run dev  (or Docker frontend running)
 *
 * Usage:
 *   npx playwright install chromium  # first time only
 *   node scripts/capture_screenshots.mjs
 */

import { chromium } from "playwright";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.join(__dirname, "..", "docs", "screenshots");

const BASE_URL = "http://localhost:3000";
const API_URL = "http://localhost:8000";
const DEMO_EMAIL = "demo@cvtailor.dev";
const DEMO_PASSWORD = "demo1234";

const VIEWPORT = { width: 1280, height: 800 };

async function login() {
  const res = await fetch(`${API_URL}/api/v1/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: DEMO_EMAIL, password: DEMO_PASSWORD }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  return res.json();
}

async function main() {
  // 1. Login via API to get tokens
  console.log("Logging in...");
  const auth = await login();
  console.log(`  Logged in as ${auth.user.email}`);

  // Build the Zustand auth-storage value
  const authStorage = JSON.stringify({
    state: {
      user: auth.user,
      accessToken: auth.access,
      refreshToken: auth.refresh,
      isAuthenticated: true,
      googleLinked: false,
      isLoading: false,
      error: null,
    },
    version: 0,
  });

  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: VIEWPORT });

  // Helper: take a screenshot with auth state pre-loaded
  async function capture(name, urlPath, { authenticated = true, waitMs = 2000 } = {}) {
    const page = await context.newPage();

    if (authenticated) {
      // Inject auth state into localStorage before navigating
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
      await page.evaluate((val) => {
        localStorage.setItem("auth-storage", val);
      }, authStorage);
    }

    const url = `${BASE_URL}${urlPath}`;
    console.log(`  Capturing ${name} → ${url}`);
    await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
    await page.waitForTimeout(waitMs);

    const filePath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: filePath, fullPage: false });
    console.log(`    Saved ${filePath}`);
    await page.close();
  }

  // 2. Capture login page (unauthenticated)
  await capture("login", "/login", { authenticated: false });

  // 3. Capture authenticated pages
  await capture("dashboard", "/dashboard");
  await capture("artifacts", "/artifacts");
  await capture("generation-create", "/generations/create");

  // Bullet review — use the bullets_ready generation
  const bulletsReadyId = await getBulletsReadyId(auth.access);
  if (bulletsReadyId) {
    await capture("bullet-review", `/generations/${bulletsReadyId}`);
  } else {
    console.log("  WARNING: No bullets_ready generation found, skipping bullet-review screenshot");
  }

  await browser.close();
  console.log("\nDone! Screenshots saved to docs/screenshots/");
}

async function getBulletsReadyId(token) {
  const res = await fetch(`${API_URL}/api/v1/generations/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  const items = data.results || data;
  const found = items.find((g) => g.status === "bullets_ready");
  return found ? found.id : items[0]?.id;
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
