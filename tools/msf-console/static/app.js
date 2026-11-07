const $ = (s) => document.querySelector(s);

const state = {
  proteins: [],
  current: null,
  custom: null,   // a sequence the user pasted; has no pocket map
  track: "small",
  residues: [],
  sequence: "",
  // methane is the negative control from docs/04-EVALUATION.md 5.1 -- it must
  // score worst, so it is seeded and cannot be removed.
  ligands: [
    { name: "ATP", smiles: "Nc1ncnc2n(cnc12)C1OC(COP(O)(=O)OP(O)(=O)OP(O)(O)=O)C(O)C1O" },
    { name: "glutathione", smiles: "NC(CCC(=O)NC(CS)C(=O)NCC(O)=O)C(O)=O" },
    { name: "methane", smiles: "C", control: true },
  ],
};

const TRACK_LABEL = { small: "small molecule", metal: "metal", nuc: "nucleic acid" };

/* ---------- the ramp: pale sand -> teal -> deep indigo ---------- */

// The index is the model's *confidence in its call*, not a binding strength, so a
// confidently non-binding residue scores just as high as a confidently binding one.
// Colouring on the index alone would paint most of a protein dark and read as though
// it all binds. So the scale diverges: saturated means binds, pale means does not,
// and depth within each arm is the confidence.
const BIND = [
  [176, 205, 199], [150, 191, 189], [124, 175, 180], [ 99, 157, 171],
  [ 78, 137, 160], [ 60, 116, 147], [ 47,  96, 132], [ 38,  77, 114],
  [ 32,  59,  96], [ 24,  44,  76],
];
const NOBIND = [
  [240, 242, 241], [237, 239, 238], [234, 237, 236], [231, 234, 234],
  [228, 232, 232], [224, 229, 229], [220, 226, 226], [216, 223, 223],
  [212, 220, 220], [207, 216, 217],
];

function lerp(ramp, ri) {
  const t = Math.max(0, Math.min(9, ri));
  const i = Math.floor(t), f = t - i;
  const a = ramp[i], b = ramp[Math.min(9, i + 1)];
  return a.map((v, k) => Math.round(v + (b[k] - v) * f));
}

