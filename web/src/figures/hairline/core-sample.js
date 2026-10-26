/**
 * Core sample: a drill core lifted out of the ground, cut into three bands, one
 * per stratum (Strata's deck, ticket 47; the 47 brief, section 4.2). From the
 * bottom: Why, one dense block with a single seam, the way a bound report is;
 * How, thin stacked sheets with offset edges, the way plans and status reports
 * pile up; What, fine even grooves round it, row on row, the way records are.
 * The pointer's height picks a band, which slides out toward the viewer while
 * the gaps around it open, staggered by distance on the 700ms lift curve. The
 * chosen band takes the bright stroke and its name goes to the read-out. At
 * rest the bands sit slightly and unevenly parted, and the Why band is bright,
 * because the evidence of why is the hardest to reach. The slider is the gap.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, and a hit test on
 * the bands' resting heights, so a band moving out cannot flip the choice.
 */
const { Cam, circ, facing, fit, open, prism, proj, ringAt, run, tween, tset, tval, tdone, mk, pointer, put, register, solid, disposer } = HL;

const R = 42, B = 1.6, N = 36, OUT = 26, STEP = 45, S = 1.62;
// A chosen band slides toward the viewer and a little to the right, as a drawer is pulled.
const DX = 0.96, DY = 0.28;
// Bottom to top. Why is a block with one seam; How is three sheets, each offset; What has grooves.
const BANDS = [
  { name: "why", h: 40 },
  { name: "how", h: 30, sheets: [[0, 0], [2.2, -1.4], [-1.6, 2]] },
  { name: "what", h: 34, grooves: 5 },
];
const REST = [0.55, 1.05]; // the gaps at rest, as shares of the slider's gap: parted, not even
const OPEN = 1.9, SHUT = 0.45; // around the chosen band, and elsewhere

/** A ring moved by (dx, dy) on the ground. */
const shift = (ring, dx, dy) => ring.map((q) => ({ ...q, u: q.u + dx, v: q.v + dy }));

/** Each band's base height, given the two gaps between them. */
const bases = (gaps) => [0, BANDS[0].h + gaps[0], BANDS[0].h + gaps[0] + BANDS[1].h + gaps[1]];

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let gap = value, act = -1;
  const top = BANDS.reduce((sum, b) => sum + b.h, 0) + 2 * OPEN * 20;
  const C = Cam(45, 0.5, S);
  // Fitted to the most extreme pose: every gap open at the slider's far end and a band slid all the way out.
  fit(C, [[-R, -R, 0], [R + OUT * DX, R + OUT * DY, 0], [R, -R, 0], [-R, R, 0], [-R, -R, top], [R + OUT * DX, R + OUT * DY, top]], 200, 166);
  const P = proj(C), front = facing(C);
  const ring = circ(R, N), inner = circ(R - B, N);

  const g = mk("g", {}, svg);
  const bands = BANDS.map((band, i) => {
    const parts = (band.sheets || [[0, 0]]).map(() => solid(g));
    const marks = mk("path", { class: "nf lo" }, g);
    return { ...band, i, parts, marks, z: tween(bases(REST.map((r) => r * gap))[i]), s: tween(0) };
  });

  function drawBand(b, now) {
    const z0 = tval(b.z, now), ox = tval(b.s, now) * DX, oy = tval(b.s, now) * DY;
    if (b.sheets) {
      const h = b.h / b.sheets.length;
      b.sheets.forEach(([dx, dy], k) =>
        put(b.parts[k], prism(P, front, shift(ring, ox + dx, oy + dy), shift(inner, ox + dx, oy + dy), z0 + k * h, z0 + (k + 1) * h - 0.8)));
      b.marks.setAttribute("d", "");
      return;
    }
    const r = shift(ring, ox, oy);
    put(b.parts[0], prism(P, front, r, shift(inner, ox, oy), z0, z0 + b.h));
    const at = b.grooves ? Array.from({ length: b.grooves - 1 }, (_, k) => z0 + (b.h * (k + 1)) / b.grooves) : [z0 + b.h * 0.42];
    b.marks.setAttribute("d", at.map((z) => open(ringAt(P, run(r, front), z))).join(""));
  }

  const L = register(stage, (_dt, now) => {
    let moving = false;
    bands.forEach((b) => { drawBand(b, now); if (!tdone(b.z, now) || !tdone(b.s, now)) moving = true; });
    return moving;
  });
  bag.add(L.unregister);

  /** The gaps for a choice: open on both sides of the chosen band, shut elsewhere; at rest, REST. */
  const gapsFor = (a) => (a < 0 ? REST.map((r) => r * gap) : [0, 1].map((k) => (k === a || k + 1 === a ? OPEN : SHUT) * gap));

  /** Picks band a (-1 for rest). The stagger spreads out from the band chosen, or the one let go. */
  function setActive(a, force = false) {
    if (a === act && !force) return;
    const now = performance.now(), from = a >= 0 ? a : Math.max(act, 0);
    act = a;
    const z = bases(gapsFor(a));
    bands.forEach((b, i) => {
      const delay = Math.abs(i - from) * STEP;
      tset(b.z, z[i], now, delay);
      tset(b.s, i === a ? OUT : 0, now, delay);
      const lit = a < 0 ? i === 0 : i === a;
      b.parts.forEach((part) => part.sil.classList.toggle("hi", lit));
    });
    read.textContent = a < 0 ? "rest" : BANDS[a].name;
    L.wake();
  }

  // Hit bands: each band's resting height on screen, which moves only when the slider sets a new gap.
  const resting = () => bases(REST.map((r) => r * gap)).map((z, i) => P(0, 0, z + BANDS[i].h / 2)[1]);
  let rest = resting();
  const cx = P(0, 0, 0)[0], half = R * S * 1.25;
  function hit([x, y]) {
    if (Math.abs(x - cx) > half) return -1;
    let best = 0;
    rest.forEach((ry, i) => { if (Math.abs(y - ry) < Math.abs(y - rest[best])) best = i; });
    return Math.abs(y - rest[best]) > 60 ? -1 : best;
  }

  setActive(-1, true);
  bag.add(pointer(stage, { move: (p) => setActive(hit(p)), leave: () => setActive(-1) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { gap = v; rest = resting(); setActive(act, true); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "core-sample",
  means: "One core sample cut in three bands: records of what happened, documents on how it was done, and evaluations of why.",
  rules: [1, 2, 4, 5],
  range: [6, 12, 20],
  tour: [[200, 134], [200, 254], [200, 196], null],
  mount,
});
