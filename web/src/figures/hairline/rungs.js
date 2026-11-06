/**
 * Rungs: the evidence ladder, a short ladder of four rungs leaning on a wall
 * and standing on a floor plate (Prism's research talk, the opener of The
 * decisions; .notes/deck3/brief.md, section 7). The plate is the floor, the
 * Bank's own record; the rungs from the bottom are public posts, satellite
 * pictures, formal complaints and field photos, each harder to fake than the
 * one below. The pointer's height picks the rung under it: that rung takes
 * the bright stroke, the rungs below it keep the silhouette's stroke, and the
 * rungs above it fade to the mid stroke, as rungs not reached. The change
 * spreads from the rung chosen, rung by rung, on the 700ms lift curve. The
 * read-out names the rung. At rest the top rung is lit. The slider is the
 * stagger, in ms.
 *
 * The rails are leaning solids: each is the hull of its foot ring on the plate
 * and its top ring against the wall, as a tapered solid is drawn. A rung is the
 * hull of its two round ends, and stops at the far rail's near face, so the
 * far rail is painted before it and the near rail after it.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, and a hit test
 * on the rungs, which never move: only their strokes change.
 */
const {
  Cam, facing, fit, hull, poly, prism, proj, ringAt, rings, rrect, seg,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const NAMES = ["posts", "satellite", "complaints", "photos"]; // bottom to top
const ZS = [18, 36, 54, 72], TOP = 84, FOOT = 34, LEAN = 2; // the rungs' heights; where the rails meet the wall; the feet; the top
const Y1 = 19, Y2 = 51, RT = 1.8, RR = 1.6; // the rails across the ladder, their half thickness; the rungs' radius
const WX = -6, WY0 = -2, WY1 = 72, WH = 94; // the wall: its back face, its run, its height
const PX0 = -14, PX1 = 50, PY0 = -8, PY1 = 78, PT = 4; // the floor plate
const CLASS = ["", "sil", "sil hi"]; // a rung above the chosen one, below it, and the one chosen
const REST = NAMES.length - 1;

/** A rail's or a rung's x at height z: the ladder leans from its feet to the wall. */
const xAt = (z) => FOOT + (LEAN - FOOT) * (z / TOP);

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let stag = value, act = -2;
  const C = Cam(45, 0.5, 1.84);
  fit(C, [[PX0, PY0, -PT], [PX1, PY1, -PT], [PX1, PY0, -PT], [PX0, PY1, -PT], [WX, WY0, WH], [0, WY1, WH]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  // The plate, then the wall standing at its back, with its courses on the face the ladder leans on.
  const [pr, pi] = rings(PX0, PY0, PX1, PY1, 8, 2);
  put(solid(g), prism(P, front, pr, pi, -PT, 0));
  const [wr, wi] = rings(WX, WY0, 0, WY1, 1.6, 0.8);
  put(solid(g), prism(P, front, wr, wi, 0, WH));
  mk("path", { d: [16, 32, 48, 64, 80].map((z) => seg(P(0, WY0 + 3, z), P(0, WY1 - 3, z))).join(""), class: "nf lo" }, g);

  // A rail: the hull of its foot on the plate and its top against the wall.
  const rail = (y) => {
    const ring = rrect(-RT, y - RT, RT, y + RT, 0.8, 3);
    const at = (dx, z) => ringAt(P, ring.map((q) => ({ ...q, u: q.u + dx })), z);
    mk("path", { d: poly(hull(at(FOOT, 0).concat(at(LEAN, TOP)))), class: "sil" }, g);
  };
  // A rung: the hull of its two round ends, from the far rail's near face into the near rail.
  const rung = (z) => {
    const x = xAt(z), ends = [];
    for (const y of [Y1 + RT, Y2])
      for (let k = 0; k < 12; k++) ends.push(P(x + RR * Math.cos((k * Math.PI) / 6), y, z + RR * Math.sin((k * Math.PI) / 6)));
    return mk("path", { d: poly(hull(ends)) }, g);
  };

  rail(Y1);
  // the top rung is the farthest from the viewer, so the rungs go top down
  const rungs = [];
  for (let i = ZS.length - 1; i >= 0; i--) rungs[i] = { i, el: rung(ZS[i]), lv: tween(i === REST ? 2 : 1), cls: -1 };
  rail(Y2);

  function draw(r, now) {
    const c = Math.round(tval(r.lv, now));
    if (c === r.cls) return;
    r.cls = c;
    r.el.setAttribute("class", CLASS[c]);
  }

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const r of rungs) { draw(r, now); if (!tdone(r.lv, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** Lights rung a (-1 for rest, the top one): below it the silhouette's stroke, above it the mid one, spreading from it. */
  function choose(a) {
    if (a === act) return;
    const now = performance.now(), at = a < 0 ? REST : a;
    act = a;
    for (const r of rungs) tset(r.lv, r.i === at ? 2 : r.i < at ? 1 : 0, now, Math.abs(r.i - at) * stag);
    read.textContent = a < 0 ? "rest" : NAMES[a];
    B.wake();
  }

  // Hit test: the rungs never move, so the rung whose middle is nearest the pointer's height, over the ladder.
  const ry = ZS.map((z) => P(xAt(z), (Y1 + Y2) / 2, z)[1]);
  const xL = P(LEAN, Y2, TOP)[0] - 12, xR = P(FOOT, Y1, 0)[0] + 12, half = (ry[0] - ry[1]) / 2; // the near rail's top, the far rail's foot
  function hit([sx, sy]) {
    if (sx < xL || sx > xR || sy > ry[0] + half + 8 || sy < ry[ry.length - 1] - half - 8) return -1;
    let best = 0;
    ry.forEach((y, k) => { if (Math.abs(sy - y) < Math.abs(sy - ry[best])) best = k; });
    return best;
  }

  choose(-1);
  bag.add(pointer(stage, { move: (p) => choose(hit(p)), leave: () => choose(-1) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { stag = v; },
    destroy: bag.dispose,
  };
}

hairline({
  name: "rungs",
  means: "Four rungs of evidence, each harder to fake than the one below.",
  rules: [1, 2, 4, 6],
  range: [0, 60, 120],
  tour: [[212, 212], [201, 178], [190, 144], [180, 110], null],
  mount,
});