function riColor(ri, binds) {
  const c = lerp(binds ? BIND : NOBIND, ri);
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// flip the glyph to the pale ground once the cell is dark enough to need it
function textOn(ri, binds) {
  const [r, g, b] = lerp(binds ? BIND : NOBIND, ri);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.58 ? "#15303D" : "#F1F3F3";
}

function rampCss(ramp) {
  return `linear-gradient(90deg, ${ramp.map((c) => `rgb(${c[0]},${c[1]},${c[2]})`).join(",")})`;
}

/* ---------- boot ---------- */

async function boot() {
  const d = await (await fetch("/api/proteins")).json();
  state.proteins = d.proteins;

  $("#protein-aside").textContent = d.pocket_provenance.note;
  $("#screen-stamp").textContent =
    `PSICHIC, trained to ${d.psichic_contamination.training_cutoff}`;

  renderProteinList();
  renderRamp();
  renderQueue();

  const first = state.proteins.find((p) => p.has_pocket) || state.proteins[0];
  if (first) selectProtein(first.id);
}

function renderProteinList() {
  $("#protein-list").innerHTML = state.proteins
    .map(
      (p) => `<li><button data-id="${p.id}" ${p.id === state.current ? 'aria-current="true"' : ""}>
        <span>${p.id}</span><span class="len">${p.length}</span></button></li>`
    )
    .join("");
  document.querySelectorAll("#protein-list button").forEach((b) =>
    b.addEventListener("click", () => selectProtein(b.dataset.id))
  );
}

function renderRamp() {
  $("#ramp-bind").style.background = rampCss(BIND);
  $("#ramp-no").style.background = rampCss(NOBIND);
}

/* ---------- pocket channel ---------- */

function showEmptyPocket(label) {
  state.residues = [];
  $("#strip").innerHTML = "";
  $("#readout").textContent = "";
  document.querySelector(".strip-controls").hidden = true;
  document.querySelector(".legend").hidden = true;
  $("#pocket-sub").hidden = true;
  $("#pocket-caveat").className = "empty-pocket";
  $("#pocket-caveat").innerHTML =
    `<b>No binding map for ${label}.</b> This channel reads a ProtT5 embedding, and only the
     five candidates listed have one. Generating a new embedding means running the 3B-parameter
     ProtT5 model, which is not wired into this console.
     <br><br>The interaction channel below has no such limit, so you can still score this
     sequence against any ligand.`;
}

async function selectProtein(id) {
  state.current = id;
  state.custom = null;
  renderProteinList();
  $("#results").innerHTML = "";
  $("#run-msg").textContent = "";
  $("#specimen-name").textContent = id;
  document.querySelector(".strip-controls").hidden = false;
  document.querySelector(".legend").hidden = false;
  $("#pocket-sub").hidden = false;
  $("#pocket-caveat").className = "caveat";

  const r = await fetch(`/api/pocket/${encodeURIComponent(id)}`);
  if (!r.ok) {
    $("#measures").innerHTML = "";
    showEmptyPocket(id);
    return;
  }
  const d = await r.json();
  state.residues = d.residues;
  state.sequence = d.sequence;
  renderStrip();
  renderMeasures();
  renderPocketCaveat();
}

function renderStrip() {
  const t = state.track;
  const chunks = [];
  for (let i = 0; i < state.residues.length; i += 10) {
    const cells = state.residues
      .slice(i, i + 10)
      .map((res, k) => {
        const ri = res[t], b = res[t + "_b"], idx = i + k;
        return `<span class="res" data-i="${idx}"
          style="background:${riColor(ri, b)};color:${textOn(ri, b)}"
          >${state.sequence[idx] || "?"}</span>`;
      })
      .join("");
    chunks.push(
      `<div class="chunk"><div class="chunk-pos">${i + 1}</div>
       <div class="chunk-cells">${cells}</div></div>`
    );
  }
  const strip = $("#strip");
  strip.innerHTML = chunks.join("");
  strip.querySelectorAll(".res").forEach((el) =>
    el.addEventListener("mouseenter", () => showResidue(+el.dataset.i))
  );
  strip.addEventListener("mouseleave", () => {
    $("#readout").textContent = "Point at a residue to read its index.";
  });
}

function showResidue(i) {
  const r = state.residues[i];
  const t = state.track;
  $("#readout").innerHTML =
    `<b>${state.sequence[i] || "?"}${r.pos}</b> &nbsp; ${TRACK_LABEL[t]}
     <b>${r[t].toFixed(0)}</b> of 9, ${r[t + "_b"] ? "called binding" : "not called"}
     &nbsp;&nbsp; metal ${r.metal.toFixed(0)} &nbsp; nucleic ${r.nuc.toFixed(0)}
     &nbsp; small ${r.small.toFixed(0)}`;
}

function renderMeasures() {
  const n = state.residues.length;
  const sm = state.residues.filter((r) => r.small_b).length;
  const mt = state.residues.filter((r) => r.metal_b).length;
  const nu = state.residues.filter((r) => r.nuc_b).length;
  // Only rank residues the model actually calls binding. The index alone is
  // confidence in the call, so the highest index can be a confident "no".
  const called = state.residues.filter((r) => r.small_b);
  const top = called.length
    ? called.reduce((a, b) => (b.small > a.small ? b : a))
    : null;
  $("#measures").innerHTML =
    `<span><b>${n}</b> residues</span>
     <span><b>${sm}</b> called small molecule</span>
     <span><b>${mt}</b> metal</span>
     <span><b>${nu}</b> nucleic acid</span>
     <span>${top
       ? `surest small-molecule site at <b>${state.sequence[top.pos - 1] || "?"}${top.pos}</b>`
       : "no small-molecule site called"}</span>`;
}

function renderPocketCaveat() {
  const t = state.track;
  const n = state.residues.filter((r) => r[t + "_b"]).length;
  const pct = ((100 * n) / state.residues.length).toFixed(0);
  $("#pocket-caveat").textContent =
    `${n} of ${state.residues.length} residues, ${pct}%, clear the model's default 0.5 cutoff for
     ${TRACK_LABEL[t]} binding. Read that as orientation, not as a gate. A fixed cutoff is not
     calibrated for any one target, so the evaluation protocol scores the graded index instead.`;
}

document.querySelectorAll(".seg").forEach((btn) =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".seg").forEach((b) => b.classList.remove("is-on"));
    btn.classList.add("is-on");
    state.track = btn.dataset.track;
    if (state.residues.length) {
      renderStrip();
      renderPocketCaveat();
    }
  })
);

/* ---------- pasted sequences ---------- */

