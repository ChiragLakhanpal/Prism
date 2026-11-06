/**
 * Two slabs: two apps built on one brief, as two slabs of different sizes
 * lying apart on a long board, each with a title bar creased across its far
 * end and three dots in it, as a window has (Prism's research talk, the opener
 * of How we got here; .notes/deck3/brief.md, section 7). The pointer's place
 * from left to right is how far the two have come together: the smaller slab
 * slides along the board until it meets the larger one's side, rises beside
 * it, and settles on its top as one stack, set back so the larger slab's title
 * bar still shows, since nothing is dropped. The smaller slab holds the bright
 * stroke while it travels; once it is stacked, the stack takes it. The
 * read-out names the phase: "two apps", "one conversation", "one app". At rest
 * the two lie apart. The slider is the gap between them at rest, in world units.
 *
 * The pattern: scrub. One spring on how far it has come, a hit test on the
 * pointer's screen x across the board, which never moves, and paint order
 * kept true by moving the small slab's group past the large one's once it is
 * above the large one's top, never by redrawing.
 */
const {
  Cam, clamp, facing, fit, flatDot, lerp, place, prism, proj, rings, seg, spring, stepS,
  disposer, mk, pointer, put, register, solid,
} = HL;

const AX0 = 70, AW = 60, AD = 54, AH = 10; // the larger slab: where it starts along the board, its length, depth and height
const BW = 40, BD = 34, BH = 7; // the smaller slab
const BY0 = (AD - BD) / 2, TB = 10, HOP = 4; // the smaller one's place across the board; a title bar's width; how far it rises past the top
const BX0 = -8, BY = -10, BX1 = AX0 + AW + 8, BY1 = AD + 10, BT = 5; // the board
const REST = 0, MEET = 0.5, UP = 0.7; // the pose at rest; where the two meet; where the small one is up beside the top
const WORDS = [[0.34, "two apps"], [0.72, "one conversation"], [2, "one app"]];
const smooth = (u) => u * u * (3 - 2 * u);

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let gap = value, said = "";
  const C = Cam(45, 0.5, 1.96);
  const far = AX0 - 36 - BW; // the farthest the small slab starts, at the slider's top end
  fit(C, [[far - 8, BY, -BT], [BX1, BY1, -BT], [BX1, BY, -BT], [far - 8, BY1, -BT], [AX0, BY0, AH + HOP + BH], [far, BY0, BH]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  /** Where the small slab's far end and base are at progress p: along the board, then up beside the large one, then over onto it. */
  function pose(p) {
    const home = AX0 - gap - BW, meet = AX0 - BW, on = AX0 + TB + 4;
    if (p <= MEET) return [lerp(home, meet, smooth(p / MEET)), 0];
    if (p <= UP) return [meet, (AH + HOP) * smooth((p - MEET) / (UP - MEET))];
    const u = smooth(clamp((p - UP) / (0.92 - UP), 0, 1));
    return [lerp(meet, on, u), AH + HOP * (1 - u)];
  }

  const [br, bi] = rings(far - 8, BY, BX1, BY1, 8, 2);
  put(solid(g), prism(P, front, br, bi, -BT, 0));
  // a slab, with its title bar's crease and three dots and a few lines under it, as a group whose paths are
  // redrawn where it is; `rows` are the lines' lengths across the slab
  const slab = (w, d, h, y0, rows) => {
    const grp = mk("g", {}, g), el = solid(grp), bar = mk("path", { class: "nf" }, grp), body = mk("path", { class: "nf lo" }, grp);
    const dots = [0, 1, 2].map((k) => flatDot(grp, C, 1.25, k ? "dot off" : "dot m"));
    const draw = (x0, z) => {
      const [ring, inner] = rings(x0, y0, x0 + w, y0 + d, 3, 1), zt = z + h;
      put(el, prism(P, front, ring, inner, z, zt));
      bar.setAttribute("d", seg(P(x0 + TB, y0 + 1.6, zt), P(x0 + TB, y0 + d - 1.6, zt)));
      body.setAttribute("d", rows.map((len, k) => seg(P(x0 + TB + 6 + k * 6, y0 + 5, zt), P(x0 + TB + 6 + k * 6, y0 + 5 + len, zt))).join(""));
      dots.forEach((el2, k) => place(el2, P(x0 + TB / 2, y0 + 5.5 + k * 4.2, zt)));
    };
    return { grp, el, draw };
  };
  const small = slab(BW, BD, BH, BY0, [22, 16, 20]), large = slab(AW, AD, AH, 0, [40, 30, 44, 24, 36, 18]);
  large.draw(AX0, 0);

  const sp = spring(REST, { eps: 0.0005 });
  let drawn = NaN, above = false;
  function draw(p) {
    if (p === drawn) return;
    drawn = p;
    const [x0, z] = pose(clamp(p, 0, 1));
    small.draw(x0, z);
    // once its base is up at the large slab's top, the small slab is above it, so it is painted after it
    const up = z >= AH - 0.01;
    if (up !== above) { above = up; if (up) large.grp.after(small.grp); else large.grp.before(small.grp); }
  }

  const B = register(stage, (dt) => {
    const moving = stepS(sp, dt);
    draw(sp.x);
    return moving;
  });
  bag.add(B.unregister);

  /** Points the figure at progress t, or at rest (null). The read-out and the bright stroke read the target, never the spring. */
  function aim(t) {
    sp.t = t ?? REST;
    const stacked = t !== null && t >= WORDS[1][0];
    small.el.sil.classList.toggle("hi", true);
    large.el.sil.classList.toggle("hi", stacked);
    const word = t === null ? "rest" : WORDS.find(([to]) => t < to)[1];
    if (word !== said) read.textContent = said = word;
    B.wake();
  }

  // Hit test: the pointer's screen x across the board, which never moves, from the small slab's home to the
  // large slab's middle; above or below the board's band, or past its ends, is rest.
  const yTop = P(far - 8, BY, AH + HOP + BH)[1] - 10, yBot = P(BX1, BY1, -BT)[1] + 6;
  const xL = P(far - 8, BY1, 0)[0] - 6, xR = P(BX1, BY, 0)[0] + 6;
  function hit([sx, sy]) {
    if (sx < xL || sx > xR || sy < yTop || sy > yBot) return null;
    const a = P(AX0 - gap - BW / 2, AD / 2, 0)[0], b = P(AX0 + AW / 2, AD / 2, 0)[0];
    return clamp((sx - a) / (b - a), 0, 1);
  }

  aim(null);
  bag.add(pointer(stage, { move: (p) => aim(hit(p)), leave: () => aim(null) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { gap = v; drawn = NaN; B.wake(); },
    destroy: bag.dispose,
  };
}

hairline({
  name: "two-slabs",
  means: "Two apps on one brief become one, and nothing is dropped.",
  rules: [1, 3, 5, 8],
  range: [16, 26, 36],
  tour: [[160, 140], [205, 165], [262, 190], null],
  mount,
});
