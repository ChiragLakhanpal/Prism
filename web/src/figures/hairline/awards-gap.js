/**
 * Awards gap: the contract awards record as a row of year blocks on its base (Strata's deck, the data slide). The
 * older awards dataset's blocks stand on one base and the newer dataset's taller blocks on another; between them the
 * base breaks, and three thin plates lie on the ground where only award notices fill the years no dataset covers,
 * each with a dot, and a dashed outline of the block that is missing behind it. The middle plate holds the bright
 * stroke at rest. The pointer lifts the part under it, and its neighbours a little, staggered outwards on the 700ms
 * lift curve; the bright stroke goes to the part it lifts, and the part's years to the read-out. The slider is the
 * lift, in world units.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, and a hit test on each part's resting top, so a part
 * lifting out cannot flip the choice.
 */
const {
  Cam, facing, fit, flatDot, place, prism, proj, rings, unproj,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const W = 10, G = 3.2, D = 40, BT = 4, PT = 2.2, STEP = 45;
// 0: the older awards dataset, 1: years only award notices fill, 2: the newer awards dataset
const KIND = [0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 2];
const REST = [12, 15, 13, 16, 14, PT, PT, PT, 17, 14, 18, 15]; // each part's height at rest
const WORDS = ["FY01-16", "FY17-19", "FY20 on"];
const FALL = [1, 0.5, 0.18]; // a lift's share on the part chosen and one and two parts from it; none beyond
const FOCAL = 6;
const xAt = (i) => i * (W + G);
const LAST = KIND.length - 1;

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let lift = value, act = -2;

  // The camera is fitted to the row with the tallest block lifted all the way, so nothing leaves the frame.
  const C = Cam(45, 0.5, 2.25);
  const high = 18 + 24;
  fit(C, [[-6, -6, -BT], [xAt(LAST) + W + 6, D + 6, -BT], [xAt(LAST) + W + 6, -6, -BT], [-6, D + 6, -BT],
    [-6, -6, high], [xAt(LAST) + W + 6, D + 6, high]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  // The bases, broken where the notices lie: they never move, so they are drawn once.
  const base = (x0, x1) => { const [r, n] = rings(x0, -6, x1, D + 6, 5, 1.4); put(solid(g), prism(P, front, r, n, -BT, 0)); };
  base(-6, xAt(4) + W + 3);

  // The parts, far to near, so appending is painting back to front. A notice plate has the missing block's dashed
  // outline painted behind it, and a dot on its top.
  const parts = KIND.map((k, i) => {
    const x = xAt(i), [ring, inner] = rings(x, 0, x + W, D, 2.4, 0.9);
    if (i === 8) base(xAt(8) - 3, xAt(LAST) + W + 6);
    const z0 = k === 1 ? -BT : 0;
    if (k === 1) mk("path", { d: prism(P, front, ring, inner, 0, 15).sil, class: "nf dash lo" }, g);
    const el = solid(g), dot = k === 1 ? flatDot(g, C, 1.5, "dot m") : null;
    return { i, k, x, z0, ring, inner, el, dot, h: tween(REST[i]), drawn: NaN };
  });

  function draw(p, h) {
    if (h === p.drawn) return;
    p.drawn = h;
    put(p.el, prism(P, front, p.ring, p.inner, p.z0, p.z0 + h));
    if (p.dot) place(p.dot, P(p.x + W / 2, D / 2, p.z0 + h));
  }

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const p of parts) { draw(p, tval(p.h, now)); if (!tdone(p.h, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** Lifts part a (-1 lets them all back down). The stagger spreads out from the part lifted, or the one let go. */
  function choose(a) {
    if (a === act) return;
    const now = performance.now(), from = a >= 0 ? a : Math.max(act, 0);
    act = a;
    for (const p of parts) {
      const n = Math.abs(p.i - a), up = a < 0 || n >= FALL.length ? 0 : lift * FALL[n];
      tset(p.h, REST[p.i] + up, now, Math.abs(p.i - from) * STEP);
      const lit = a < 0 ? p.i === FOCAL : p.i === a;
      p.el.sil.classList.toggle("hi", lit);
      if (p.dot) p.dot.setAttribute("class", lit ? "dot" : "dot m");
    }
    read.textContent = a < 0 ? "rest" : WORDS[parts[a].k];
    B.wake();
  }

  // Hit test: the pointer on each part's RESTING top plane, which never moves; the part whose middle it lands nearest.
  function hit([sx, sy]) {
    let best = -1, bd = (W + G) * 0.75;
    for (const p of parts) {
      const [wx, wy] = unproj(C, sx, sy, p.z0 + REST[p.i]);
      const d = Math.abs(wx - (p.x + W / 2));
      if (wy > -6 && wy < D + 6 && d < bd) { bd = d; best = p.i; }
    }
    return best;
  }

  choose(-1);
  bag.add(pointer(stage, { move: (p) => choose(hit(p)), leave: () => choose(-1) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { lift = v; const a = act; act = -2; choose(a); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "awards-gap",
  means: "The awards record year by year, with a break that only award notices fill.",
  rules: [1, 2, 5, 6],
  range: [10, 16, 24],
  tour: [[126, 141], [211, 212], [295, 215], null],
  mount,
});
