/**
 * Ground: a square plot of nine ground tiles on a plate, and a page lying
 * beside it with faint lines of text (Prism's research talk, the title slide
 * and the close; .notes/deck3/brief.md, section 7). One tile is lifted off
 * the plot as a thin slab, its socket left bare on the plate, and a pin stands
 * on it; a thin thread runs from the pin's head down to one line of the page,
 * the line that tile's site is cited in. The pointer's position on the plot
 * picks which tile lifts: the old one settles back into its socket, its pin
 * sinking and its thread drawn back into the pin, staggered by distance from
 * the new one, on the 700ms lift curve, while the new pin rises and its thread
 * reaches out to its own line. The lifted tile holds the bright stroke; the
 * pointer on the pin moves it to the pin, and on the page to the page; the
 * read-out says "a site", "a photo" or "a brief". At rest the middle tile of
 * the left edge is lifted, and bright, its thread across the plot. The slider
 * is the lift, in world units.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, a hit test on
 * the pin's target pose, then the plate's top split into plot and page, which
 * meet, so a pointer crossing from one to the other never passes over nothing;
 * threads drawn last, since they ride above everything they cross.
 */
const {
  Cam, clamp, facing, fit, lerp, open, poly, prism, proj, ringAt, rings, rrect, seg, unproj,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const N = 3, CELL = 24, FOOT = 21, EXT = N * CELL, STEP = 40;
const H0 = [2.4, 3.2, 2.6, 3, 2.2, 3.4, 2.8, 2.4, 3]; // each tile's thickness, tile t = i + 3j: no two rows alike
const PIN = 21, HR = 2.8, ARC = 6, REST = 3; // the pin's needle and head, the thread's rise, the tile lifted at rest
const PX0 = 90, PX1 = 124, PY0 = 4, PY1 = 54, PZ0 = -5, PZ1 = -3.4, XS = EXT + 5; // the page; XS, the plate's edge, splits plot from page
const LINES = [[11, 26], [16, 21], [21, 26], [29, 24], [34, 15], [42, 26], [47, 19]]; // each line's y on the page, and its length
const CITE = [0, 1, 2, 3, 3, 4, 5, 6, 6]; // the line each tile's site is cited in

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let lift = value, site = -2, on = "";
  const C = Cam(45, 0.5, 2);
  const top = 14 + 3.4 + PIN + 2 * HR;
  fit(C, [[-5, -5, -5], [PX1, PY1, PZ0], [PX1, PY0, PZ0], [-5, EXT + 5, -5], [12, 12, top], [PX1, PY0, top * 0.4]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  // The plate, and on it each tile's socket, which shows when its tile lifts away.
  const [pr, pi] = rings(-5, -5, EXT + 5, EXT + 5, 8, 2);
  put(solid(g), prism(P, front, pr, pi, -5, 0));
  const tiles = [];
  for (let t = 0; t < N * N; t++) {
    const i = t % N, j = Math.floor(t / N), x0 = i * CELL + (CELL - FOOT) / 2, y0 = j * CELL + (CELL - FOOT) / 2;
    mk("path", { d: poly(ringAt(P, rrect(x0, y0, x0 + FOOT, y0 + FOOT, 2.6, 3), 0)), class: "nf lo" }, g);
    const [ring, inner] = rings(x0, y0, x0 + FOOT, y0 + FOOT, 2.6, 0.9);
    tiles.push({ t, i, j, h: H0[t], cx: x0 + FOOT / 2, cy: y0 + FOOT / 2, ring, inner, z: tween(0), drawn: NaN });
  }
  // Back to front by i + j: each tile's group holds its slab, then its pin's needle and head.
  for (const tl of tiles.slice().sort((a, b) => a.i + a.j - (b.i + b.j) || a.i - b.i)) {
    tl.g = mk("g", {}, g);
    tl.el = solid(tl.g);
    tl.needle = mk("path", { class: "nf sil" }, tl.g);
    tl.head = mk("path", { class: "sil" }, tl.g);
  }

  // The page, nearer than the plot, so painted after it; its lines; each tile's thread, over everything.
  const [gr, gi] = rings(PX0, PY0, PX1, PY1, 3, 1);
  const page = solid(g);
  put(page, prism(P, front, gr, gi, PZ0, PZ1));
  const lines = LINES.map(([y, len]) => mk("path", { d: seg(P(PX0 + 5, y, PZ1), P(PX0 + 5 + len, y, PZ1)), class: "nf lo" }, g));
  for (const tl of tiles) tl.thread = mk("path", { class: "nf" }, g);
  const HS = (P(0, 0, 0)[1] - P(0, 0, HR)[1]) / Math.sqrt(0.75); // the head's radius on screen

  /** A tile's thread: from its pin's head toward its line on the page, `reach` of the way, leaving the head at its rim. */
  function threadPath(tl, head, reach) {
    if (reach <= 0) return "";
    const end = [PX0 + 5, LINES[CITE[tl.t]][0], PZ1], h = P(...head), pts = [];
    for (let k = 0; k <= 24; k++) {
      const s = (k / 24) * reach;
      pts.push(P(lerp(head[0], end[0], s), lerp(head[1], end[1], s), lerp(head[2], end[2], s) + ARC * Math.sin(Math.PI * s)));
    }
    const out = pts.filter((p) => Math.hypot(p[0] - h[0], p[1] - h[1]) >= HS);
    return out.length > 1 ? open(out) : "";
  }

  function drawTile(tl, z) {
    if (z === tl.drawn) return;
    tl.drawn = z;
    put(tl.el, prism(P, front, tl.ring, tl.inner, z, z + tl.h));
    // the pin rises with the tile, and its thread reaches out to the page once the head is up
    const w = clamp(z / lift, 0, 1), foot = z + tl.h, tip = foot + PIN * w;
    tl.needle.setAttribute("d", w > 0.02 ? seg(P(tl.cx, tl.cy, foot), P(tl.cx, tl.cy, tip)) : "");
    const [hx, hy] = P(tl.cx, tl.cy, tip + HR);
    const ring = Array.from({ length: 16 }, (_, k) => [hx + HS * Math.cos((k * Math.PI) / 8), hy + HS * Math.sin((k * Math.PI) / 8)]);
    tl.head.setAttribute("d", w > 0.15 ? poly(ring) : "");
    tl.thread.setAttribute("d", threadPath(tl, [tl.cx, tl.cy, tip + HR], clamp((w - 0.15) / 0.85, 0, 1)));
  }

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const tl of tiles) { drawTile(tl, tval(tl.z, now)); if (!tdone(tl.z, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** The pointer is on a tile (lifting it), its pin, the page, or nothing (k ""): the bright goes to what it is on. */
  function choose(k, t) {
    const s = k === "tile" ? t : k === "" ? REST : site;
    if (k === on && s === site) return;
    const now = performance.now();
    on = k; site = s;
    const si = s % N, sj = Math.floor(s / N);
    for (const tl of tiles) {
      const up = tl.t === s, d = Math.abs(tl.i - si) + Math.abs(tl.j - sj);
      tset(tl.z, up ? lift : 0, now, up ? 0 : d * STEP);
      tl.el.sil.classList.toggle("hi", up && (k === "tile" || k === ""));
      tl.needle.classList.toggle("hi", up && k === "pin");
      tl.head.classList.toggle("hi", up && k === "pin");
    }
    page.sil.classList.toggle("hi", k === "page");
    lines.forEach((el, n) => el.setAttribute("class", n === CITE[s] ? "nf" : "nf lo"));
    read.textContent = { tile: "a site", pin: "a photo", page: "a brief", "": "rest" }[k];
    B.wake();
  }

  // Hit test, on poses that never move or are already the target: the site's pin as it will stand; then,
  // on the plate's top, the page beyond the plate's edge, or else the plot, where each tile's resting top
  // decides and the nearest middle wins. The plot and the page meet, so a pointer crossing from one to the
  // other never passes over nothing.
  function hit([sx, sy]) {
    const st = tiles[site < 0 ? REST : site], hd = P(st.cx, st.cy, lift + st.h + PIN + HR), ft = P(st.cx, st.cy, lift + st.h);
    if (Math.abs(sx - hd[0]) < 12 && sy > hd[1] - 10 && sy < ft[1] - 3) return ["pin", 0];
    const [qx, qy] = unproj(C, sx, sy, 0);
    if (qx >= XS) return qx <= PX1 + 8 && qy >= -12 && qy <= PY1 + 8 ? ["page", 0] : ["", 0];
    if (qx < -12 || qy < -12 || qy > EXT + 12) return ["", 0];
    let best = 0, bd = Infinity;
    for (const tl of tiles) {
      const [wx, wy] = unproj(C, sx, sy, tl.h), d = Math.max(Math.abs(wx - tl.cx), Math.abs(wy - tl.cy));
      if (d < bd) { bd = d; best = tl.t; }
    }
    return ["tile", best];
  }

  choose("", 0);
  bag.add(pointer(stage, { move: (p) => choose(...hit(p)), leave: () => choose("", 0) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { lift = v; const k = on, t = site; on = "-"; choose(k, t); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "ground",
  means: "A brief says what is happening at each site, with every line traced to its source.",
  rules: [1, 2, 4, 5],
  range: [6, 10, 14],
  tour: [[241, 175], [241, 118], [280, 228], null],
  mount,
});