const panel = $("#paste-panel"), toggle = $("#paste-toggle");

function openPanel(open) {
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
  toggle.textContent = open ? "Hide sequence entry" : "Use another sequence";
  if (open) $("#seq-text").focus();
}

toggle.addEventListener("click", () => openPanel(panel.hidden));
$("#paste-cancel").addEventListener("click", () => {
  $("#paste-msg").textContent = "";
  openPanel(false);
});

panel.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = $("#paste-msg");
  const seq = $("#seq-text").value
    .split("\n").filter((l) => !l.startsWith(">")).join("")
    .replace(/[^A-Za-z]/g, "").toUpperCase();
  const bad = [...new Set(seq.split(""))].filter((c) => !"ACDEFGHIKLMNPQRSTVWY".includes(c));

  msg.className = "run-msg err";
  if (!seq) return (msg.textContent = "Paste a sequence first.");
  if (bad.length) return (msg.textContent = `Not an amino acid sequence. Found ${bad.join(", ")}.`);
  if (seq.length < 20) return (msg.textContent = `Only ${seq.length} residues. Needs at least 20.`);

  msg.textContent = "";
  const name = $("#seq-name").value.trim() || "Pasted sequence";
  state.current = null;
  state.custom = { name, sequence: seq };
  state.sequence = seq;
  renderProteinList();
  $("#specimen-name").textContent = name;
  $("#measures").innerHTML = `<span><b>${seq.length}</b> residues</span>
    <span>entered by hand, not from the candidate set</span>`;
  $("#results").innerHTML = "";
  $("#run-msg").textContent = "";
  showEmptyPocket(name);
  openPanel(false);
});

/* ---------- interaction channel ---------- */

function renderQueue() {
  $("#queue").innerHTML = state.ligands
    .map(
      (l, i) => `<li>
        <span class="q-name">${l.name}</span>
        <span class="q-smiles" title="${l.smiles}">${l.smiles}</span>
        ${l.control
          ? '<span class="q-ctrl">negative control, always run</span>'
          : `<button class="drop" data-i="${i}">remove</button>`}
      </li>`
    )
    .join("");
  document.querySelectorAll(".drop").forEach((b) =>
    b.addEventListener("click", () => {
      state.ligands.splice(+b.dataset.i, 1);
      renderQueue();
    })
  );
}

$("#ligand-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = $("#lig-name").value.trim();
  const smiles = $("#lig-smiles").value.trim();
  if (!smiles) return;
  state.ligands.push({ name: name || smiles.slice(0, 18), smiles });
  $("#lig-name").value = "";
  $("#lig-smiles").value = "";
  renderQueue();
  $("#lig-name").focus();
});

