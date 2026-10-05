// Records the demo: picture from a real browser, sound from the clip pack.
//
// The two halves are captured separately and put together afterwards, because a
// headless browser has no audio device. That turns out to be why the result is
// exact rather than a compromise: the page is driven with every clip taking its
// real length, so the cards arrive at speaking pace, and the frames and the
// clip offsets are stamped against the same clock.
//
// Frames are stills taken when something changes, not a video stream.
// page.screencast() produced 1040 frames for a 177-second run and labelled them
// 25 fps, so the picture ran four times too fast - it does not fill the long
// still stretches this page is mostly made of. A card arriving is a cut anyway,
// so stills lose nothing and stay sharp.
//
//   node tools/record_demo.mjs          # frames + timeline
//   python tools/mux_demo.py            # the finished mp4
//
// Needs the MCP server on :8421 and the demo shell on :8430.

import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://127.0.0.1:8430/';
const OUT = path.resolve('preview');
const FRAMES = path.join(OUT, 'frames');

const durations = JSON.parse(fs.readFileSync('preview/audio/durations.json', 'utf8'));

fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

// 1280x720 at 1.5x gives a 1920x1080 frame of a page laid out as though the
// browser were zoomed to 150 per cent - which is what the hand-made takes did,
// and for the same reason: the monospace labels have to survive YouTube.
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--window-size=1280,720', '--hide-scrollbars'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1.5 });

await page.evaluateOnNewDocument((clipLengths) => {
  window.__timeline = [];
  window.__t0 = null;
  window.__spoken = [];
  // Real lengths, real waiting, so the picture advances at the pace the audio
  // will. The page gives a clip five seconds to report its length before
  // deciding it has stalled, so this reports one.
  window.Audio = class {
    constructor(src) {
      this.listeners = {};
      const name = String(src).split('/').pop();
      const seconds = clipLengths[name];
      if (window.__t0 === null) window.__t0 = Date.now();
      if (seconds === undefined) {
        setTimeout(() => (this.listeners.error || (() => {}))(), 1);
        return;
      }
      this.duration = seconds;
      window.__timeline.push({ file: name, at: Date.now() - window.__t0, seconds });
      setTimeout(() => (this.listeners.loadedmetadata || (() => {}))(), 1);
      setTimeout(() => (this.listeners.ended || (() => {}))(), seconds * 1000);
    }
    addEventListener(kind, fn) {
      this.listeners[kind] = fn;
    }
    play() {
      return Promise.resolve();
    }
  };
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
      // The names shown in the selectors are on camera, so they are the
      // voices actually heard: the pack was rendered with these three.
      getVoices: () => [
        { name: 'Lauren', lang: 'en-GB', localService: false },
        { name: 'Lulu', lang: 'en-GB', localService: false },
        { name: 'Adam', lang: 'en-GB', localService: false },
      ],
      addEventListener() {},
      removeEventListener() {},
      cancel() {},
      speak(u) {
        window.__spoken.push(u.text);
        setTimeout(() => u.onend && u.onend(), 30);
      },
    },
  });
  // Scrolling jumps rather than glides: a smooth scroll between two stills
  // reads as a jump cut anyway, and an instant one lands the card where it
  // belongs in the very next frame.
  const realScroll = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function (arg) {
    return realScroll.call(this, typeof arg === 'object' ? { ...arg, behavior: 'auto' } : arg);
  };
}, durations);

await page.goto(URL, { waitUntil: 'networkidle0' });
await new Promise((r) => setTimeout(r, 400));

const frames = [];
let index = 0;
let previous = '';
const t0 = Date.now();

async function capture() {
  const file = path.join(FRAMES, `f${String(index).padStart(4, '0')}.png`);
  await page.screenshot({ path: file });
  frames.push({ file, at: Date.now() - t0 });
  index += 1;
}

// The opening screen, held while the narration plays over it.
await capture();
await page.click('#run');

// A still per visible change: a card arriving, the promise strip pinning, a
// tick turning, or the page scrolling under one.
const started = Date.now();
let quietPolls = 0;
while (Date.now() - started < 400000) {
  const state = await page.evaluate(() => {
    const cards = document.querySelectorAll('#timeline .event').length;
    const ticks = document.querySelectorAll('#promise li.met').length;
    const pinned = document.querySelector('#promise').className;
    return `${cards}:${ticks}:${Math.round(window.scrollY / 8)}:${pinned}`;
  });
  if (state !== previous) {
    previous = state;
    quietPolls = 0;
    await capture();
  } else {
    quietPolls += 1;
  }
  const done = await page.evaluate(() => {
    const n = window.__timeline.length;
    const last = window.__timeline[n - 1];
    return n > 5 && last && Date.now() - window.__t0 > last.at + last.seconds * 1000 + 1500;
  });
  if (done && quietPolls > 4) break;
  await new Promise((r) => setTimeout(r, 120));
}

// Hold the last card for a beat rather than cutting on its final syllable.
await new Promise((r) => setTimeout(r, 1500));
await capture();

const timeline = await page.evaluate(() => window.__timeline);
const spoken = await page.evaluate(() => window.__spoken);
await browser.close();

fs.writeFileSync(
  path.join(OUT, 'timeline.json'),
  JSON.stringify({ frames, clips: timeline, total: frames[frames.length - 1].at }, null, 2),
);

const last = timeline[timeline.length - 1];
console.log(`${timeline.length} clips, last ends at ${((last.at + last.seconds * 1000) / 1000).toFixed(1)} s`);
console.log(`${frames.length} frames over ${(frames[frames.length - 1].at / 1000).toFixed(1)} s`);
if (spoken.length) {
  console.log(`WARNING: ${spoken.length} lines had no clip:`);
  for (const line of spoken) console.log(`  ${line.slice(0, 70)}`);
}
console.log('now run: python tools/mux_demo.py');
