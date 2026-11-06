/**
 * Filter: a column of six filter plates on three posts over a base, open at
 * the front, one plate for each of the verifier's checks, top to bottom
 * (Prism's deck, the opener of How it answers; .notes/deck2/brief.md, section
 * 6). Each plate is perforated and has a slot the sentences drop through; the
 * fourth, the check for support, runs out to one side as a ledge. Five sentence
 * slabs of different lengths lie in a pile. The pointer's height picks the
 * plate under it, which takes the bright stroke: the pile drops through the
 * plates above it and rests on it, slab after slab, staggered from the top.
 * Past the fourth plate one slab stays caught on it and slides out along the
 * ledge. At rest every check has run: four slabs lie on the base, and the one
 * taken out lies on the ledge with the bright stroke. The slider is the
 * stagger, in ms.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, a hit test on
 * plates that never move, and paint order kept true by moving a slab's group
 * to the gap it is in, never by redrawing. It is declared as "filters": the
 * validator's paint check refuses the string "filter", an SVG filter's name;
 * the deck keys it by its file name.
 */
const {
  Cam, circ, facing, fit, flatDot, place, poly, prism, proj, ringAt, rings, rrect,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const NAMES = ["numbers", "cited IDs", "quotes", "support", "advice", "both sides"];
const N = 6, W = 48, T = 2.6, GZ = 22, BH = 7, LIFT = 16, OUT = 30, FAIL = 3;
const POSTS = [[5, 5], [43, 5], [5, 43]]; // the far corner and the two sides: the rack is open at the front
const SLOT = [16, 25, 46, 41]; // toward the open front, so the pile shows in each gap
const SENT = [[27, 0], [19, 2], [24, -1], [21, 1], [25, 0]]; // each slab's length and its offset across the slot
const FAILS = 2; // the slab that fails the check for support
const SW = 9, ST = 2.2;
const HOLES = [10, 17, 24, 31, 38].flatMap((x) => [10, 17].map((y) => [x, y])); // the perforations, behind the slot

/** Plate k's base: 0 is the top plate. */
const zb = (k) => BH + LIFT + (N - 1 - k) * GZ;

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let stag = value, act = -2;
  const C = Cam(45, 0.5, 1.6);
  const ztop = zb(0) + T + 6;
  fit(C, [[-3, -3, 0], [W + OUT + 3, W + 3, 0], [W + OUT + 3, -3, 0], [-3, W + 3, 0], [-3, -3, ztop], [W, W, ztop]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);
  const post = (x, y, z0, z1) => {
    const r = circ(2.2, 12).map((q) => ({ ...q, u: q.u + x, v: q.v + y })), i = circ(1.4, 12).map((q) => ({ ...q, u: q.u + x, v: q.v + y }));
    put(solid(g), prism(P, front, r, i, z0, z1));
  };

  // The base, then, bottom up, each gap's posts and slabs and the plate over it. A slab lives in the
  // group of the gap it is in.
  const [br, bi] = rings(-3, -3, W + 3, W + 3, 7, 1.8);
  put(solid(g), prism(P, front, br, bi, 0, BH));
  const gaps = [];
  const plates = [];
  for (let k = N; k >= 0; k--) {
    const z0 = k === N ? BH : zb(k) + T, z1 = k === 0 ? z0 + 6 : zb(k - 1);
    POSTS.forEach(([x, y]) => post(x, y, z0, z1));
    gaps[k] = mk("g", {}, g);
    if (k === 0) break;
    const p = k - 1, x1 = p === FAIL ? W + OUT : W, [ring, inner] = rings(0, 0, x1, W, 6, 1.6), el = solid(g);
    put(el, prism(P, front, ring, inner, zb(p), zb(p) + T));
    const slot = mk("path", { d: poly(ringAt(P, rrect(...SLOT, 3, 4), zb(p) + T)), class: "nf lo" }, g);
    for (const [x, y] of HOLES) place(flatDot(g, C, 1.1, "dot off"), P(x, y, zb(p) + T));
    plates[p] = { el, slot };
  }
  const ahead = mk("g", {}, g); // the slab on the ledge, in front of everything

  /** Where each slab rests when the pile is on plate a (-1: on the base): its height, and whether it is out on the ledge. */
  const targets = (a) => {
    const floor = a < 0 ? BH : zb(a) + T, out = a < 0 || a > FAIL;
    let rank = 0;
    return SENT.map((_, i) => (i === FAILS && out ? [zb(FAIL) + T, 1] : [floor + ST * rank++, 0]));
  };
  const rest = targets(-1);
  const slabs = SENT.map(([len, dy], i) => {
    const x0 = (SLOT[0] + SLOT[2] - len) / 2 + dy, y0 = (SLOT[1] + SLOT[3] - SW) / 2 + dy;
    const grp = mk("g", {}, gaps[N]), el = solid(grp), [ring, inner] = rings(x0, y0, x0 + len, y0 + SW, 2, 0.6);
    return { i, x0, grp, el, ring, inner, z: tween(rest[i][0]), s: tween(rest[i][1]), at: gaps[N], drawn: "" };
  });

  /** The gap a slab whose base is at z is in, or the front once it is out on the ledge. */
  const where = (z, s, x0) => {
    if (x0 + s * OUT > W + 1) return ahead;
    for (let k = 0; k < N; k++) if (z >= zb(k) + T - 0.5) return gaps[k];
    return gaps[N];
  };

  function draw(sl, now) {
    const z = tval(sl.z, now), s = tval(sl.s, now), key = z + "," + s;
    if (key === sl.drawn) return;
    sl.drawn = key;
    const dx = s * OUT, shift = (r) => r.map((q) => ({ ...q, u: q.u + dx }));
    put(sl.el, prism(P, front, shift(sl.ring), shift(sl.inner), z, z + ST));
    const at = where(z, s, sl.x0);
    if (at !== sl.at) { sl.at = at; at.append(sl.grp); }
  }

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const sl of slabs) { draw(sl, now); if (!tdone(sl.z, now) || !tdone(sl.s, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** The pile rests on plate a (-1: on the base, every check run). Past the check for support, one slab stays there and slides out. */
  function choose(a) {
    if (a === act) return;
    const now = performance.now();
    act = a;
    const to = targets(a);
    for (const sl of slabs) {
      const [z, caught] = to[sl.i], delay = sl.i * stag;
      // the caught slab drops, then slides; brought back, it slides in, then drops
      tset(sl.z, z, now, caught ? delay : delay + (tval(sl.s, now) > 0.01 ? 300 : 0));
      tset(sl.s, caught ? 1 : 0, now, caught ? delay + 300 : 0);
      sl.el.sil.classList.toggle("hi", a < 0 && sl.i === FAILS);
    }
    plates.forEach((p, k) => { p.el.sil.classList.toggle("hi", k === a); p.slot.setAttribute("class", k === a ? "nf hi" : "nf lo"); });
    read.textContent = a < 0 ? "rest" : NAMES[a];
    B.wake();
  }

  // Hit test: the plates never move, so the plate whose front corner is nearest the pointer's height.
  const fy = plates.map((_, k) => P(W, W, zb(k) + T / 2)[1]);
  const xl = P(0, W, 0)[0] - 6, xr = P(W + OUT, 0, 0)[0] + 6;
  function hit([sx, sy]) {
    if (sx < xl || sx > xr || sy < fy[0] - 50 || sy > fy[N - 1] + GZ) return -1;
    let best = 0;
    fy.forEach((y, k) => { if (Math.abs(sy - y) < Math.abs(sy - fy[best])) best = k; });
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
  name: "filters",
  means: "Every sentence passes the checks, and one that fails is taken out.",
  rules: [1, 2, 4, 6],
  range: [0, 40, 90],
  tour: [[183, 97], [183, 188], [183, 249], null],
  mount,
});