$("#run").addEventListener("click", async () => {
  const target = state.current || (state.custom && state.custom.name);
  if (!target) return;
  const btn = $("#run"), msg = $("#run-msg");
  btn.disabled = true;
  msg.className = "run-msg";
  msg.textContent = `Scoring ${state.ligands.length} ligands against ${target}.`;
  const t0 = performance.now();
  try {
    const calibrate = $("#calibrate").checked;
    if (calibrate) {
      msg.textContent += ` Also scoring ${state.ligands.length} × 30 background pairs,`
        + " so this takes a minute or two.";
    }
    const payload = state.custom
      ? { sequence: state.custom.sequence, protein_id: state.custom.name,
          ligands: state.ligands, calibrate }
      : { protein_id: state.current, ligands: state.ligands, calibrate };
    const r = await fetch("/api/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "The screen did not finish.");
    msg.textContent = `Scored in ${((performance.now() - t0) / 1000).toFixed(1)}s.`;
    renderResults(d);
  } catch (err) {
    msg.className = "run-msg err";
    msg.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
});

function renderResults(d) {
  const rows = d.results;
  const ctrl = rows.filter((r) => isControl(r.name));
  const real = rows.filter((r) => !isControl(r.name));

  // Bars span this run's own range, not zero. A zero-anchored bar would imply
  // these raw scores carry ratio meaning and invite the cross-molecule
  // comparison docs/04-EVALUATION.md forbids.
  const vals = rows.map((r) => r.affinity);
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;

  const cal = d.calibrated && rows.every((r) => r.background);

  const body = [...rows]
    .sort((a, b) => b.affinity - a.affinity)
    .map((r, i) => {
      const c = isControl(r.name);
      const w = 5 + 105 * ((r.affinity - lo) / span);
      const bg = r.background;
      return `<tr class="${c ? "is-ctrl" : ""}" style="animation-delay:${i * 45}ms">
        <td class="r-name">${r.name}${c ? ", control" : ""}</td>
        <td class="num"><span class="aff-cell">
          <span class="aff-bar${c ? " ctrl" : ""}" style="width:${w}px"></span>
          ${r.affinity.toFixed(2)}</span></td>
        ${cal ? `<td class="num">${bg.mean.toFixed(2)}</td>
        <td class="num ${bg.z > 1 ? "stands-out" : bg.z < 0 ? "below" : ""}">
          ${bg.z >= 0 ? "+" : ""}${bg.z.toFixed(2)}</td>
        <td class="num">${bg.percentile.toFixed(0)}</td>` : ""}
        <td class="verdict">${verdict(r)}</td>
      </tr>`;
    })
    .join("");

  const worst = real.length ? Math.min(...real.map((r) => r.affinity)) : Infinity;
  const passed = ctrl.length > 0 && ctrl.every((c) => c.affinity < worst);
  const check = ctrl.length
    ? `<p class="ctrl-check ${passed ? "" : "fail"}">
        ${passed
          ? `The control holds. Methane scored <b>${ctrl[0].affinity.toFixed(2)}</b>, under every
             real ligand, the lowest of which reached <b>${worst.toFixed(2)}</b>. Its non-binder
             probability was <b>${ctrl[0].nonbinder.toFixed(4)}</b>. The model is discriminating,
             not rewarding whatever it is handed.`
          : `The control failed. Methane scored <b>${ctrl[0].affinity.toFixed(2)}</b>, which is not
             under every real ligand, the lowest being <b>${worst.toFixed(2)}</b>. Discard this run
             and check the ligand inputs before reading anything into the other rows.`}
       </p>`
    : "";

  const caption = cal
    ? `${d.protein} against ${d.background_n} unrelated human protein domains.
       Affinity tracks molecular size, so the raw number cannot be compared between
       ligands &mdash; read the z-score instead. Anything under +1 is an ordinary score
       this ligand would get for almost any protein.`
    : `${d.protein}. Affinity is the model's raw output and it tracks molecular size, so it
       does not compare across ligands. Without a background comparison there is no way to
       tell a high score from an ordinary one.`;

  $("#results").innerHTML = `
    <div class="table-scroll"><table class="results-table">
      <caption>${caption}</caption>
      <thead><tr>
        <th>Ligand</th><th class="num">Affinity</th>
        ${cal ? '<th class="num">Background</th><th class="num">z</th>'
              + '<th class="num">Percentile</th>' : ""}
        <th>Reading</th>
      </tr></thead>
      <tbody>${body}</tbody>
    </table></div>${check}${cal ? standout(rows) : ""}`;
}

function standout(rows) {
  const real = rows.filter((r) => !isControl(r.name) && r.background);
  if (!real.length) return "";
  const hits = real.filter((r) => r.background.z >= 1);
  if (!hits.length) {
    const best = real.reduce((a, b) => (b.background.z > a.background.z ? b : a));
    return `<p class="ctrl-check">Nothing here stands out. The strongest is
      <b>${best.name}</b> at <b>z ${best.background.z >= 0 ? "+" : ""}${best.background.z.toFixed(2)}</b>,
      which is within the range this ligand scores against unrelated proteins. On this evidence
      the honest answer is no confident ligand, which is a result in itself.</p>`;
  }
  return `<p class="ctrl-check">${hits.map((h) => `<b>${h.name}</b> at z
    +${h.background.z.toFixed(2)}`).join(", ")} ${hits.length > 1 ? "score" : "scores"}
    above the background range. Treat that as a lead to test, not a finding: this model ranks
    at chance on annotated binding sites.</p>`;
}

function isControl(name) {
  return state.ligands.some((l) => l.control && l.name === name);
}

// The model's three classes are agonist / antagonist / non-binder, which is
// receptor pharmacology. Most targets here are enzymes and transporters, where
// a ligand is a substrate and "agonist" is a category error. So the two binding
// classes are summed and only binds / does not is reported.
function verdict(r) {
  const binder = r.agonist + r.antagonist;
  return binder >= r.nonbinder
    ? `binds, p=${binder.toFixed(2)}`
    : `does not bind, p=${r.nonbinder.toFixed(2)}`;
}

boot();
