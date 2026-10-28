/**
 * Passages: a report of four pages, each page carrying three paragraph slabs
 * with lines of text on them, beside a low shelf with a row of three places
 * for each page, the page's number dotted at the row's end (Strata's deck, the
 * opener of How it is built; .notes/deck2/brief.md, section 6). The pointer
 * opens the report at the page under it: the pages above lift away as one
 * block, staggered outwards from it, and the page's three passages lift off
 * and slide out to their places in that page's row, one after another, on the
 * 700ms lift curve. Pointing at a row of the shelf opens its page the same way.
 * The chosen page's passages take the bright stroke and its number goes to the
 * read-out. At rest the report lies open at page 2, its passages filed and
 * bright. The slider is the gap the report opens.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, a hit test on the
 * report's resting height and the shelf's fixed rows, and paint order kept true
 * by moving a passage's group when it clears the report, never by redrawing.
 */
const {
  Cam, facing, fit, flatDot, place, poly, prism, proj, ringAt, rings, rrect, seg, unproj,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const N = 4, PW = 34, PD = 60, TP = 2.6, PT = 1.5, PITCH = TP + PT + 0.6, STEP = 50;
const PARAS = [[4, 18], [22, 37], [41, 56]]; // each passage's span across its page
const LINES = [[0.82, 0.6], [0.9, 0.72], [0.78, 0.86]]; // its two lines of text, as shares of its length
const X0 = 4, X1 = 30; // a passage's span along the page
const XT0 = 48, RP = 30, TT = 3, BACK = 12; // the shelf: where it starts, its row pitch, its height, its back's
const XT1 = XT0 + 4 + N * RP, YT0 = -6, YT1 = PD + 5;
const REST = 1, ARC = 7; // the page open at rest; how high a passage arcs on its way

/** Row k's offset along the shelf from a passage's place on its page. */
const reach = (k) => XT0 + 4 + k * RP - X0;

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let gap = value, act = -2;
  const C = Cam(45, 0.5, 1.5);
  const top = N * PITCH + 26 + ARC;
  fit(C, [[0, 0, 0], [XT1, YT1, 0], [XT1, YT0, 0], [0, YT1, 0], [0, 0, top], [PW, PD, top]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  // The shelf and its back, painted first: they are low and in front of the report, so the two never cross on screen.
  const [br, bi] = rings(XT0 + 5, YT0 - 3, XT1 - 5, YT0, 1.5, 0.6);
  put(solid(g), prism(P, front, br, bi, 0, BACK));
  const [sr, si] = rings(XT0, YT0, XT1, YT1, 6, 1.6);
  put(solid(g), prism(P, front, sr, si, 0, TT));
  const marks = [];
  for (let k = 0; k < N; k++) {
    const x = XT0 + 4 + k * RP;
    PARAS.forEach(([y0, y1]) => marks.push(poly(ringAt(P, rrect(x - 1, y0 - 1, x + X1 - X0 + 1, y1 + 1, 2, 3), TT))));
    if (k) marks.push(seg(P(x - 2.5, YT0 + 3, TT), P(x - 2.5, YT1 - 3, TT)));
    for (let d = 0; d <= k; d++) place(flatDot(g, C, 0.9, "dot off"), P(x + 3 + d * 3.4, YT1 - 2.5, TT));
  }
  mk("path", { d: marks.join(""), class: "nf lo" }, g);

  // The report, bottom page first. Each passage has a place in the paint order on its page and one after
  // everything, and moves between them when it clears the report's front.
  const [pr, pi] = rings(0, 0, PW, PD, 3, 1);
  const pages = [], home = [], out = [];
  for (let k = N - 1; k >= 0; k--) {
    const el = solid(g), prints = mk("path", { class: "nf lo" }, g);
    pages[k] = { k, el, prints, z: tween(0), drawn: NaN };
    home[k] = PARAS.map(() => mk("g", {}, g));
  }
  const tail = mk("g", {}, g);
  for (let k = 0; k < N; k++) out[k] = PARAS.map(() => mk("g", {}, tail));
  const slabs = [];
  for (let k = 0; k < N; k++) PARAS.forEach(([y0, y1], j) => {
    const grp = mk("g", {}, home[k][j]), el = solid(grp), text = mk("path", { class: "nf lo" }, grp);
    const [ring, inner] = rings(X0, y0, X1, y1, 1.8, 0.7);
    slabs.push({ k, j, y0, y1, grp, el, text, ring, inner, s: tween(0), outside: false, drawn: "" });
  });
  const base = (k) => (N - 1 - k) * PITCH;

  function drawPage(p, z) {
    if (z === p.drawn) return;
    p.drawn = z;
    put(p.el, prism(P, front, pr, pi, base(p.k) + z, base(p.k) + z + TP));
    p.prints.setAttribute("d", PARAS.map(([y0, y1]) => poly(ringAt(P, rrect(X0 - 1, y0 - 1, X1 + 1, y1 + 1, 2, 3), base(p.k) + z + TP))).join(""));
  }
  function drawSlab(sl, now) {
    const s = tval(sl.s, now), zh = base(sl.k) + tval(pages[sl.k].z, now) + TP;
    const dx = s * reach(sl.k), z = zh + (TT - zh) * s + ARC * Math.sin(Math.PI * s), key = dx + "," + z;
    if (key === sl.drawn) return;
    sl.drawn = key;
    const shift = (r) => r.map((q) => ({ ...q, u: q.u + dx }));
    put(sl.el, prism(P, front, shift(sl.ring), shift(sl.inner), z, z + PT));
    const len = X1 - X0 - 6;
    sl.text.setAttribute("d", LINES[sl.j].map((f, n) => {
      const y = sl.y0 + (sl.y1 - sl.y0) * (n + 1) / 3;
      return seg(P(X0 + 3 + dx, y, z + PT), P(X0 + 3 + dx + len * f, y, z + PT));
    }).join(""));
    // the order changes where the passage's back edge clears the report's front edge
    const outside = X0 + dx > PW + 1;
    if (outside !== sl.outside) { sl.outside = outside; (outside ? out : home)[sl.k][sl.j].append(sl.grp); }
  }

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const p of pages) { drawPage(p, tval(p.z, now)); if (!tdone(p.z, now)) moving = true; }
    for (const sl of slabs) { drawSlab(sl, now); if (!tdone(sl.s, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** Opens the report at page a (-1 for rest). The pages above lift, spreading from it; its passages go out in turn. */
  function choose(a) {
    if (a === act) return;
    const now = performance.now(), at = a < 0 ? REST : a, lift = a < 0 ? gap * 0.6 : gap;
    act = a;
    for (const p of pages) tset(p.z, p.k < at ? lift : 0, now, Math.abs(p.k - at) * STEP);
    for (const sl of slabs) {
      const go = sl.k === at;
      tset(sl.s, go ? 1 : 0, now, go ? 260 + sl.j * STEP : (2 - sl.j) * STEP);
      sl.el.sil.classList.toggle("hi", go);
    }
    read.textContent = a < 0 ? "rest" : "page " + (a + 1);
    B.wake();
  }

  // Hit test, on poses that never move: a row of the shelf, from the pointer on the shelf's top; or a page of
  // the report, from the pointer's height over the report as it lies closed.
  const yTop = P(0, 0, N * PITCH)[1], yBot = P(PW, PD, 0)[1];
  const xL = P(0, PD, 0)[0], xR = P(PW, 0, 0)[0];
  function hit([sx, sy]) {
    const [wx, wy] = unproj(C, sx, sy, TT);
    if (wx >= XT0 && wx <= XT1 && wy >= YT0 && wy <= YT1) return Math.max(0, Math.min(N - 1, Math.floor((wx - XT0 - 2) / RP)));
    if (sx < xL - 6 || sx > xR + 6 || sy < yTop - 30 || sy > yBot + 6) return -1;
    return Math.max(0, Math.min(N - 1, Math.floor(((sy - yTop) / (yBot - yTop)) * N)));
  }

  choose(-1);
  bag.add(pointer(stage, { move: (p) => choose(hit(p)), leave: () => choose(-1) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { gap = v; const a = act; act = -2; choose(a); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "passages",
  means: "Every page becomes numbered passages, each with its page.",
  rules: [1, 2, 6, 10],
  range: [14, 20, 28],
  tour: [[157, 128], [157, 166], [266, 225], null],
  mount,
});
