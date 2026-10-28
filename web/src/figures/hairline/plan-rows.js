/**
 * Plan rows: a borrower's Procurement Plan as seven thin row slabs on a
 * clipboard, under a clip at the head of the board (Strata's deck, the opener
 * of Strata at work; .notes/deck2/brief.md, section 6). Short creases cut every
 * row into the plan's columns, the same on each row, so the slabs read as one
 * table, and each row has a check box at its head. A row stands off the board
 * by how much it asks for: rows on time lie flat with a dim dot in the box,
 * rows worth watching stand a little off it with a medium dot, and the row
 * that needs a look stands highest and holds the bright stroke at rest. The pointer lifts
 * the row under it, and its two neighbours a little, staggered outwards on the
 * 700ms lift curve; the bright stroke goes to the row it lifts, and the row's
 * status to the read-out. The slider is the lift, in world units.
 *
 * The pattern: discrete items. Tweens, a stagger by distance, and a hit test on
 * each row's resting top, so a row lifting out cannot flip the choice.
 */
const {
  Cam, facing, fit, flatDot, place, poly, prism, proj, ringAt, rings, rrect, seg, unproj,
  tdone, tset, tval, tween, disposer, mk, pointer, put, register, solid,
} = HL;

const N = 7, L = 132, D = 12, G = 3.2, T = 2.6, Y0 = 4, STEP = 45;
const BOX = [4, 13]; // each row's check box, at its head
const COLS = [20, 44, 84, 108]; // the plan's column edges, the same on every row
const STATUS = [0, 0, 1, 0, 2, 1, 0]; // 0 on time, 1 worth watching, 2 needs a look
const WORDS = ["on time", "worth watching", "needs a look"];
const OFF = [0, 3.6, 9]; // how far a row stands off the board at rest, by its status
const MARK = ["dot off", "dot m", "dot m"]; // the dot in a row's check box, by its status, until the row takes the bright
const FALL = [1, 0.3, 0.1]; // a lift's share on the row chosen and one and two rows from it; none beyond
const FOCAL = STATUS.indexOf(2);
const BX0 = -10, BX1 = L + 10, BY0 = -24, BY1 = Y0 + N * (D + G) - G + 10, BT = 5;

/** Row i's far edge on the board. */
const yAt = (i) => Y0 + i * (D + G);

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let lift = value, act = -2;

  // The camera is fitted to the board with the highest row lifted all the way, so nothing leaves the frame.
  const C = Cam(45, 0.5, 1.46);
  const high = OFF[2] + 22 + T;
  fit(C, [[BX0, BY0, -BT], [BX1, BY1, -BT], [BX1, BY0, -BT], [BX0, BY1, -BT], [BX0, BY0, high], [BX1, BY1, high]], 200, 166);
  const P = proj(C), front = facing(C);
  const g = mk("g", {}, svg);

  // The board and the clip at its head, a hinge roll over a pressure plate: they never move, so they are drawn once.
  const [br, bi] = rings(BX0, BY0, BX1, BY1, 9, 2);
  put(solid(g), prism(P, front, br, bi, -BT, 0));
  const hx = L / 2;
  const [pr, pi] = rings(hx - 30, BY0 + 6, hx + 30, Y0 - 4, 3, 1.2);
  put(solid(g), prism(P, front, pr, pi, 0, 1.6));
  mk("path", { d: poly(ringAt(P, rrect(hx - 10, Y0 - 12, hx + 10, Y0 - 8, 2, 4), 1.6)), class: "nf lo" }, g);
  // the roll overhangs the board's head edge, as a clip grips it
  const [hr, hn] = rings(hx - 24, BY0 - 3, hx + 24, BY0 + 9, 5, 1.2);
  put(solid(g), prism(P, front, hr, hn, 0, 7));

  // The rows, far to near, so appending is painting back to front. Each has a check box at its head, holding a dot.
  const rows = STATUS.map((s, i) => {
    const y = yAt(i), [ring, inner] = rings(0, y, L, y + D, 2.6, 0.9);
    const el = solid(g), cols = mk("path", { class: "nf lo" }, g), box = mk("path", { class: "nf" }, g);
    const dot = flatDot(g, C, 1.5, MARK[s]), cb = rrect(BOX[0], y + 2.5, BOX[1], y + D - 2.5, 1.6, 3);
    return { i, s, y, ring, inner, el, cols, box, cb, dot, z: tween(OFF[s]), drawn: NaN };
  });

  function draw(r, z) {
    if (z === r.drawn) return;
    r.drawn = z;
    put(r.el, prism(P, front, r.ring, r.inner, z, z + T));
    const zt = z + T;
    r.cols.setAttribute("d", COLS.map((x) => seg(P(x, r.y + 1.8, zt), P(x, r.y + D - 1.8, zt))).join(""));
    r.box.setAttribute("d", poly(ringAt(P, r.cb, zt)));
    place(r.dot, P((BOX[0] + BOX[1]) / 2, r.y + D / 2, zt));
  }

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const r of rows) { draw(r, tval(r.z, now)); if (!tdone(r.z, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** Lifts row a (-1 lets them all back down). The stagger spreads out from the row lifted, or the one let go. */
  function choose(a) {
    if (a === act) return;
    const now = performance.now(), from = a >= 0 ? a : Math.max(act, 0);
    act = a;
    for (const r of rows) {
      const k = Math.abs(r.i - a), up = a < 0 || k >= FALL.length ? 0 : lift * FALL[k];
      tset(r.z, OFF[r.s] + up, now, Math.abs(r.i - from) * STEP);
      const lit = a < 0 ? r.i === FOCAL : r.i === a;
      r.el.sil.classList.toggle("hi", lit); r.dot.setAttribute("class", lit ? "dot" : MARK[r.s]);
    }
    read.textContent = a < 0 ? "rest" : WORDS[rows[a].s];
    B.wake();
  }

  // Hit test: the pointer on each row's RESTING top plane, which never moves; the row whose middle it lands nearest.
  function hit([sx, sy]) {
    let best = -1, bd = (D + G) * 0.9;
    for (const r of rows) {
      const [wx, wy] = unproj(C, sx, sy, OFF[r.s] + T);
      const d = Math.abs(wy - (r.y + D / 2));
      if (wx > -8 && wx < L + 8 && d < bd) { bd = d; best = r.i; }
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
  name: "plan-rows",
  means: "A borrower's plan, checked row by row.",
  rules: [1, 2, 4, 5],
  range: [8, 14, 22],
  tour: [[257, 187], [160, 197], [150, 171], null],
  mount,
});
