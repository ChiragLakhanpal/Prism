/**
 * Sediment: a clear core standing in a foot, the core sample of the title
 * slide grown on (Prism's deck, the opener of How it grows;
 * .notes/deck2/brief.md, section 6). At its bottom lies the old core, the
 * sample's three bands in little; on it settle new thin layers, one a night,
 * each a little thicker or thinner than the last; above them, the nights still
 * to come drift loose in the clear tube, each a little off centre. The
 * pointer's height sets how many nights have settled: the layers under it drop
 * onto the core and the rest of the drift sinks after them, staggered up from
 * the lowest, on the 700ms lift curve; brought back, the drift lifts from the
 * top down. The newest settled layer holds the bright stroke and its night
 * goes to the read-out. At rest five nights have settled and one drifts. The
 * slider is the stagger, in ms.
 *
 * The glass is the one thing drawn without a fill: its back rim is painted
 * before the layers and its front rim and walls after them, so the tube is
 * clear and nothing shows through a solid.
 *
 * The pattern: discrete items. Tweens, a stagger by distance from where the
 * change starts, and a hit test on the tube, which never moves.
 */
const {
  Cam, circ, extremes, facing, fit, open, prism, proj, ringAt, run, seg,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const R = 30, B = 1.4, LR = 26, OLD = 40, SEAM = 0.6, GAP0 = 16, PITCH = 13, REST = 5, S = 1.78;
const THICK = [3, 3.8, 2.6, 3.4, 2.8, 4]; // one layer a night, none the same
const DRIFT = [[2.5, -2], [-2, 2.5], [3, 1], [-2.5, -2.5], [1.5, 3], [-3, 1]]; // where each drifts while loose
const N = THICK.length;
const H = OLD + THICK[0] + SEAM + GAP0 + (N - 2) * PITCH + 4 + 8; // the tube's height: the drift with one night settled, and a margin

/** Each layer's base once settled: on the old core, under the ones after it. */
const SETTLED = THICK.map((_, i) => OLD + SEAM + THICK.slice(0, i).reduce((a, t) => a + t + SEAM, 0));
/** Layer i's base and drift with n nights settled. */
function pose(i, n) {
  if (i < n) return [SETTLED[i], 0];
  const top = n ? SETTLED[n - 1] + THICK[n - 1] : OLD;
  return [top + GAP0 + (i - n) * PITCH, 1];
}

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let stag = value, act = -2;
  const C = Cam(45, 0.5, S);
  fit(C, [[-R - 10, -R - 10, -7], [R + 10, R + 10, -7], [R + 10, -R - 10, -7], [-R - 10, R + 10, -7], [-R, -R, H], [R, R, H]], 200, 166);
  const P = proj(C), front = facing(C);
  const ring = (r, dx = 0, dy = 0) => circ(r, 48).map((q) => ({ ...q, u: q.u + dx, v: q.v + dy }));
  const tube = ring(R), wall = ring(R - B);
  const back = (r) => open(ringAt(P, run(r, (q) => !front(q)), H));
  const near = (r, z) => open(ringAt(P, run(r, front), z));
  const g = mk("g", {}, svg);

  // the foot, the tube's back rim, then the old core with its grooves
  put(solid(g), prism(P, front, ring(R + 10), ring(R + 8.4), -7, 0));
  mk("path", { d: back(tube) + back(wall), class: "nf" }, g);
  // the old core is the title's sample in little: a block with one seam, three offset sheets, a grooved band
  put(solid(g), prism(P, front, ring(LR), ring(LR - B), 0, 15));
  [[0, 0], [1.4, -1], [-1.1, 1.3]].forEach(([dx, dy], k) =>
    put(solid(g), prism(P, front, ring(LR, dx, dy), ring(LR - B, dx, dy), 15.6 + k * 4.2, 19.2 + k * 4.2)));
  put(solid(g), prism(P, front, ring(LR), ring(LR - B), 28.8, OLD));
  mk("path", { d: [6.3, 31.6, 34.4, 37.2].map((z) => near(ring(LR), z)).join(""), class: "nf lo" }, g);

  // the layers, oldest first: index order is height order in every pose, so it is the paint order
  const layers = THICK.map((t, i) => {
    const [z, d] = pose(i, REST);
    return { i, t, el: solid(g), z: tween(z), d: tween(d), drawn: "" };
  });

  // the glass in front: its near rim, its walls, and where it stands in the foot
  const [l, r] = extremes(P, tube);
  mk("path", {
    d: near(tube, H) + near(wall, H) + near(tube, 0) + seg(P(l.u, l.v, 0), P(l.u, l.v, H)) + seg(P(r.u, r.v, 0), P(r.u, r.v, H)),
    class: "nf",
  }, g);

  function draw(ly, now) {
    const z = tval(ly.z, now), d = tval(ly.d, now), key = z + "," + d;
    if (key === ly.drawn) return;
    ly.drawn = key;
    const [dx, dy] = DRIFT[ly.i].map((v) => v * d);
    put(ly.el, prism(P, front, ring(LR, dx, dy), ring(LR - B, dx, dy), z, z + ly.t));
  }

  const L = register(stage, (_dt, now) => {
    let moving = false;
    for (const ly of layers) { draw(ly, now); if (!tdone(ly.z, now) || !tdone(ly.d, now)) moving = true; }
    return moving;
  });
  bag.add(L.unregister);

  /**
   * n nights settled (-1 for rest). Settling, the stagger runs up from the lowest layer that moves; lifting,
   * down from the top. Every layer then leads the ones above it down and trails them up, so none passes
   * another and index order stays paint order.
   */
  let was = REST;
  function choose(a) {
    if (a === act) return;
    const now = performance.now(), n = a < 0 ? REST : a, down = n > was;
    act = a;
    for (const ly of layers) {
      const [z, d] = pose(ly.i, n), delay = (down ? Math.max(0, ly.i - was) : N - 1 - ly.i) * stag;
      tset(ly.z, z, now, delay); tset(ly.d, d, now, delay);
      ly.el.sil.classList.toggle("hi", ly.i === n - 1);
    }
    was = n;
    read.textContent = a < 0 ? "rest" : "night " + n;
    L.wake();
  }

  // Hit test: the tube never moves. Its height, from the old core's top to its rim, is read as nights settled.
  const cx = P(0, 0, 0)[0], yb = P(0, 0, OLD)[1], yt = P(0, 0, H)[1];
  function hit([sx, sy]) {
    if (Math.abs(sx - cx) > R * S * 1.1 || sy < yt - 30 || sy > yb + 40) return -1;
    return Math.max(1, Math.min(N, Math.round(1 + ((yb - sy) / (yb - yt)) * (N - 1))));
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
  name: "sediment",
  means: "New reports settle as new layers every night, and every layer is kept.",
  rules: [1, 2, 4, 5],
  range: [20, 50, 90],
  tour: [[200, 162], [200, 59], [200, 136], null],
  mount,
});
