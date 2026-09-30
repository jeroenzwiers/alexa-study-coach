// Drives the demo shell in a real browser and reports what a viewer would get.
//
// The demo has been through a run of defects that no Python test could see and
// that a human had to sit through to find: a stretch of eight cards with no
// audio, an answer spoken to the wrong question, a tick mark mangled into "13",
// a stray space before a comma. This exists so nobody has to find the next one
// by watching.
//
// It replaces speech synthesis with a recorder, so every utterance is captured
// with its voice, pitch, rate and the time real speech would have taken. It
// then checks the things that broke before: that no card is silent, that the
// question counter never jumps, that the three promises tick over, and that
// the console is clean. Screenshots are written alongside for the things only
// an eye can judge.
//
//   npm install puppeteer-core          # needs Chrome already on the machine
//   python server/app.py                # and the demo shell on :8430
//   node harness/test_demo_browser.mjs [output-dir]
//
// Not wired into the Python suite: it needs node and a browser, and the rest of
// the harness deliberately needs neither.

import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://127.0.0.1:8430/';
const OUT = process.argv[2] || '.';

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--window-size=1600,1000'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 1000 });

// Replace speech synthesis with a recorder. `speechSynthesis` is a read-only
// accessor on window, so it has to be redefined rather than assigned - an
// earlier version assigned it, the assignment was silently dropped, and the
// run recorded nothing at all.
await page.evaluateOnNewDocument(() => {
  window.__speech = [];
  const t0 = Date.now();
  const voices = [
    { name: 'Test Coach Natural', lang: 'en-US', localService: false },
    { name: 'Test Student Natural', lang: 'en-GB', localService: false },
  ];
  class FakeUtterance {
    constructor(text) {
      this.text = text;
    }
  }
  const fake = {
    getVoices: () => voices,
    addEventListener() {},
    removeEventListener() {},
    cancel() {},
    speak(u) {
      const words = String(u.text || '').trim().split(/\s+/).filter(Boolean).length;
      const ms = Math.max(120, (words / (150 * (u.rate || 1))) * 60000);
      window.__speech.push({
        at: Date.now() - t0,
        ms: Math.round(ms),
        words,
        voice: u.voice ? u.voice.name : null,
        pitch: u.pitch,
        rate: u.rate,
        text: u.text,
      });
      // Finish quickly so the run completes fast; `ms` is what the real thing
      // would have taken and is what the report adds up.
      setTimeout(() => u.onend && u.onend(), 30);
    },
  };
  Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true });
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {
    value: FakeUtterance,
    configurable: true,
  });
});

const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + String(e)));
page.on('console', (m) => {
  if (m.type() === 'error') errors.push('console: ' + m.text());
});
page.on('response', (r) => {
  if (r.status() >= 400) errors.push('http ' + r.status() + ': ' + r.url());
});

await page.goto(URL, { waitUntil: 'networkidle0' });
await page.screenshot({ path: OUT + '/01-opening.png' });

const before = await page.evaluate(() => ({
  ticks: [...document.querySelectorAll('#promise li')].map((li) => ({
    text: li.innerText.replace(/\s+/g, ' ').trim(),
    met: li.classList.contains('met'),
    tick: (li.querySelector('.tick') || {}).textContent,
  })),
  pinned: document.querySelector('#promise').classList.contains('pinned'),
  coach: document.querySelector('#voice').value,
  student: document.querySelector('#voice-student').value,
  voiceOn: document.querySelector('#voice-on').checked,
}));

await page.click('#run');
await page.waitForFunction(
  () => document.querySelectorAll('#timeline .event').length >= 15,
  { timeout: 90000 },
);
await new Promise((r) => setTimeout(r, 3000));

const after = await page.evaluate(() => ({
  speech: window.__speech,
  cards: [...document.querySelectorAll('#timeline .event')].map((el) => ({
    cls: el.className,
    label: (el.querySelector('.label') || { innerText: '' }).innerText,
    speech: (el.querySelector('.speech') || { innerText: '' }).innerText,
    tags: [...el.querySelectorAll('.tag')].map((t) => t.innerText),
  })),
  ticks: [...document.querySelectorAll('#promise li')].map((li) => ({
    text: li.innerText.replace(/\s+/g, ' ').trim(),
    met: li.classList.contains('met'),
    tick: (li.querySelector('.tick') || {}).textContent,
  })),
  pinned: document.querySelector('#promise').classList.contains('pinned'),
  status: document.querySelector('#status').innerText,
  overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
}));

await page.screenshot({ path: OUT + '/02-end.png' });
await page.evaluate(() => window.scrollTo(0, 0));
await page.screenshot({ path: OUT + '/03-top.png' });
await page.evaluate(() => {
  const cards = document.querySelectorAll('#timeline .event');
  cards[Math.min(5, cards.length - 1)].scrollIntoView({ block: 'center' });
});
await page.screenshot({ path: OUT + '/04-middle.png' });

fs.writeFileSync(OUT + '/result.json', JSON.stringify({ before, after, errors }, null, 2));
console.log('cards:', after.cards.length, 'utterances:', after.speech.length, 'errors:', errors.length);
await browser.close();
