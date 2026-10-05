// Writes out every line the demo speaks, so they can be re-recorded properly.
//
// Chrome's Google voices arrive as a compressed stream: a spectrogram of any
// take shows a haze from 4 kHz to a hard shelf at 11.2 kHz, and it tracks the
// speech rather than sitting behind it. No filter removes that, because it is
// the voice. The way out is to render each line with a better engine and have
// the page play the files instead.
//
// This drives the real page, so the list is what the session actually says
// rather than what anyone believes it says. It writes:
//
//   preview/audio/manifest.json  every line with its hash, role and order
//   preview/audio/script.txt     the same lines, numbered, ready to paste
//
// Then: render each line, save it as preview/audio/<hash>.mp3, and the page
// picks it up. Anything missing falls back to the browser voice, so a partial
// set works and you can do it in batches.
//
//   npm install puppeteer-core        # needs Chrome, and the demo on :8430
//   node tools/dump_demo_speech.mjs

import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://127.0.0.1:8430/';
const OUT = path.resolve('preview/audio');

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new' });
const page = await browser.newPage();

// Record instead of speaking, and finish instantly so the whole run takes
// seconds. The keys come from the page itself, so they cannot drift from what
// it will look for at playback time.
await page.evaluateOnNewDocument(() => {
  window.__speech = [];
  const voices = [
    { name: 'A', lang: 'en-US', localService: false },
    { name: 'B', lang: 'en-GB', localService: false },
    { name: 'C', lang: 'en-GB', localService: false },
  ];
  class FakeUtterance {
    constructor(text) {
      this.text = text;
    }
  }
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {
    value: FakeUtterance,
    configurable: true,
  });
  Object.defineProperty(window, 'speechSynthesis', {
    configurable: true,
    value: {
      getVoices: () => voices,
      addEventListener() {},
      removeEventListener() {},
      cancel() {},
      speak(u) {
        window.__speech.push({
          key: u.__key,
          text: u.text,
          voice: u.voice ? u.voice.name : null,
          rate: u.rate,
        });
        setTimeout(() => u.onend && u.onend(), 5);
      },
    },
  });
  // No clip exists yet on a first run, and a 404 per line is noise.
  window.Audio = class {
    constructor() {}
    addEventListener(kind, fn) {
      if (kind === 'error') setTimeout(fn, 0);
    }
    play() {
      return Promise.reject(new Error('no clips yet'));
    }
  };
});

await page.goto(URL, { waitUntil: 'networkidle0' });
await page.click('#run');
// Wait for the run to have started before watching for it to stop, or the
// stability check is satisfied by nothing having happened yet.
await page.waitForFunction(() => window.__speech.length >= 5, { timeout: 90000 });
await page.waitForFunction(
  () => {
    const n = window.__speech.length;
    if (window.__n === n) return (window.__still = (window.__still || 0) + 1) > 6;
    window.__n = n;
    window.__still = 0;
    return false;
  },
  { timeout: 90000, polling: 300 },
);

const lines = await page.evaluate(() => window.__speech);
await browser.close();

// Role from the voice slot the page chose, named for a human reading the list.
const ROLE = { A: 'coach', B: 'student', C: 'narrator' };
const manifest = lines.map((l, i) => ({
  order: i + 1,
  key: l.key,
  role: ROLE[l.voice] || 'coach',
  text: l.text,
  file: `${l.key}.mp3`,
}));

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));

const byRole = new Map();
for (const m of manifest) {
  if (!byRole.has(m.role)) byRole.set(m.role, []);
  byRole.get(m.role).push(m);
}
let script = 'Every line the demo speaks, grouped by who says it.\n';
script += 'Render each one and save it as preview/audio/<file>.\n\n';
for (const [role, items] of byRole) {
  script += `${'='.repeat(70)}\n${role.toUpperCase()} - ${items.length} lines\n${'='.repeat(70)}\n\n`;
  for (const m of items) {
    script += `[${String(m.order).padStart(2, '0')}] ${m.file}\n${m.text}\n\n`;
  }
}
fs.writeFileSync(path.join(OUT, 'script.txt'), script);

const chars = manifest.reduce((n, m) => n + m.text.length, 0);
console.log(`${manifest.length} lines, ${chars} characters`);
for (const [role, items] of byRole) console.log(`  ${role}: ${items.length}`);
console.log(`written to ${OUT}`);
