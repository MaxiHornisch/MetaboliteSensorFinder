# Data sources: licensing, provenance and temporal pinning

Status: specification, v1.
Verification date: **2026-11-07**. Every licence below was read off an official page on that date unless marked `UNVERIFIED`.
Licences change. Re-run `scripts/verify_licenses.py` before any release and update the verification date.

This document is subordinate to [04-EVALUATION.md](04-EVALUATION.md).
Where that document defines a leakage class (L1 literature, L2 database annotations, L5 structure), this one says, per source, whether the leak can actually be closed.

## What you may safely commit to this repo

You may commit, as raw data, anything that is **CC0** (RCSB PDB, PDBe coordinate archive, InterPro, Pfam, Reactome data, OpenAlex, Open Targets Platform output, GWAS Catalog summary statistics flagged CC0) and anything that is **plain CC BY 4.0** (UniProt, ChEBI, Rhea, AlphaFold DB, LIPID MAPS, STRING, GPCRdb, PDBe-KB, Human-GEM, Human Protein Atlas **v25.0 and later only**), provided each such dataset lives in its own directory under `data/third_party/<source>/` with its own `LICENSE` and `NOTICE` file and is listed in `ATTRIBUTION.md` — CC BY data is *not* relicensed by the repo's Apache-2.0 header and must never appear to be.
You may commit **identifiers, dates and your own computed scores** derived from anything else.
You may **not** commit raw data, bulk extracts, or substantial verbatim excerpts from HMDB, KEGG, DrugBank, ARCHS4, ZINC, Recon3D/BiGG/VMH, ChEMBL, BindingDB's combined `BindingDB_All` file, HPA ≤ v24, PubMed abstracts, Europe PMC author manuscripts, or bioRxiv/medRxiv full text.
The repo's default licences (Apache-2.0 for code, CC BY 4.0 for text) apply to what *we* wrote; everything vendored carries its own terms, and the hackathon donation is only clean if that separation is visible in the tree.

## Red flags — the sources most likely to cost us the licence check

Ordered by how badly they break an open donation.

| Source | Problem | Consequence |
|---|---|---|
| **KEGG** | Copyright Kanehisa Laboratories. Website free for academics only; `rest.kegg.jp` is *"made available only for academic use by academic users"*; FTP is a paid academic subscription; non-academic use needs a commercial licence | `AVOID` entirely. Not a redistribution question — we may not even query it programmatically in a donatable project |
| **HMDB** | CC BY-**NC** 4.0, plus a separate clause requiring explicit permission for redistribution and commercial use | `AVOID`. NC is incompatible with both Apache-2.0 and CC BY 4.0. The classic trap, and the most tempting source in this project |
| **DrugBank** | CC BY-NC 4.0 **and** Terms of Use §2.1 forbid making the databases available to third parties. Academic downloads are additionally *paused* as of 2026-11-07 | `AVOID`. Only DrugBank **Open Data** (vocabulary + structures, CC0) is usable |
| **ARCHS4** | CC BY-**NC-SA** 4.0 — the link text on the terms page says "CC BY 4.0" but the `href` and the accompanying sentence say non-commercial. Both NC and SA | `AVOID`. The mislabelling is itself a risk; do not rely on the link text |
| **ZINC** | *"you may not redistribute major portions of ZINC without the express written permission of John Irwin"* | `AVOID` for data. IDs and our own screen results only |
| **Recon3D** (BiGG / VMH) | BiGG is UC Regents "educational, research and non-profit purposes" — functionally NC. VMH publishes **no licence at all** | `AVOID`. Use **Human-GEM** (CC BY 4.0) instead |
| **ChEMBL** | CC BY-**SA** 3.0 Unported. Share-alike is viral and propagates into BindingDB's `BindingDB_All`, Pharos/TCRD, and Open Targets' `sourceId=chembl` evidence | `DERIVED-FACTS-ONLY`. Not AVOID, but it contaminates three downstream sources that look clean |
| **Human Protein Atlas ≤ v24** | v24 is CC BY-SA 4.0; v18–v23 are CC BY-**SA** 3.0. Only v25.0 (2025-11-11) onward is plain CC BY 4.0 | A 2018-pinned HPA snapshot (v17/v18) is **share-alike**. The version we pin decides the licence |
| **GtoPdb** | ODbL (database) + CC BY-SA 4.0 (contents). Both are share-alike | Our *primary ground-truth source* is copyleft. `DERIVED-FACTS-ONLY`; see §2 |
| **PubChem** | NCBI adds no restriction but explicitly disclaims depositor IP, and the annotation layer carries through HMDB (NC), CTD (NC), PharmGKB (SA), WHO ATC (no commercial) | Pulling HMDB through PubChem **does not launder the licence**. Whitelist by `SourceName` |

Two further red flags that are not licensing but will break the benchmark:

- **AlphaFold DB did not exist before 2021-07.** It cannot be part of any evidence window with cutoff 2015 or 2018. Using it at those cutoffs is an L2 leak dressed as a feature.
- **STRING v10.5 bulk files are gone** (404 at every probed path), so the release that was current on 2018-01-01 is not reconstructable. The oldest retrievable modern release is v11.0, whose files are dated 2018-12-18.

---

## 1. Source register

Verdict vocabulary:

- `REDISTRIBUTABLE` — raw files may live in this repo, with attribution and a per-directory `LICENSE`.
- `FETCH-ONLY` — may be queried or downloaded at runtime, must not be committed.
- `DERIVED-FACTS-ONLY` — we may commit identifiers and our own computed values, not the source records. Usually because of share-alike, which we cannot satisfy without relicensing the repo.
- `AVOID` — do not commit, do not depend on at runtime in the donated artefact.

"2018 snapshot?" answers the one question [04-EVALUATION.md §2 L2](04-EVALUATION.md) actually needs: can we retrieve this source as it stood at the default cutoff `C = 2018-01-01`?

### 1.1 Protein sequence, family and structure

#### UniProt / Swiss-Prot

| | |
|---|---|
| Provides | Reviewed protein entries, sequences, `BINDING`/`ACT_SITE`/`COFACTOR` features, evidence codes, cross-references |
| Channel | Structure (sequence input), ground truth (orphan status at `C`) |
| Access | REST `https://rest.uniprot.org/`, no key. Bulk `https://ftp.uniprot.org/pub/databases/uniprot/` |
| Licence | **CC BY 4.0** — *"We have chosen to apply the Creative Commons Attribution 4.0 International (CC BY 4.0) License to all copyrightable parts of our databases."* (`https://www.uniprot.org/help/license`) |
| Verdict | `REDISTRIBUTABLE` with attribution |
| Archive | **Yes.** `https://ftp.uniprot.org/pub/databases/uniprot/previous_releases/release-<YYYY_NN>/`, oldest `release-2010_01`, per-release from `2015_01`. **`release-2018_01` exists.** Per-entry history via UniSave `https://rest.uniprot.org/unisave/<ACC>` |
| Cadence | ~8 weeks (4 weeks before release 2020_01). Current 2026_03/2026_04 |

Caveats.
TrEMBL is machine-annotated and dwarfs Swiss-Prot; its binding-site annotations are largely back-propagated from InterPro/UniRule/ARBA signatures.
Filter ligand labels to `ECO:0000269` (experimental) and reject `ECO:0000256`/`ECO:0000213`/`ECO:0000250`, or the loop will be scored on its own feature source.
`BINDING` coverage is sparse and biased toward well-studied families, which is exactly the survivorship problem flagged in [04-EVALUATION.md §9](04-EVALUATION.md).

#### InterPro / Pfam

| | |
|---|---|
| Provides | Domain and family signatures, clans, a small set of binding-site and active-site entries |
| Channel | Chemistry (family prior baseline), structure (domain boundaries) |
| Access | REST `https://www.ebi.ac.uk/interpro/api/`, no key. Bulk `https://ftp.ebi.ac.uk/pub/databases/interpro/` |
| Licence | **CC0 1.0** — *"All of the InterPro, Pfam, PRINTS and SFLD downloadable data provided on the InterPro website is freely available under CC0 1.0 Universal (CC0 1.0) Public Domain Dedication."* (`https://interpro-documentation.readthedocs.io/en/latest/license.html`) |
| Verdict | `REDISTRIBUTABLE`, unconditional. Other member databases (PANTHER, PROSITE, SMART, CDD, CATH-Gene3D, NCBIFAM) are **`UNVERIFIED` — must confirm before release** |
| Archive | **Yes, by version number not date.** `https://ftp.ebi.ac.uk/pub/databases/interpro/releases/<version>/` back to `1.0`; `https://ftp.ebi.ac.uk/pub/databases/Pfam/releases/Pfam<version>/` back to `Pfam1.0`. Map date → version via release notes |
| Cadence | ~8 weeks. Current InterPro 111.0 (2026-11-05), Pfam 39.0 |

Caveats.
Signatures are predictive models; a family hit is not evidence of a specific ligand.
Promiscuous folds (Rossmann, TIM barrel, P-loop NTPase) are where overprediction bites — a Rossmann hit does not discriminate NAD from FAD from SAM.
Binding-site entries number 82 out of 72,944 in release 111.0: coverage, not precision, is the limit.
**Circularity:** InterPro feeds TrEMBL's automatic annotation, so using InterPro features to predict UniProt labels trains the loop to reproduce InterPro.

#### RCSB PDB

| | |
|---|---|
| Provides | Experimental coordinates, bound ligands (HETATM), Chemical Component Dictionary, validation metrics |
| Channel | Structure, ground truth (holo evidence) |
| Access | Data REST `https://data.rcsb.org/rest/v1/`, search `https://search.rcsb.org/rcsbsearch/v2/query`, no key. Bulk `https://files.wwpdb.org/pub/pdb/`, rsync `rsync://rsync.rcsb.org`. **FTP protocol deprecated since 2024-11-01** |
| Licence | **CC0 1.0** — *"data files contained in the PDB archive are available under the CC0 1.0 Universal (CC0 1.0) Public Domain Dedication."* (`https://www.rcsb.org/pages/usage-policy`) |
| Verdict | `REDISTRIBUTABLE`, unconditional. RCSB-*computed* annotations and website content are not all CC0 — check separately |
| Archive | **Yes, truly dated.** `https://pdbsnapshots.s3.amazonaws.com/<YYYYMMDD>/pub/pdb/data/structures/divided/mmCIF/<2char>/<id>.cif.gz`, bucket `s3://pdbsnapshots/`. Snapshots exist for `20050106 … 20170101 20170308 20170710 **20180101** 20180321 20190101 … 20260415`. Per-entry versioned repo (since Oct 2017) at `https://ftp.ebi.ac.uk/pub/databases/pdb_versioned/data/entries/<2char>/<pdb_accession>/` |
| Cadence | Weekly, Wednesday 00:00 UTC. Snapshots annual plus milestones |

Caveats.
**Crystallisation additives masquerade as biological ligands**: GOL, EDO, PEG/PG4/1PE, SO4, PO4, ACT, DMSO, MES/TRIS/HEPES.
Harvesting all HETATM records yields a label set dominated by cryoprotectant.
Ions (NA, CL, K, MG, ZN, CA) are genuinely ambiguous and routinely mis-assigned against density.
Check `_atom_site.occupancy` and RSCC before treating a ligand as observed.
Use the biological assembly, not the asymmetric unit, or crystal-packing contacts count as sites.
Fragment-screening depositions dump hundreds of near-identical entries and massively over-weight a few targets.
**This is the L5 source**: a post-cutoff holo co-crystal of the answer is the single most direct structural leak, and the dated snapshot above is what closes it.
Note `https://s3snapshots.rcsb.org` is a browser-only SPA and unusable from a script; use the S3 object path.

#### PDBe and PDBe-KB

| | |
|---|---|
| Provides | PDBe: mirror of the archive plus SIFTS UniProt↔PDB residue mappings. PDBe-KB: aggregated per-UniProt ligand sites and binding annotations from ~30 partner resources |
| Channel | Structure |
| Access | PDBe REST `https://www.ebi.ac.uk/pdbe/api/`; PDBe-KB Graph API `https://www.ebi.ac.uk/pdbe/graph-api/` (e.g. `/uniprot/ligand_sites/<ACC>`), no key. Bulk `https://ftp.ebi.ac.uk/pub/databases/msd/` |
| Licence | PDBe archive **CC0** (`https://www.ebi.ac.uk/pdbe/about/public-data-access-statement`). PDBe-KB aggregate **CC BY 4.0**, *"All of the data provided is freely avaialble for both academic and commercial use"* [sic] (`https://www.ebi.ac.uk/pdbe/pdbe-kb/`) |
| Verdict | Archive `REDISTRIBUTABLE`. PDBe-KB aggregate `REDISTRIBUTABLE` with attribution + the 2022 NAR citation — **but per-contributor terms for the ~30 aggregated partner resources are `UNVERIFIED` — must confirm before release** if we vendor the full aggregate rather than query it |
| Archive | Coordinate archive: yes, via RCSB/PDBj snapshots (PDBe hosts none). Versioned repo mirrored at `https://ftp.ebi.ac.uk/pub/databases/pdb_versioned/`. **PDBe-KB aggregated annotations: no dated archive of any kind.** Snapshot at ingest |
| Cadence | Archive weekly. PDBe-KB aggregation cadence `UNVERIFIED` — no official statement; directory mtimes suggest irregular |

Caveats.
PDBe-KB fuses *experimental and predicted* annotations into one view; consuming `ligand_sites` without reading the per-annotation provenance field ingests predictions as labels.
"Bound molecules" group linked HETATM groups into composite entities, so monomer counts and bound-molecule counts differ — pick one deliberately before computing ligand frequencies.
SIFTS is authoritative but not 1:1; expression tags, engineered mutations and unmodelled loops mean PDB numbering ≠ UniProt numbering, and mapping sites onto an AlphaFold model without SIFTS silently off-by-N.
Several `pub/databases/msd/` subdirectories are stale relative to the weekly archive.

#### AlphaFold DB

| | |
|---|---|
| Provides | Predicted monomer structures, per-residue pLDDT, PAE, MSAs (v6+) |
| Channel | Structure |
| Access | REST `https://alphafold.ebi.ac.uk/api/prediction/<ACC>`, no key. Bulk `https://ftp.ebi.ac.uk/pub/databases/alphafold/`. Direct `/files/` fetches 403 bot-filtered clients; use the FTP mirror |
| Licence | **CC BY 4.0** — *"Data is available for academic and commercial use, under a CC-BY-4.0 licence."* (`https://alphafold.ebi.ac.uk/download`). Licence also travels inside each v2+ mmCIF under `_pdbx_data_usage` |
| Verdict | `REDISTRIBUTABLE` with attribution. **Datasets under `collaborations/` (AlphaMissense, BFVD, AllTheBacteria, Kinetoplastid, Viro3D, Viral AFDB) are separately copyrighted and `UNVERIFIED` — must confirm before release.** AlphaMissense in particular has carried non-commercial terms elsewhere |
| Archive | **By version number only, no dates.** `https://ftp.ebi.ac.uk/pub/databases/alphafold/v<1..6>/UP<proteome>_<taxid>_<MNEMONIC>_v<N>.tar`. v1 2021-07-22, v2 2021-12-09, v3 2022-01-27, v4 2022-11-01, v6 2025-09-15 (pinned to UniProt 2025_03). **v5's release date and content are `UNVERIFIED`** — the directory exists, the CHANGELOG does not document it |
| Cadence | Irregular, unannounced. Major releases every 1–3 years |

Caveats.
**AlphaFold DB postdates the 2015 and 2018 cutoffs entirely.** Including it in those evidence windows is an L2 violation; it is admissible only for the 2021 cutoff, and then only v1/v2.
**There are no ligands, cofactors, metals, ions, waters or glycans in any AFDB file.** An agent expecting HETATM records gets silent empty results, not errors.
Models are apo and monomeric: cryptic pockets are frequently modelled closed, and inter-subunit sites — a large share of real metabolite sites — do not exist in these coordinates.
Global pLDDT hides local garbage; use the per-residue confidence JSON and the `fractionPlddtVeryLow` field.
High per-domain pLDDT with high inter-domain PAE means a composite two-domain site may be geometrically meaningless.
Global pLDDT was redefined at v6 from a per-atom to a per-residue average, so v4 and v6 give systematically different numbers for the same entry — record the version in the manifest.

### 1.2 Chemistry, bioactivity and ground truth

#### ChEMBL

| | |
|---|---|
| Provides | Curated bioactivities from the medicinal-chemistry literature, target dictionary, assay metadata |
| Channel | Chemistry, ground truth (orphan status at `C`) |
| Access | REST `https://www.ebi.ac.uk/chembl/api/data/`, no key. Bulk `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_<NN>/` (SQLite/MySQL/PostgreSQL/SDF) |
| Licence | **CC BY-SA 3.0 Unported** — *"The ChEMBL data is made available on a Creative Commons Attribution-Share Alike 3.0 Unported License."* (`https://chembl.gitbook.io/chembl-interface-documentation/about`, repeated in the web UI footer) |
| Verdict | **`DERIVED-FACTS-ONLY`.** Share-alike cannot be satisfied inside an Apache-2.0 / CC BY 4.0 repo without relicensing. Commit ChEMBL IDs and our own computed values; fetch the rest |
| Archive | **Yes.** `chembl_23` (2017-07-31), `chembl_24` (2018-06-18), `chembl_24_1` (2018-12-21). Releases `chembl_01` … `chembl_37` (May 2026) all present; the 2025 mtimes on `chembl_01`–`chembl_20` are re-uploads, not release dates |
| Cadence | Irregular, roughly annual |

Caveats.
Mixed `Ki`/`IC50`/`Kd`/`EC50` with inconsistent assay context; `IC50` is substrate-concentration dependent and not interconvertible with `Ki`.
Censored values (`>`, `<`) are common and silently mis-rank under naive numeric parsing.
Heavily skewed toward druggable targets and synthetic chemistry, not endogenous metabolites.
**For DeorphBench, ChEMBL target–ligand pairs are the label, not a feature.** Any pipeline that reads current ChEMBL activities is leaking (L2); this is also why Open Targets' `sourceId=chembl` partition must be excluded.

#### BindingDB

| | |
|---|---|
| Provides | Measured binding affinities, including patent-derived data; UniProt/PubChem/DrugBank cross-maps |
| Channel | Chemistry |
| Access | REST `https://bindingdb.org/rest/` (`getLigandsByUniprot`, `getLigandsByPDBs`), no key. Bulk via `https://www.bindingdb.org/rwd/bind/chemsearch/marvin/SDFdownload.jsp?download_file=/bind/downloads/<file>` |
| Licence | **Split.** *"All data curated by BindingDB staff are provided under the Creative Commons Attribution 3.0 License."* / *"Data imported from ChEMBL are provided under their Creative Commons Attribution-Share Alike 3.0 Unported License."* (`https://www.bindingdb.org/rwd/bind/info.jsp`) |
| Verdict | BindingDB-curated subsets (`BindingDB_BindingDB_*`, `BindingDB_USPatent_*`, `BindingDB_PubChem_*`): `REDISTRIBUTABLE` under CC BY 3.0. **`BindingDB_All_*` and `BindingDB_ChEMBL_*`: `DERIVED-FACTS-ONLY`** — SA-contaminated |
| Archive | Not on the site (current month only, naming `BindingDB_<Source>_<YYYYMM>`). BindingDB directs archival users to quarterly deposits at `https://library.ucsd.edu/dc/collection/bb03870458`, explicitly recommending them *"for documentably training an AI"*. **Which vintages exist there, and whether any predate 2018, is `UNVERIFIED` — must confirm before release** (the UCSD site is behind a proof-of-work bot wall) |
| Cadence | Downloads ~monthly; archival cuts quarterly |

Caveats.
Patent-derived rows are large, single-measurement and frequently unreplicated.
`BindingDB_All` duplicates the same pair across ChEMBL/PubChem/PDSP provenance — dedupe on (target, ligand, assay, source).
Several file dates on the download page are `1969-12-31` placeholders and some sizes read 0 bytes; trust HTTP headers, not the page.

#### IUPHAR/BPS Guide to Pharmacology (GtoPdb) — primary ground truth

| | |
|---|---|
| Provides | Expert-curated receptor/transporter/enzyme–ligand pairings with **explicit endogenous-ligand annotation**, orphan receptor lists, primary literature references per interaction |
| Channel | **Ground truth** — the authoritative statement of what the field considers an agreed endogenous ligand |
| Access | Web services `https://www.guidetopharmacology.org/services/`, no key. Flat files `https://www.guidetopharmacology.org/DATA/{targets_and_families,interactions,ligands}.csv` — **verified key-free (HTTP 200) on 2026-11-07**, despite the HTML site now asking users to register |
| Licence | **ODbL (database) + CC BY-SA 4.0 (contents)** — *"The Guide to PHARMACOLOGY database is licensed under the Open Data Commons Open Database License (ODbL)."* / *"Its contents are licensed under a Creative Commons Attribution-ShareAlike 4.0 International License."* (`https://www.guidetopharmacology.org/about.jsp`) |
| Verdict | **`DERIVED-FACTS-ONLY`.** Both ODbL and CC BY-SA are share-alike: redistributing a GtoPdb-derived *database* obliges us to license it under ODbL, which the repo does not do. Commit GtoPdb object IDs, our item records, and PMIDs; fetch the rest |
| Archive | **Yes, and it is the best archive of any ground-truth source.** `https://www.guidetopharmacology.org/DATA/public_iuphardb_v<YYYY.N>.zip` — verified `application/zip`, HTTP 200, for `2016.1`, `2017.5`, `2018.1`, `2018.2`, `2018.3`, `2019.4`, `2021.3`, `2024.3`, `2025.4`, `2026.1`. The directory index itself 404s; construct URLs by version |
| Cadence | Quarterly, version `YYYY.N`. Current 2026.1 |

Caveats.
GtoPdb's curation is a *consensus* judgement, and "agreed endogenous ligand" is a committee position that sometimes lags or precedes the primary literature by years — which is exactly why §2 dates items by publication, not by the release a pairing first appeared in.
Coverage is deepest for GPCRs, NRs, ion channels and transporters and thinnest for enzymes, which biases DeorphBench's family strata.
Registration is now requested for interactive use; the bulk endpoints remain open, but that could change — the snapshot manifest's SHA-256 is our insurance.

#### ChEBI

| | |
|---|---|
| Provides | Chemical ontology, structures, roles, the identifier namespace DeorphBench uses for ligands |
| Channel | Chemistry, ground truth (ligand identity) |
| Access | REST `https://www.ebi.ac.uk/chebi/backend/api/public/compound/<id>/`, no key. Bulk `https://ftp.ebi.ac.uk/pub/databases/chebi/`. The legacy SOAP service returns HTTP 500 — treat as dead |
| Licence | **CC BY 4.0** — *"The data on this website is available under the Creative Commons License (CC BY 4.0)"* (`https://www.ebi.ac.uk/chebi/about/`) |
| Verdict | `REDISTRIBUTABLE` with attribution |
| Archive | **Yes.** `https://ftp.ebi.ac.uk/pub/databases/chebi/archive/rel<N>/` for ≥245; `https://ftp.ebi.ac.uk/pub/databases/chebi/archive/chebi_legacy/archive/rel<N>/` for ≤244, listing from rel100. **`rel159` is dated 2018-01-01** — the exact cutoff release. Versioned ontology PURLs `http://purl.obolibrary.org/obo/chebi/<N>/chebi.owl.gz`. Known data-loss gaps: `rel228` files lost, `rel240` OBO/SDF corrupt |
| Cadence | Monthly, plus a nightly ontology rebuild. Current rel256 (2026-11-04) |

Caveats.
2-star (submitted, unchecked) and 3-star (manually curated) entries are mixed in the full files; filter to 3-star for ligand work.
`is_a` and `has_role` are routinely conflated — a compound can sit under a structural `is_a` parent and a `has_role` → "drug" simultaneously, so role-based "endogenous" filtering is unreliable.
There is no explicit "endogenous in human" role; `has_role` → human metabolite (CHEBI:77746) is the nearest proxy and is curated incompletely.
Protonation state is not normalised; use Rhea's `chebi_pH7_3_mapping.tsv`.

#### Rhea

| | |
|---|---|
| Provides | Expert-curated enzymatic and transport reactions in ChEBI terms, with Swiss-Prot links |
| Channel | Chemistry (metabolite plausibility), structure (enzyme substrate priors) |
| Access | REST `https://www.rhea-db.org/rhea/?query=…&format=tsv`, SPARQL `https://sparql.rhea-db.org/sparql`, no key. FTP `ftp://ftp.expasy.org/databases/rhea/` |
| Licence | **CC BY 4.0** — *"Rhea is available under the Creative Commons Attribution 4.0 International (CC BY 4.0) License… provided you credit Rhea."* (`https://www.rhea-db.org/help/license-disclaimer`) |
| Verdict | `REDISTRIBUTABLE` with attribution and reproduction of the FTP copyright statement |
| Archive | **Partial — and it does not reach the 2018 cutoff.** `ftp://ftp.expasy.org/databases/rhea/old_releases/<N>.tar.bz2`, earliest `100.tar.bz2` dated **2018-11-26**. There is no Rhea release retrievable for 2018-01-01 |
| Cadence | ~4/year, synced to UniProt. Current release 143 (2026-11-04) |

Caveats.
Rhea is reaction scope, not occurrence: a ChEBI participating in a Rhea reaction may be a xenobiotic-metabolism substrate, not an endogenous metabolite.
Only `rhea2uniprot_sprot` is reviewed; the TrEMBL mapping is automatic.
The SMILES files are self-labelled "beta" and RDKit-computed.
Class-level reactions use ChEBI parent classes, so naive participant expansion over-generates.

#### Reactome

| | |
|---|---|
| Provides | Curated human pathways, reactions, small-molecule participants |
| Channel | Chemistry, co-expression (pathway context) |
| Access | REST `https://reactome.org/ContentService`, no key. Bulk `https://reactome.org/download/current/`, graph DB tarball |
| Licence | **Data CC0**, code Apache-2.0, illustrations CC BY 4.0 — *"Data and derived files are licensed under the Creative Commons Public Domain Dedication (CC0)"* (`https://reactome.org/license`) |
| Verdict | `REDISTRIBUTABLE`, unconditional for data. Do **not** bundle Reactome diagram images or icons on the same assumption (CC BY 4.0), and avoid FoamTree (special licence) |
| Archive | **Yes, partially.** MySQL dumps `https://download.reactome.org/<NN>/databases/gk_current.sql.gz` — verified for v60, v63, v65, v70, v75. Flat-file bundles `https://download.reactome.org/<NN>/<file>` verified only from ~v79. v63 is the release around the cutoff; **its exact date is `UNVERIFIED`** — confirm against `https://reactome.org/about/news`. Per-release Zenodo deposits from v89 (2024-06) |
| Cadence | Quarterly. Current v98 |

Caveats.
Reactome electronically infers reactions into 14 non-human species from curated human reactions via PANTHER orthology.
**Filter to `speciesName == "Homo sapiens"` and exclude `isInferred`**, or orthology projections enter as evidence.
Small molecules are often annotated as generic ChEBI classes, `DefinedSet` or `CandidateSet` rather than specific species.
"Black box events" carry no participant stoichiometry.

#### KEGG — `AVOID`

| | |
|---|---|
| Provides | Pathways, compounds, orthology |
| Channel | Would feed chemistry/pathway context |
| Access | Website free to academics. REST `rest.kegg.jp` — *"KEGG API at rest.kegg.jp is made available only for academic use by academic users."* FTP is a paid academic subscription operated by Pathway Solutions |
| Licence | **Proprietary.** *"KEGG is an original database product, copyright Kanehisa Laboratories."* *"Academic users who utilize KEGG for providing services are requested to obtain an academic service provider license."* Non-academic use requires a commercial licence (`https://www.kegg.jp/kegg/legal.html`, last updated 2024-10-01) |
| Verdict | **`AVOID`** |
| Archive | Versioned releases exist behind the paid subscription; irrelevant to us |
| Cadence | n/a |

This is not merely a "don't commit it" case.
A donated open-source project that ships an agent tool calling `rest.kegg.jp` is distributing a service built on an academic-only API, which the KEGG terms specifically ask service providers to license.
Reactome plus Rhea plus Human-GEM cover the pathway channel adequately.
If a reviewer finds a KEGG call anywhere in `src/`, we lose the licence check.

#### HMDB — `AVOID`

| | |
|---|---|
| Provides | Human metabolite reference set with concentrations, tissue locations, spectra — the single most natural candidate library for this project |
| Channel | Would be the chemistry/candidate-library backbone |
| Access | Web + bulk XML/SDF at `hmdb.ca/downloads`. The site returns HTTP 403 to automated clients |
| Licence | **CC BY-NC 4.0**, plus a separate explicit-permission clause for redistribution and commercial use. The About page states all data and metadata are released under CC BY-NC 4.0; the Citing page states that use and re-distribution for commercial purposes requires explicit permission of the authors. **`UNVERIFIED` by direct retrieval — hmdb.ca 403s automated fetches, so the verbatim wording could not be rendered on 2026-11-07. The non-commercial status itself is not in doubt** (CC BY-NC is also what PubChem records for HMDB-sourced annotations) |
| Verdict | **`AVOID`.** NC is incompatible with Apache-2.0 and with CC BY 4.0 |
| Archive | Version-numbered (1.0 2007 … 5.0 2021); current version `UNVERIFIED`. No dated release archive found |
| Cadence | Irregular, multi-year |

This is the trap the brief names, and it is a real loss.
HMDB is the best-curated statement of what molecules are actually present in human tissue, and no permissively licensed source replaces it cleanly.
Our substitute candidate library is ChEBI 3-star `has_role` → human metabolite ∪ LIPID MAPS curated ∪ Human-GEM metabolites — see §6.
Note that **pulling HMDB content through PubChem does not launder it**: PubChem records HMDB's own terms on the HMDB-sourced annotation layer.

#### LIPID MAPS

| | |
|---|---|
| Provides | LMSD lipid structures and classification |
| Channel | Chemistry (lipid candidate library) |
| Access | REST `https://www.lipidmaps.org/rest/compound/lm_id/<LMID>/all`, no key, but the site actively bot-blocks (403) — throttle and set a UA. Bulk `https://www.lipidmaps.org/files/?file=LMSD&ext=sdf.zip` |
| Licence | **CC BY 4.0** — *"All LIPID MAPS® databases are licensed under a Creative Commons Attribution 4.0 International License."* (`https://www.lipidmaps.org/terms-of-use`). The ID/InChIKey/SMILES mapping TSV is **CC0**. *Not* non-commercial, contrary to a common assumption |
| Verdict | `REDISTRIBUTABLE` with attribution; the ID TSV is unconditional |
| Archive | **None.** The download page exposes only "Last updated" with no version numbers and no dated past releases. **A 2018 LMSD state cannot be reconstructed.** Vendoring our own snapshot is both permitted and necessary |
| Cadence | Rolling; no published schedule (`UNVERIFIED`) |

Caveats.
Roughly 43% of LMSD (~22k of ~50.6k) is **computationally enumerated, not observed** — concentrated in glycerolipids (~438 curated vs ~7,378 computed) and glycerophospholipids (~2,308 vs ~8,297).
Treat computed entries as chemical possibility, never as evidence of endogenous occurrence.
The separate LMISSD in-silico database (>1.1M structures) must never enter the candidate library.
Totals differ between LIPID MAPS' own pages (50,386–50,680), so the site serves inconsistent snapshots — record our download's SHA-256.

#### Recon3D / Human-GEM

| | |
|---|---|
| Provides | Genome-scale human metabolic reconstructions: reactions, metabolites, gene–protein–reaction rules |
| Channel | Chemistry (metabolite universe), genetics (enzyme context) |
| Recon3D licence | **BiGG: UC Regents, non-profit only** — *"Permission to use, copy, modify and distribute any part of BiGG Models for educational, research and non-profit purposes… Those desiring to incorporate BiGG Models into commercial products or use for commercial purposes should contact the Technology Transfer & Intellectual Property Services, University of California, San Diego"* (`http://bigg.ucsd.edu/license`). **VMH (`vmh.life`), Recon3D's primary home, publishes no licence at all** — footer reads "© 2026 by ThieleLab/FlemingLab" and "For research purposes only" |
| Recon3D verdict | **`AVOID`.** A field-of-use restriction functionally equivalent to NC, and VMH grants nothing. Whether the new `bigg.bio` CC BY 4.0 collections cover Recon3D is `UNVERIFIED` — it is not listed among them |
| Human-GEM licence | **CC BY 4.0**, repo-wide `LICENSE.md` at `https://github.com/SysBioChalmers/Human-GEM`. That the root licence covers `model/Human-GEM.xml` is inference from a repo-wide licence with no carve-out, not an explicit sentence — `UNVERIFIED` as an explicit statement, strong as an inference |
| Human-GEM verdict | `REDISTRIBUTABLE` with attribution. **Use this instead of Recon3D** |
| Archive | Human-GEM: git tags, `https://raw.githubusercontent.com/SysBioChalmers/Human-GEM/<tag>/model/Human-GEM.xml`. Current 2.1.1 (2026-10-07). **Human-GEM did not exist in 2018** (first release ~2019) — for a 2018 cutoff the only contemporary reconstructions are HMR2 / Recon2–3D, i.e. the encumbered lineage |
| Cadence | Irregular, release-tag driven |

Caveats.
A generic reconstruction: reaction presence is not tissue- or condition-specific activity.
Many reactions are GPR-inferred or gap-filled to close mass balance and will read as false "endogenous metabolism" evidence.
Recon3D/BiGG and Human-GEM use non-interchangeable namespaces; do not union them without an explicit mapping table.

#### PubChem

| | |
|---|---|
| Provides | Compound structures and computed descriptors; aggregated annotations; BioAssay |
| Channel | Chemistry |
| Access | PUG REST `https://pubchem.ncbi.nlm.nih.gov/rest/pug/…`, no key. Bulk FTP `https://ftp.ncbi.nlm.nih.gov/pubchem/`. The HTML docs pages serve a reCAPTCHA to non-browser clients; the REST and FTP endpoints do not. Documented rate limits `UNVERIFIED` for the same reason |
| Licence | **No licence.** *"NCBI itself places no restrictions on the use or distribution of the data contained therein. However, some submitters of the original data may claim patent, copyright, or other intellectual property rights… NCBI is not in a position to assess the validity of such claims"* (`https://ftp.ncbi.nlm.nih.gov/pubchem/README`) |
| Verdict | **Split.** NCBI-computed Compound records: `REDISTRIBUTABLE` in practice. **Annotation layer: `DERIVED-FACTS-ONLY` at best** — confirmed source licences include CC BY-SA 4.0 (PharmGKB), research/education only (CTD), commercial redistribution needs author permission (HMDB), commercial copying prohibited (WHO ATC). Whitelist by `SourceName` |
| Archive | **None.** `Compound/CURRENT-Full/` is a rolling dump that is overwritten. `Compound/Monthly/` holds ~4 directories of *incremental updates*, pruned over time — not snapshots. **PubChem as of 2018-01-01 cannot be obtained from NCBI.** Snapshot at ingest |
| Cadence | Daily incrementals, weekly and monthly rollups |

Caveats.
A CID's existence carries zero evidence of biological relevance or endogeneity.
Substance records are uncurated depositor submissions with duplicate, mis-stereochemistry'd and wrong-tautomer entries aggregating into CIDs.
BioAssay is the noisiest input here: unconfirmed HTS primaries, PAINS and aggregator artefacts, frequent hitters, missing negatives, and depositor-chosen `Active` thresholds that differ across AIDs.
Deduplicate on the InChIKey skeleton block and prefer Compound-level computed properties.

#### ZINC — `AVOID` for data

| | |
|---|---|
| Provides | Purchasable and make-on-demand compound libraries, 3D conformers for docking |
| Channel | Chemistry (decoys only, if at all) |
| Access | `https://files.docking.org/2D/`, `/3D/`, `/zinc22/`; CartBlanche for 3D selection. No API key, but automated clients are captcha-gated or refused. **All docking.org hosts refused or captcha-blocked automated access on 2026-11-07**, so everything in this row is `UNVERIFIED` by direct fetch and taken from the official-domain search index |
| Licence | Free to use and download, **but** *"you may not redistribute major portions of ZINC without the express written permission of John Irwin"* (`https://wiki.docking.org/index.php?title=UCSF_ZINC_License`). Users *are* free to share the results of a ZINC screen |
| Verdict | **`AVOID`** for bulk data. `DERIVED-FACTS-ONLY` for ZINC IDs as cross-references and for our own screen outputs, which the terms explicitly bless |
| Archive | **None.** Versioning is by major release on separate hostnames (ZINC12/15/20/22); there are no dated snapshots and ZINC IDs are not stable across major versions. Purchasability is mutated in place |
| Cadence | Rolling; no published schedule |

Caveats.
ZINC's inclusion criterion is commercial purchasability, which is the wrong shape for this project: endogenous metabolites are under-represented because many are not sold, and ZINC-22's ~10^10-scale generations are largely virtual synthesis-on-demand enumerations that have never been made.
Tranche partitioning by heavy-atom count × logP means any tranche subset is a biased physicochemical slice — relevant to the L6 decoy-separability control.
One compound appears as multiple 3D protonation/tautomer forms with distinct IDs.

#### DrugBank — `AVOID`

| | |
|---|---|
| Provides | Drug–target annotations, drug structures |
| Channel | Chemistry (not endogenous ligands; included here because judges will ask) |
| Licence | **CC BY-NC 4.0** on the datasets, plus Terms of Use §1.3 limiting use to *"educational, scientific, and non-commercial research purposes"* and §2.1 prohibiting making the databases *"available to any third party"* (`https://trust.drugbank.com/drugbank-trust-center/terms-of-use`, updated 2025-09-17). Registration required; **academic downloads are currently paused** |
| Verdict | **`AVOID`.** Not even in a segregated directory — §2.1 overrides. **DrugBank Open Data** (vocabulary + structures) is **CC0** and may be used for ID mapping |
| Archive | Per-release pages `https://go.drugbank.com/releases/5-1-x`, dated and identifiable, but account-gated and currently unavailable |

### 1.3 Expression, interaction and genetics

#### STRING

| | |
|---|---|
| Provides | Functional association networks with separable evidence channels |
| Channel | Co-expression, genetics (association context) |
| Access | REST `https://string-db.org/api` (pin as `https://version-12-5.string-db.org/api`), no key except the enrichment Values/Ranks API. Bulk `https://stringdb-downloads.org/download/<file>` |
| Licence | **CC BY 4.0** — *"All data and download files in STRING are freely available under the Creative Commons Attribution 4.0 (CC BY 4.0) license."* Commercial use explicitly permitted; *"No separate permission is needed to publish the STRING outputs listed above."* There is an explicit AI clause permitting training and evaluation with attribution naming STRING **and its version** (`https://string-db.org/cgi/access?footer_active_subpage=licensing`) |
| Verdict | `REDISTRIBUTABLE` with attribution including the version. **Whether *older* releases (v10.5/v11.0) carried the same terms is `UNVERIFIED` — must confirm before release**; the archived version sites are Cloudflare-gated |
| Archive | **Partial, with a hole exactly where we need it.** Per-file-type directories exist for v11.0, v11.5, v12.0, v12.5 — e.g. `https://stringdb-downloads.org/download/protein.links.detailed.v11.0/9606.protein.links.detailed.v11.0.txt.gz` (verified, files dated 2018-12-18). Legacy ≤v9.1 at `https://stringdb-downloads.org/download/archive/v9.1/download/…`. **v10.5 and v10.0 bulk files 404 at every probed path.** v10.5 was current 2017-05-14 → 2019-01-19, i.e. on the cutoff date |
| Cadence | Irregular majors, ~18–24 months. Current v12.5 (2026-09-29) |

Caveats.
**Do not use `combined_score` in a time-split benchmark.**
It fuses text-mining and orthology-transferred evidence and is effectively contaminated by future literature.
Use `protein.links.full.*`, whose columns are `neighborhood neighborhood_transferred fusion cooccurence homology coexpression coexpression_transferred experiments experiments_transferred database database_transferred textmining textmining_transferred combined_score`, and drop `textmining*` and every `*_transferred` column.
**The text-mining channel cannot be date-filtered at all** — no per-edge PMID or date is exposed — so release pinning is the only control, and our best pin (v11.0, files dated 2018-12-18) is ~12 months past a 2018-01-01 cutoff.
Record this as a known, quantified leakage residue rather than claiming L2 is fully closed for the co-expression channel.

#### GTEx

| | |
|---|---|
| Provides | Bulk tissue RNA-seq, median TPM per tissue, eQTLs |
| Channel | Co-expression, genetics |
| Access | REST `https://gtexportal.org/api/v2/`, no key. Bulk `https://storage.googleapis.com/adult-gtex/…`, anonymous. Individual-level data is controlled access: dbGaP `phs000424` DAR + AnVIL |
| Licence | **Custom GTEx Portal Data License**, not CC. *"Downloading data from the GTEx Portal servers indicates your acceptance of the following Terms and Conditions…"* with (a) a mandatory acknowledgement string naming the portal and access date, (b) no-endorsement, and (c) *"Users who republish or redistribute the data… agree to: maintain the most current version of all distributed data, or make known in a clear and conspicuous manner that the products/services/applications do not reflect the most current/accurate data available from the GTEx Portal."* No NC, no SA |
| Verdict | Open-access summary files: `REDISTRIBUTABLE` conditional on the acknowledgement string **and** a prominent staleness notice — which pinning a release *triggers*. Controlled-access individual-level data: **never** |
| Archive | **Yes, excellent.** `https://storage.googleapis.com/adult-gtex/bulk-gex/<v7\|v8\|v10\|v11>/rna-seq/<file>`. V7 (freeze 2016-01-15) is the release current on 2018-01-01 and is still live: `…/bulk-gex/v7/rna-seq/GTEx_Analysis_2016-01-15_v7_RNASeQCv1.1.8_gene_median_tpm.gct.gz`. **The old `gs://gtex_analysis_v7` and `gs://gtex_analysis_v8` buckets are dead (404/403)** |
| Cadence | Irregular multi-year majors. Current V11 (freeze 2025-08-22) |

Caveats.
Post-mortem ischaemic time is a per-sample confounder and is exposed in the open metadata (`SMTSISCH`, with `SMRIN` and `SMATSSCR`); regress it out rather than ignoring it.
Bulk tissue conflates cell-type composition with per-cell expression.
Tissue labels churn across releases ("Cells - Transformed fibroblasts" → "Cells - Cultured fibroblasts"); V11 ships an explicit change file.
Gencode and aligner versions differ between releases, so gene ID versions do not join naively.

#### Human Protein Atlas

| | |
|---|---|
| Provides | Tissue and single-cell RNA, antibody-based IHC, subcellular localisation |
| Channel | Co-expression |
| Access | Per-gene `https://www.proteinatlas.org/<ENSG>.json`/`.tsv`; per-dataset TSVs under `/download/tsv/`. No key, no registration |
| Licence | **Version-dependent — this is the trap.** v25.0+ **CC BY 4.0**; v24 **CC BY-SA 4.0**; v18–v23 **CC BY-SA 3.0** (each confirmed at `https://v<NN>.proteinatlas.org/about/licence`). Third-party content bundled in the monolithic dump carries worse terms: **AlphaFold 3 → CC BY-NC-SA 4.0**, IUHPARDB → CC BY-SA 4.0, TCDB → CC BY-SA 3.0, MetabolicAtlas → CC BY-SA 4.0 |
| Verdict | v25.0+, HPA-generated tables only: `REDISTRIBUTABLE` with attribution. **v24 and earlier: `DERIVED-FACTS-ONLY`** (share-alike). **The monolithic `proteinatlas.tsv.zip` at any version: `DERIVED-FACTS-ONLY`** — it contains NC-SA third-party content |
| Archive | **Yes, clean and dated.** `https://v<NN>.proteinatlas.org/download/<file>` — verified for v18, v23, v24. Release dates at `https://www.proteinatlas.org/about/releases`. A 2018 pin lands on v17/v18, i.e. CC BY-SA 3.0 |
| Cadence | ~annual major plus point releases. Current v25.1 (2026-05-25) |

Caveats.
IHC is semi-quantitative and antibody-dependent; filter to reliability Enhanced/Supported and record the antibody ID.
HPA withdraws antibodies between releases for quality reasons, so protein-level calls are **not stable across versions** for the same gene.
v23 documents an Illumina-vs-MGI batch effect making prefrontal cortex incomparable to other brain regions.
v21.0 brain data has a sample-naming rotation error corrected in v21.1 — do not use v21.0 brain.

#### ARCHS4 — `AVOID`

| | |
|---|---|
| Provides | ~1.1M uniformly reprocessed human GEO RNA-seq samples, precomputed co-expression |
| Channel | Would feed co-expression |
| Access | REST `https://archs4.org/api/`, bulk H5 `https://s3.dev.maayanlab.cloud/archs4/files/<species>_<level>_v2.<minor>.h5` |
| Licence | **CC BY-NC-SA 4.0.** The terms page reads *"All data is free to use for non-commercial purposes. For commercial use please contact MSIP"* and the CC badge `href` is `creativecommons.org/licenses/by-nc-sa/4.0/` — **even though the link *text* says "Creative Commons Attribution 4.0 International License."** The mislabelling is itself a reason not to rely on this source |
| Verdict | **`AVOID`.** NC is incompatible with Apache-2.0 and CC BY 4.0; SA is additionally incompatible with Apache-2.0. The *code* (`archs4py`, Apache-2.0) is fine to depend on |
| Archive | Numbered minors are retained (`human_gene_v2.2.h5`, `v2.3`, `v2.6` verified) but **`*_v2.latest.h5` is a mutable URL overwritten on every rebuild** — rebuilds observed through 2026-11-06. There is **no date→version index**, so "ARCHS4 as of 2018-01-01" does not exist |
| Cadence | Rolling, every few weeks |

If we later obtain written clarification from the Ma'ayan lab, this becomes usable; until then it is out, and GTEx + HPA cover the co-expression channel.

#### Open Targets Platform (incl. former Open Targets Genetics)

| | |
|---|---|
| Provides | Target–disease associations by datasource, variant/study/credible-set data, expression, tractability |
| Channel | Genetics, co-expression, literature (indirectly) |
| Access | GraphQL `https://api.platform.opentargets.org/api/v4/graphql`, no key. Bulk `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/<release>/output/<dataset>/`, also `gs://open-targets-data-releases/` |
| Licence | **CC0 1.0** — *"Open Targets Platform is marked with CC0 1.0. This dedicates the data to the public domain…"* (`https://platform-docs.opentargets.org/licence`). Code Apache-2.0 |
| Verdict | Platform-generated aggregates: `REDISTRIBUTABLE`, unconditional. **Raw evidence parquet: conditional** — OT's own third-party table flags ChEMBL as CC BY-SA 3.0, HPA as CC BY-SA 3.0, and Europe PMC evidence as *"CC-BY, CC-BY-NC or CC0 … depending on publication licenses"*. Exclude `sourceId=chembl`, `sourceId=europepmc` and HPA-derived partitions before vendoring |
| Archive | **Yes, the best release tree of any source here.** Releases `16.04` through `26.09` all present; **use `17.12` for a 2018-01-01 cut.** Path schema changed at 25.03: ≤24.09 is `…/<release>/output/etl/parquet/<camelCase>/`, ≥25.03 is `…/<release>/output/<snake_case>/`, Parquet only. Never pin `latest/` |
| Cadence | Quarterly (Mar/Jun/Sep/Dec; no 24.12). Current 26.09 |

**Open Targets Genetics no longer exists as a separate resource.**
It merged into the Platform at release **25.03** (2025-03-19); `genetics.opentargets.org` now redirects to the Platform.
The standalone Genetics FTP is frozen: `https://ftp.ebi.ac.uk/pub/databases/opentargets/genetics/` lists `190303 … 22.09 latest` and nothing newer.

Caveats.
Association scores are harmonic-sum aggregations, not measurements; a high score can come entirely from one noisy source.
Decompose with `association_by_datasource_direct`.
The `Evidence` type exposes `publicationYear`, `publicationDate`, `literature`, `studyStartDate` and `evidenceDate`, so date filtering *is* implementable — but **per-`sourceId` null rates for `publicationYear` are `UNVERIFIED`**, and pinning release 17.12 is a far stronger L2 guarantee than filtering a modern release.
`sourceId=chembl` encodes known target–ligand pairs: that is label leakage, not evidence, and excluding it also removes the share-alike partition.

#### GWAS Catalog and metabolite-QTL studies

| | |
|---|---|
| Provides | Curated GWAS associations and harmonised summary statistics; metabolite traits via EFO |
| Channel | Genetics (the mQTL evidence channel) |
| Access | FTP `https://ftp.ebi.ac.uk/pub/databases/gwas/`, REST v2 `https://www.ebi.ac.uk/gwas/rest/api/v2` (100 req/min, 15 req/s, HTTP 429 over limit), no key |
| Licence | **Summary statistics CC0 1.0** *"unless otherwise specified"*, mandatory from March 2021 submissions onward; a per-study **"Usage License" column** exists on the summary-statistics download page. Non-sumstats Catalog files fall under **EMBL-EBI Terms of Use**, which impose no additional restriction but grant nothing affirmatively |
| Verdict | CC0-flagged summary statistics: `REDISTRIBUTABLE`. Pre-2021 studies and flagged studies: check the Usage License column per study. Accessions + fetch script is the safe default |
| Archive | **Yes, month-level dated full releases** — `https://ftp.ebi.ac.uk/pub/databases/gwas/releases/<YYYY>/<MM>/`, verified back to 2016 and including all of 2018. This is the cleanest true as-of snapshot of any source in this document |
| Cadence | Curated releases bi-weekly; summary statistics nightly |

Metabolite trait selection: there is no dedicated metabolite endpoint.
Use EFO `metabolite measurement` = **EFO_0004725** with `show_child_traits=true`, and the `gwas-efo-trait-mappings.tsv` file in each release directory.

**The named mQTL studies are the weakest link in this entire document.**

| Resource | Status |
|---|---|
| Metabolomics GWAS Server (Helmholtz Munich, Suhre 2011 / Shin 2014) | **`UNVERIFIED` — must confirm before release.** No licence or terms statement found; the site's TLS chain failed to verify on 2026-11-07. Interactive browse only; no bulk download or API confirmed |
| mGWAS-Explorer (`mgwas.ca`) | **`UNVERIFIED` — must confirm before release.** No licence text on the official site or the paper |
| Shin et al. 2014 (Nat Genet 46:543) | Genome-wide summary statistics availability and licence **`UNVERIFIED`** |
| Lotta et al. 2021 | **`UNVERIFIED`**; the associated Omicscience portal could not be confirmed on an official page |
| "Schlosser et al. 2023" | **`UNVERIFIED`** — the citation as given did not resolve. A metabolite-ratio GWAS deposit exists at GWAS Catalog `GCST90199621–90201020` (European) and `GCST90201021–90204063` (non-European), author attribution unconfirmed |
| "Chen et al. 2023 (UKB-PPP-adjacent)" | **`UNVERIFIED`** — no matching paper found. Related confirmed NMR work: Tambets et al., Nature 2026, GWAS Catalog `GCST90449363–GCST90451603`; licence unconfirmed |

Operating rule: any mQTL summary statistics reached **through** the GWAS Catalog inherit that study's Usage License column and are usable.
Anything reached through an author portal is not safe to vendor and must be licence-checked individually before it enters the genetics channel.

#### Pharos / TCRD

| | |
|---|---|
| Provides | Target Development Levels (Tclin/Tchem/Tbio/**Tdark**) — the operational definition of "under-characterised" used in [00-PROBLEM.md](00-PROBLEM.md) |
| Channel | Ground truth (orphan status at `C`), target selection |
| Access | GraphQL `https://pharos-api.ncats.io/graphql`, no key. Bulk MySQL dumps `http://habanero.health.unm.edu/tcrd/download/` (juniper refused TLS on 2026-11-07), no registration |
| Licence | **None asserted.** *"Data accessed from Pharos and TCRD is publicly available from the primary sources listed above… Please respect their individual licenses regarding proper use and redistribution."* (`https://pharos.nih.gov/about`). A per-source inventory exists as `TCRDv6_DataSourcesLicenses.xlsx` on the download server |
| Verdict | **`DERIVED-FACTS-ONLY`.** TCRD aggregates ChEMBL (CC BY-SA 3.0) and DrugCentral (CC BY-SA 4.0); there is no umbrella grant, so bulk-redistributing `TCRD*.sql.gz` is not defensible. NIH authorship does not launder the embedded third-party content. Commit the UniProt→TDL mapping we compute, with per-source attribution |
| Archive | **Excellent — and it is the only clean way to establish Tdark status at a past date.** `http://habanero.health.unm.edu/tcrd/download/old_versions/` holds 78 files. **`tcrd_v4.6.9.sql.gz` (2017-12-01)** is the closest to a 2018-01-01 cutoff; `tcrd_v4.6.10.sql.gz` (2018-03-21) brackets it. Naming is inconsistent: `tcrd_vX.Y.Z.sql.gz` for ≤v5, `TCRDvX.Y.Z.sql.gz` for ≥v6, with `TCRD_v6.1.0.sql.gz` as an outlier |
| Cadence | Historically 1–6 months; **bulk dumps frozen since 2023-07-11 (v6.13.4)** while the live site reports 6.13.5. CSV TDL extracts refreshed 2026 |

Caveats.
TDLs are literature- and reagent-count dependent and therefore drift with publication volume.
Tchem and Tclin are defined by ChEMBL and DrugCentral activities, so **reading current TDLs into a time-split benchmark is direct label leakage.**
Reconstruct Tdark at `C` by loading `tcrd_v4.6.9`, never by re-scoring today's literature.
The numeric TDL thresholds (PubMed score ≥5, >3 GeneRIFs, >50 antibodies) are **`UNVERIFIED` on an official page** — do not cite them without confirming.
Pharos ≠ TCRD exactly; Pharos carries some updated sources.

#### GPCRdb

| | |
|---|---|
| Provides | GPCR-specific structures, generic residue numbering, structure-based alignments, ligand annotations, orphan lists |
| Channel | Structure, chemistry, ground truth (GPCR orphan status) |
| Access | REST `https://gpcrdb.org/services/` (e.g. `/services/protein/adrb2_human/`), no key, no documented rate limit. Curated spreadsheets at `https://files.gpcrdb.org/` |
| Licence | **Data CC BY 4.0, code Apache-2.0** (`https://docs.gpcrdb.org/legal_notice.html`). Note `gpcrdb.org/pages/privacy_policy` is a 404 and the homepage carries no licence text. The legal notice adds *"the copyrights for ALL information stored in the GPCRdb belongs to the partners in the GPCRdb project unless stated otherwise"* — so spot-check records flagged as third-party |
| Verdict | `REDISTRIBUTABLE` with attribution |
| Archive | **None.** 44 releases are listed back to 2015-09-30 at `https://gpcrdb.org/pages/releasenotes`, but these are changelog entries only: no per-release download, no version-pinned subdomain, no archive directory. **GPCRdb as of 2018-01-01 is not retrievable.** The last release before the cutoff was 2017-11-15. The git history of `github.com/protwis/gpcrdb_data` is the only plausible reconstruction route and its coverage is **`UNVERIFIED` — must confirm before release** |
| Cadence | Irregular, 2–12 releases/year. Latest 2026-09-22 |

Caveats.
Structure and ligand data are imported from PDB and bioactivity resources and re-annotated, so provenance per record is mixed.
**No release pinning means any GPCRdb-derived feature is silently non-reproducible and un-time-splittable** — the worst L2 exposure of any source we intend to use.
Until the `gpcrdb_data` route is validated, GPCRdb features must be flagged leakage-prone in the run record, or restricted to generic-numbering lookups (which are stable) rather than ligand annotations (which are not).

### 1.4 Literature

Every row here is an L1 source, and the shared finding is blunt: **none of the four publishes as-of snapshots.**
Filtering today's index by publication date is *not* the same as the index as it stood at `C`, because records are retrospectively edited.
This is confirmed, not speculative, and §2 and §5 are built around it.

#### Europe PMC

| | |
|---|---|
| Provides | Abstracts, OA full text, preprint records, text-mined annotations |
| Channel | Literature |
| Access | REST `https://www.ebi.ac.uk/europepmc/webservices/rest/` (v6.9), annotations API `/europepmc/annotations_api/`, **no key**. Rate limits **undocumented → `UNVERIFIED`**; be polite. Bulk under `https://europepmc.org/ftp/…` (the site 403s automated clients) |
| Licence | **No single licence.** *"Bulk downloading of articles from the main Europe PMC site, in any way, is prohibited because of copyright restrictions."* Articles obtained via the permitted services *"are still protected by copyright, but are distributed under a Creative Commons or similar license."* The **OA subset** is per-article CC and *"The license terms are not identical for all articles in this subset."* The **author-manuscript collection** grants no open licence — only *"These files are available for text mining."* Non-OA full text is not fetchable at all (verified: `rest/<PMCID>/fullTextXML` returns 200 for OA, 404 for non-OA) |
| Verdict | IDs and metadata: `REDISTRIBUTABLE` with attribution. Abstracts: `FETCH-ONLY`. OA full text: `DERIVED-FACTS-ONLY` unless we track per-article licences and exclude NC/ND. Author manuscripts and non-OA: **`AVOID`** |
| Archive | **No dated snapshots** — FTP files are "latest" only and `DOI_mappings` is explicitly overwritten monthly. Date filtering works: `FIRST_PDATE:[2017-12-01 TO 2017-12-31]`. Fields present: `FIRST_PDATE`, `P_PDATE`, `E_PDATE`, `FIRST_IDATE`, `CREATION_DATE`, `INDEX_DATE`, `UPDATE_DATE`, `PUB_YEAR`. **There is no `PDATE` field**; the print/electronic split is `P_PDATE`/`E_PDATE`. Field *semantics* are not officially documented → `UNVERIFIED` beyond the names |
| Cadence | Index daily; OA XML weekly; OA PDF and DOI mappings monthly |

Caveats.
`firstIndexDate` ≠ publication date, and the gap can be years: a live example has `firstPublicationDate` 2017-12-31 and `firstIndexDate` 2019-03-26.
**Filtering today's index by `FIRST_PDATE < C` therefore systematically over-includes records that did not exist in Europe PMC at `C`.**
Closing L1 properly requires constraining `FIRST_IDATE`/`CREATION_DATE` as well — and even then the abstract text returned is today's, not 2018's.
A preprint and its journal version are separate records (`SRC:PPR` with a `PPRxxxxx` ID vs `SRC:MED` with a PMID), so earliest-publication dating requires querying both and linking by DOI.

#### OpenAlex

| | |
|---|---|
| Provides | Scholarly works graph: IDs, dates, authors, concepts, citations, inverted abstracts |
| Channel | Literature |
| Access | API `https://api.openalex.org`. **Changed in 2026**: the `mailto` polite pool is gone; unauthenticated calls share a $0.10/day budget per IP at 10 req/s, a free key gives $1/day at 30 req/s (`https://help.openalex.org/api/authentication`). Snapshot `s3://openalex`, **not** requester-pays, `--no-sign-request` |
| Licence | **CC0 1.0** — *"Our data is CC0, our code is open source, and our governance is transparent."* `LICENSE.txt` in the bucket is the full CC0 text |
| Verdict | IDs and metadata: `REDISTRIBUTABLE`, unconditional. **Abstracts: `DERIVED-FACTS-ONLY`** — OpenAlex's CC0 covers its records, but reconstituting and republishing abstract text re-exposes publisher copyright |
| Archive | **Partitioned by `updated_date`, which is not an as-of date.** Current layout `s3://openalex/data/jsonl/works/updated_date=YYYY-MM-DD/part_NNNN.gz` (and `data/parquet/…`); the pre-2026 layout moved to `legacy-data/`. A 2017 work edited in 2026 lives *only* under a 2026 partition. `from_publication_date`/`to_publication_date` filters work and are free; **`from_created_date`/`from_updated_date` are now paid sync filters**, which removes the cheap "everything created before X" trick |
| Cadence | Rolling; new `updated_date=` partitions roughly weekly-to-monthly |

Caveats.
Works get merged and IDs retired into `deleted_ids.csv.gz`, so stored OpenAlex IDs rot.
`cited_by_count` is re-inferred and is never a time-stamped fact.
`is_retracted` is populated retroactively, so a 2018 reconstruction from today's data "knows" about retractions unknown in 2018 — a genuine L1 leak.
`publication_date` is often the journal issue date, not the earliest appearance.

#### PubMed / MEDLINE

| | |
|---|---|
| Provides | Citations, abstracts, MeSH indexing |
| Channel | Literature |
| Access | E-utilities `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` — **3 req/s without a key, 10 req/s with**, the cap applying per key across all IPs. Bulk `https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/` + `updatefiles/` |
| Licence | **No open licence — a terms-and-conditions grant.** *"NLM freely provides PubMed data. Please note some abstracts may be protected by copyright."* Users agree to acknowledge NLM conspicuously, not use the PubMed wordmark, not imply endorsement, and — critically for us — *"maintain the most current version of all distributed data, or make known in a clear and conspicuous manner that the products/services/applications do not reflect the most current/accurate data available from NLM"* (`https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/README.txt`) |
| Verdict | IDs, titles, journals, MeSH, dates: `REDISTRIBUTABLE` subject to those extra obligations — so a `NOTICE` file is mandatory and the data is **not** relicensable as CC BY 4.0. **Abstracts: `AVOID`** — NLM explicitly disclaims the ability to grant them |
| Archive | **Only the current baseline.** `pubmed26n####.xml.gz` is the 2026 baseline, released December 2025. `https://ftp.ncbi.nlm.nih.gov/pubmed/` contains only `baseline/`, `updatefiles/` and beta variants — **prior-year baselines are not retained. A 2018 baseline is unobtainable from NLM.** Date fields: `[dp]` publication, `[epdat]` electronic only, `[ppdat]` print only, `[crdt]` record creation, `[edat]` entry, `[lr]` last revision, `[mhda]` MeSH date |
| Cadence | Annual baseline each December; daily updates |

Caveats.
`[dp]` collapses print and electronic dates and pads missing components (a bare "2017" becomes 2017-01-01), distorting year-boundary splits.
Ahead-of-print records **change their publication date** when the issue appears, so `[dp]` is mutable.
MeSH indexing is applied after record creation (`mhda` diverges from `edat`), so **MeSH terms on an old record today were frequently absent on 2018-01-01** — a MeSH-based retrieval benchmark leaks forward by construction.
Update files contain revised and deleted citations; `deleted.pmids.gz` exists.
Since a frozen snapshot is required by [04-EVALUATION.md §2 L2](04-EVALUATION.md), the NLM staleness clause obliges us to label it as not current — do so in `data/third_party/pubmed/NOTICE`.

#### bioRxiv / medRxiv

| | |
|---|---|
| Provides | Preprint metadata and full text; **version-1 posting dates** |
| Channel | Literature, and the earliest-publication clock for §2 |
| Access | REST `https://api.biorxiv.org/details/<server>/<interval>/<cursor>/<format>`, 30 results/page, no key, rate limits undocumented (`UNVERIFIED`). Bulk TDM `s3://biorxiv-src-monthly` and `s3://medrxiv-src-monthly`, **us-east-1, requester-pays** (an AWS account is required) |
| Licence | **Per-preprint, author-chosen**: no-reuse-without-permission (`cc_no`), CC BY, CC BY-NC, CC BY-ND, CC BY-NC-ND, or CC0 — the value is in the API's `license` field per version. TDM terms: the bulk repository *"is not intended as a source for further redistribution of articles posted on bioRxiv"* and does not grant *"permission to re-host content"*; tools must link back |
| Verdict | DOIs, dates, versions, licence field: `REDISTRIBUTABLE` with attribution. Abstracts: `FETCH-ONLY`, tracking the per-preprint licence. **Full text: `AVOID`** — re-hosting is explicitly disclaimed and many preprints are ND or `cc_no` |
| Archive | **Version rows are append-only and expose v1 distinctly** — `/details/biorxiv/<DOI>` returns one row per version with its own `date`, `version` and `license`. `min(date where version == 1)` is the authoritative original posting date. `/details/` interval filtering is by posting date, so "everything posted before 2018-01-01" is directly enumerable. No official as-of snapshots; S3 packages are monthly batches |
| Cadence | Continuous; S3 TDM packages monthly |

Caveats.
`published`, `published_doi` and `published_journal` are **backfilled** when a preprint is later journal-published: pure hindsight, and a direct leakage vector.
Ignore them entirely when reconstructing what was known at `C`.
One DOI maps to many version rows — collapse on DOI and take v1 for dating.
The same work appears as a bioRxiv record, a Europe PMC `SRC:PPR` record and a PubMed record: three IDs, three dates.
`license` varies per version, so a v2 can be more permissive than v1.

---

## 2. Ground-truth provenance for DeorphBench

The benchmark makes two claims per item, and they need different evidence.

| Claim | What establishes it |
|---|---|
| **Protein P was an orphan at cutoff `C`** | Absence of an agreed endogenous ligand in a *contemporaneous* snapshot. Criterion I1 in [04-EVALUATION.md §1.2](04-EVALUATION.md) |
| **Ligand L was assigned to P after `C`** | Presence of the pairing in a *current* curated resource, dated by the earliest primary publication reporting the binding. Criteria I2, I3 |

### 2.1 Recommended sources

**Primary: IUPHAR/BPS Guide to Pharmacology.**
It is the only resource that curates *endogenous* ligand status as a distinct, committee-adjudicated judgement rather than inferring it from bioactivity volume, and it maintains explicit orphan lists.
Crucially for us, it has a **true dated archive**: `public_iuphardb_v<YYYY.N>.zip` back to 2016.1, verified as real zip files.
So orphan status at `C = 2018-01-01` is read from `v2017.5` (the release immediately preceding the cutoff), and the post-cutoff assignment is read from the freeze release `F`.
The `interactions.csv` export carries per-interaction PMIDs, which is what makes step 2.2 possible.

**Corroborating: Pharos / TCRD** for orphan status, and **UniProt + ChEMBL** for the negative check.
TCRD is the right corroborator because its archive is equally good — `tcrd_v4.6.9.sql.gz` (2017-12-01) brackets the cutoff — and because it encodes "under-characterised" through an independent definition (Target Development Level) rather than through ligand curation.
A protein that is `Tdark` or `Tbio` in TCRD v4.6.9 **and** carries no endogenous ligand in GtoPdb v2017.5 **and** has no `BINDING` feature with an experimental ECO code in UniProt `release-2018_01` **and** no small-molecule activity in `chembl_23` is an orphan by four independent definitions.
Requiring all four is deliberately conservative: it shrinks the positive set, which [04-EVALUATION.md §9](04-EVALUATION.md) already flags as small, but a contested orphan designation destroys an item's value entirely.

For GPCRs specifically, GPCRdb would be the natural fifth check — but it has **no dated archive**, so it can only corroborate the *present* state, never the state at `C`.
Use it for the current-orphan `true-orphan-hold` control, not for I1.

### 2.2 Dating an assignment by earliest primary publication

**The database release in which a pairing first appears is not the date of the discovery, and using it would invalidate the benchmark.**
GtoPdb curates in quarterly waves; a 2016 paper can first appear in a 2019.2 release.
If we dated by release, that item would count as a post-2018 "discovery" the loop was supposed to find, while the paper reporting it sat inside the evidence window the whole time.
The loop would then be rewarded for reading the answer — an L1 leak that produces a good number for the worst possible reason.
This is why [04-EVALUATION.md §1.3](04-EVALUATION.md) names earliest primary publication as the mitigation, and the procedure is:

1. **Extract the reference set.** From GtoPdb `interactions.csv` at freeze `F`, take every PMID attached to the P–L interaction. Add the references on the ligand and target pages. This is the candidate set of papers that could have first reported the binding.
2. **Filter to primary evidence.** Keep only papers reporting a direct binding or activity measurement on P and L (criterion I3). Reviews, commentaries and database-citation entries are dropped here, not later. A pre-cutoff review that *speculates* about L is not an assignment — but it is recorded as `prior_speculation: true`, because [04-EVALUATION.md §1.3](04-EVALUATION.md) requires recovery rates to be reported split by that flag.
3. **Resolve each surviving paper to its earliest public appearance.** Take the minimum across four clocks:
   - bioRxiv/medRxiv `min(date where version == 1)` via `api.biorxiv.org` — the cleanest clock, append-only, and the only one that reliably predates journal publication;
   - Europe PMC `SRC:PPR` `FIRST_PDATE` for preprints not on bioRxiv/medRxiv;
   - PubMed `[epdat]` (electronic publication date) — **not** `[dp]`, which is padded and mutable for ahead-of-print records;
   - journal `[dp]` as the fallback when no electronic date exists.
   Link across clocks by DOI. Record **all** resolved dates in the item, not just the minimum, so the choice is auditable.
4. **Set `first_assignment_date` = the minimum over step 3**, and `date_confidence` per [04-EVALUATION.md §1.3](04-EVALUATION.md):
   - `high` — a DOI-linked preprint or electronic publication date, and the paper's primary evidence is unambiguous;
   - `medium` — journal `[dp]` only, or a one-month padding ambiguity near the cutoff;
   - `low` — year-only date, conflicting clocks more than six months apart, or the primary paper could not be identified from the curated references.
5. **Corroborate independently.** Look up the same pairing in ChEMBL and in the literature directly (Europe PMC query on P and L), and record whether an earlier primary report exists that GtoPdb did not cite. If one does, use it and set `date_confidence: medium` at best — GtoPdb's reference list having been incomplete is evidence that our dating may be too.
6. **Reject items whose earliest primary publication precedes `C`.** These are not post-cutoff discoveries regardless of what any database release says.

Step 6 is the one that does the real work, and it will discard items that look attractive.
That is the point.

A residual honesty note for the run record: steps 3–5 use *today's* Europe PMC and PubMed indexes, and §1.4 establishes that those indexes have been retrospectively edited.
For dating this is acceptable — we are asking when a paper appeared, not what the index said in 2018 — but the same indexes must not be used to decide what the loop could retrieve at `C`. Those are different queries and the date-filter MCP layer (L1) must keep them separate.

---

## 3. Redistribution decision table

What may physically exist in this git repository.
Columns: **Raw** = source data files; **Derived** = identifiers plus our own computed values; **Fetch** = an ID list plus a script that retrieves at runtime.
Where Raw is allowed, the files go in `data/third_party/<source>/` with their own `LICENSE` and `NOTICE`, and are listed in `ATTRIBUTION.md`.

| Source | Licence | Raw | Derived | Fetch script | What actually lives in the repo |
|---|---|---|---|---|---|
| UniProt / Swiss-Prot | CC BY 4.0 | ✅ | ✅ | ✅ | Per-target FASTA + filtered feature TSV for benchmark targets, with NOTICE |
| InterPro / Pfam | CC0 1.0 | ✅ | ✅ | ✅ | Domain assignments for benchmark targets |
| RCSB PDB | CC0 1.0 | ✅ | ✅ | ✅ | Snapshot-pinned mmCIF for benchmark targets; CCD exclusion list |
| PDBe (archive) | CC0 1.0 | ✅ | ✅ | ✅ | SIFTS mappings |
| PDBe-KB (aggregate) | CC BY 4.0 (contributors `UNVERIFIED`) | ⚠️ | ✅ | ✅ | **IDs + fetch script only** until per-contributor terms are confirmed |
| AlphaFold DB | CC BY 4.0 | ✅ | ✅ | ✅ | Per-target `.cif` + confidence JSON, version-pinned. **Not for 2015/2018 cutoffs** |
| AlphaFold `collaborations/` | `UNVERIFIED` | ❌ | ❌ | ❌ | Nothing |
| ChEMBL | CC BY-SA 3.0 | ❌ | ✅ | ✅ | CHEMBL IDs, our own scores, fetch script |
| BindingDB (curated subsets) | CC BY 3.0 | ✅ | ✅ | ✅ | Non-ChEMBL subset files only |
| BindingDB `_All` / `_ChEMBL` | CC BY-SA 3.0 | ❌ | ✅ | ✅ | IDs + fetch script |
| **GtoPdb** | ODbL + CC BY-SA 4.0 | ❌ | ✅ | ✅ | **Benchmark item records, GtoPdb object IDs, PMIDs, version pin + SHA-256. Not the CSVs** |
| ChEBI | CC BY 4.0 | ✅ | ✅ | ✅ | 3-star subset for the candidate library, with NOTICE |
| Rhea | CC BY 4.0 | ✅ | ✅ | ✅ | `chebi_pH7_3_mapping.tsv`, reaction participant table |
| Reactome | CC0 (data) | ✅ | ✅ | ✅ | `ChEBI2Reactome` mapping. **Not** diagrams or icons |
| **KEGG** | Proprietary | ❌ | ❌ | ❌ | **Nothing. No code path may call `rest.kegg.jp`** |
| **HMDB** | CC BY-NC 4.0 | ❌ | ❌ | ❌ | **Nothing.** See §4 for the derived-facts caveat |
| LIPID MAPS | CC BY 4.0 (ID TSV CC0) | ✅ | ✅ | ✅ | Curated-only LMSD subset + the CC0 ID TSV. **Exclude computed entries and all of LMISSD** |
| Recon3D (BiGG / VMH) | Non-profit only / none | ❌ | ❌ | ❌ | Nothing |
| Human-GEM | CC BY 4.0 | ✅ | ✅ | ✅ | `model/Human-GEM.xml` at a pinned tag |
| STRING | CC BY 4.0 | ✅ | ✅ | ✅ | `protein.links.full` subset for benchmark targets, **textmining and `*_transferred` columns dropped at ingest** |
| GTEx | Custom GTEx licence | ⚠️ | ✅ | ✅ | Median-TPM slice for benchmark targets + acknowledgement + **staleness notice**. Never individual-level data |
| HPA v25+ (per-dataset TSV) | CC BY 4.0 | ✅ | ✅ | ✅ | `rna_tissue_consensus` slice |
| HPA ≤ v24, or any monolithic dump | CC BY-SA, embeds CC BY-NC-SA | ❌ | ✅ | ✅ | Derived expression ranks only |
| **ARCHS4** | CC BY-NC-SA 4.0 | ❌ | ❌ | ❌ | Nothing. `archs4py` (Apache-2.0) may be a dependency |
| Open Targets Platform | CC0 1.0 | ✅ | ✅ | ✅ | Association tables **excluding `sourceId` in {chembl, europepmc} and HPA-derived partitions** |
| Open Targets Genetics | merged into Platform at 25.03 | — | — | — | Use Platform; cite the frozen 22.09 tree only for historical runs |
| GWAS Catalog (CC0 sumstats) | CC0 1.0 | ✅ | ✅ | ✅ | Metabolite-trait association slice from a dated release |
| GWAS Catalog (other files) | EBI ToU | ⚠️ | ✅ | ✅ | Accessions + fetch script |
| mQTL portals (Helmholtz, mGWAS-Explorer, author sites) | `UNVERIFIED` | ❌ | ❌ | ⚠️ | **Nothing until licences are confirmed.** Reach mQTL data through the GWAS Catalog instead |
| Europe PMC (IDs/metadata) | no explicit grant | ⚠️ | ✅ | ✅ | PMIDs/PMCIDs/DOIs + dates |
| Europe PMC (abstracts, OA full text) | per-article CC incl. NC/ND | ❌ | ✅ | ✅ | Runtime cache only, outside the repo, gitignored |
| Europe PMC (author manuscripts, non-OA) | no open licence | ❌ | ❌ | ❌ | Nothing |
| OpenAlex (records) | CC0 1.0 | ✅ | ✅ | ✅ | Work IDs, dates, DOI links |
| OpenAlex (abstract text) | publisher copyright | ❌ | ✅ | ✅ | Inverted index re-fetched at runtime |
| PubMed (IDs, MeSH, dates) | NLM T&C | ✅ | ✅ | ✅ | With `NOTICE` carrying NLM attribution, no-endorsement and the staleness disclaimer |
| PubMed (abstracts) | publisher copyright | ❌ | ✅ | ✅ | Runtime cache only, gitignored |
| bioRxiv / medRxiv (metadata) | no explicit grant | ⚠️ | ✅ | ✅ | DOIs, v1 dates, version rows, per-version `license` field |
| bioRxiv / medRxiv (full text) | per-preprint, re-hosting disclaimed | ❌ | ✅ | ✅ | Links only |
| Pharos / TCRD | none asserted; embeds SA | ❌ | ✅ | ✅ | UniProt→TDL mapping we compute from a pinned dump |
| GPCRdb | CC BY 4.0 | ✅ | ✅ | ✅ | Generic-numbering tables. Ligand annotations flagged non-reproducible |
| PubChem (Compound, NCBI-computed) | no NCBI restriction | ✅ | ✅ | ✅ | CID↔InChIKey map for the candidate library |
| PubChem (annotation layer) | heterogeneous, incl. NC and SA | ❌ | ⚠️ | ✅ | Nothing without a `SourceName` whitelist |
| **ZINC** | no redistribution of major portions | ❌ | ✅ | ⚠️ | ZINC IDs only; our own screen results are explicitly permitted |
| **DrugBank** | CC BY-NC 4.0 + no-third-party | ❌ | ❌ | ❌ | Nothing. DrugBank **Open Data** (CC0) may be vendored for ID mapping |

Legend: ✅ permitted · ⚠️ permitted only under the stated condition, default to the stricter option · ❌ forbidden.

When in doubt, the row collapses to "IDs + a fetch script".
That costs a user one download and costs us nothing.

---

## 4. The derived-facts question

Suppose we compute a docking score using an HMDB structure, or fit a calibration curve on ChEMBL affinities.
May we publish the score?

**We do not know for certain, and anyone who tells you otherwise is overstating the law.**
Here is the actual shape of the uncertainty.

The strongest argument *for* release is that a number computed from a fact is not a copy of the database.
Copyright protects expression and (in the EU, separately) substantial extraction from a database — not facts, and not the output of an independent computation.
A docking score is our creative and computational output; the molecular structure of a metabolite is a fact about the world that HMDB recorded but did not invent.
Under US law, *Feist* means a compilation's facts are not protected even when the compilation is.

The arguments *against* are real and we take them seriously.
First, the EU **sui generis** database right protects substantial extraction and re-utilisation regardless of originality, and "I transformed it first" is not obviously a defence if the transformation is mechanical and the output preserves the structure of the original selection.
Second, CC BY-NC and CC BY-SA are **contracts we accept by using the data**, not merely copyright statements, and both have an "adapted material" concept that is drawn broadly.
CC BY-SA 4.0 §1(a) defines adapted material to include work in which the licensed material is "translated, altered, arranged, transformed, or otherwise modified in a manner requiring permission".
Whether a score is adapted material or merely informed by the data is exactly the question nobody has litigated for scientific databases, and reasonable lawyers disagree.
Third — and this is the part that actually decides our behaviour — **a hackathon judge checking licence consistency is not running a legal analysis. They are looking for whether we used HMDB.**

### Our policy

| Case | Policy |
|---|---|
| Scores computed from an `AVOID` source (HMDB, KEGG, DrugBank, ARCHS4, ZINC, Recon3D) | **Do not release, and do not compute them in the default configuration.** The pipeline must run without these sources. If we ever use them for an internal comparison, that configuration is reported as an ablation and its numbers are marked as not reproducible from the public repo |
| Scores computed from a share-alike source (ChEMBL, GtoPdb, HPA ≤ v24, BindingDB `_All`, TCRD) | **Release the score; do not release the inputs.** Record the source, version and SHA-256 in the manifest so a reader can regenerate the input themselves under its own licence. Treat the score as ours, the input as theirs |
| Identifiers from any source | **Always releasable.** An accession is a reference, not content. This is the position every bioinformatics resource operates on in practice |
| Aggregate counts and statistics over any source | **Releasable**, provided they are not reconstructive — "412 of 1,109 targets had a ChEBI role annotation" is fine; a table that lets someone rebuild the source row by row is not |
| Anything we are unsure about | **Ship the script, not the output.** Reproducibility is preserved and the licence question disappears |

### What we are not claiming

We are not claiming that computing on HMDB and releasing the result is legally safe.
We are claiming that we **did not do it**, which is a much easier thing to verify and a much easier thing to defend.
The cold-start set in §6 exists precisely so that this claim is structurally true rather than a promise: the loop's default configuration has no code path to an `AVOID` source, and `tests/controls/test_no_avoid_sources.py` asserts it by checking that no hostname in the `AVOID` list appears in any resolved tool endpoint during a benchmark run.

If a reviewer disagrees with the share-alike row above and believes a derived score is adapted material, the remedy is small: those scores come from four sources, each is tagged in the manifest, and removing them costs us the chemistry channel on a subset of items rather than the project.
We would rather state that exposure than hide it.

---

## 5. Snapshot manifest format

One manifest per run, written before any agent executes, hashed into the run record per [04-EVALUATION.md §0.2](04-EVALUATION.md).
A run whose manifest does not validate does not produce reportable numbers.

### Schema

```yaml
# snapshots/<run-id>/manifest.yaml
manifest_version: 1
run_id: string                    # matches runs/<run-id>/
cutoff_date: date                 # C — the evidence-window boundary
freeze_date: date                 # F — when ground truth was read
created_at: datetime              # UTC, ISO 8601
created_by: string                # tool version that wrote this

sources:
  - name: string                  # canonical short name, matches §1 and §3
    role: enum                    # evidence | ground_truth | candidate_library | mapping
    channel: enum                 # structure | literature | chemistry | coexpression | genetics | none
    version: string               # the source's own release identifier, verbatim
    version_is_dated: bool        # true if the release maps to a date the source publishes
    release_date: date | null     # null when the source publishes none — this is a reproducibility flag
    retrieval_date: date          # when WE fetched it
    cutoff_compliant: enum        # yes | approximate | no
    cutoff_note: string | null    # REQUIRED when cutoff_compliant != yes
    url: string                   # exact URL fetched, no "latest" aliases
    sha256: string                # of the retrieved artefact as stored
    bytes: integer
    record_count: integer         # rows / entries / structures, as applicable
    record_count_definition: string
    license:
      name: string                # exact licence name
      url: string                 # the page we read it from
      verdict: enum               # REDISTRIBUTABLE | FETCH-ONLY | DERIVED-FACTS-ONLY | AVOID
      verified_on: date
      verified_by: string
    in_repo: enum                 # raw | derived | none
    filters_applied: [string]     # ingest-time exclusions, e.g. dropped columns
```

`cutoff_compliant` is the field the evaluation actually depends on.

| Value | Meaning |
|---|---|
| `yes` | The source publishes a dated release at or before `C` and we pinned it. Example: PDB snapshot `20180101` |
| `approximate` | We pinned the nearest available release and it does not sit at `C`. **`cutoff_note` must quantify the gap.** Example: STRING v11.0, files dated 2018-12-18, ~12 months past a 2018-01-01 cutoff |
| `no` | The source serves current state only. The item is a known L2 exposure and must appear in the run record's limitations section. Example: PDBe-KB, GPCRdb, LIPID MAPS |

The report generator refuses to emit headline metrics if any source with `role: evidence` has `cutoff_compliant: no` and is not listed in the pre-registration's accepted-exposures block.

### Worked example

```yaml
manifest_version: 1
run_id: 2026-11-07-loop-v0.3-deorphbench-c2018
cutoff_date: 2018-01-01
freeze_date: 2026-11-01
created_at: 2026-11-07T09:14:02Z
created_by: msf-snapshot/0.3.1

sources:
  - name: uniprot_swissprot
    role: evidence
    channel: structure
    version: "2018_01"
    version_is_dated: true
    release_date: 2018-01-31
    retrieval_date: 2026-11-07
    cutoff_compliant: approximate
    cutoff_note: >-
      UniProt release 2018_01 is the first release of 2018 and was published 2018-01-31,
      30 days after the cutoff. The preceding release 2017_12 is not in previous_releases.
      Entries modified in January 2018 are therefore visible. Quantified exposure:
      1,204 human entries carry a modification date in [2018-01-01, 2018-01-31].
    url: https://ftp.uniprot.org/pub/databases/uniprot/previous_releases/release-2018_01/knowledgebase/complete/uniprot_sprot.dat.gz
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"  # filled by fetcher
    bytes: 573419882
    record_count: 556825
    record_count_definition: reviewed entries in uniprot_sprot.dat
    license:
      name: Creative Commons Attribution 4.0 International
      url: https://www.uniprot.org/help/license
      verdict: REDISTRIBUTABLE
      verified_on: 2026-11-07
      verified_by: scripts/verify_licenses.py
    in_repo: raw
    filters_applied:
      - "taxonomy:9606"
      - "evidence: kept ECO:0000269 only for BINDING/ACT_SITE/COFACTOR features"

  - name: rcsb_pdb
    role: evidence
    channel: structure
    version: "snapshot-20180101"
    version_is_dated: true
    release_date: 2018-01-01
    retrieval_date: 2026-11-07
    cutoff_compliant: yes
    cutoff_note: null
    url: s3://pdbsnapshots/20180101/pub/pdb/data/structures/divided/mmCIF/
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"  # of the per-target tar we assemble
    bytes: 41203887
    record_count: 1109
    record_count_definition: mmCIF entries retrieved for DeorphBench target set
    license:
      name: CC0 1.0 Universal Public Domain Dedication
      url: https://www.rcsb.org/pages/usage-policy
      verdict: REDISTRIBUTABLE
      verified_on: 2026-11-07
      verified_by: scripts/verify_licenses.py
    in_repo: raw
    filters_applied:
      - "excluded CCD codes: GOL EDO PEG PG4 1PE SO4 PO4 ACT DMS MES TRS EPE"
      - "biological assembly 1 only"

  - name: gtopdb
    role: ground_truth
    channel: none
    version: "2017.5"
    version_is_dated: true
    release_date: 2017-12-01   # UNVERIFIED to the day; quarter is 2017.5
    retrieval_date: 2026-11-07
    cutoff_compliant: yes
    cutoff_note: >-
      Used for I1 (orphan status at C) only. The freeze-date release 2026.1 is recorded
      as a separate source entry with role: ground_truth and cutoff_compliant: no,
      which is correct — ground truth is read after C by construction.
    url: https://www.guidetopharmacology.org/DATA/public_iuphardb_v2017.5.zip
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    bytes: 0
    record_count: 0
    record_count_definition: interaction rows in the interaction table
    license:
      name: Open Data Commons Open Database License (ODbL) + CC BY-SA 4.0 (contents)
      url: https://www.guidetopharmacology.org/about.jsp
      verdict: DERIVED-FACTS-ONLY
      verified_on: 2026-11-07
      verified_by: manual
    in_repo: derived
    filters_applied:
      - "endogenous ligand interactions only"
      - "human targets only"

  - name: string_db
    role: evidence
    channel: coexpression
    version: "v11.0"
    version_is_dated: false
    release_date: 2019-01-19
    retrieval_date: 2026-11-07
    cutoff_compliant: approximate
    cutoff_note: >-
      v10.5 was current on 2018-01-01 but its bulk files return 404 at every known path
      (checked 2026-11-07). v11.0 is the oldest retrievable modern release; its files are
      dated 2018-12-18, ~12 months past the cutoff. Residual L2 exposure accepted and
      declared in prereg/loop-v0.3.yaml. Mitigated by dropping the textmining and
      orthology-transferred columns, which cannot be date-filtered at all.
    url: https://stringdb-downloads.org/download/protein.links.full.v11.0/9606.protein.links.full.v11.0.txt.gz
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    bytes: 110085813
    record_count: 11759454
    record_count_definition: scored protein pairs for taxid 9606
    license:
      name: Creative Commons Attribution 4.0 International
      url: https://string-db.org/cgi/access?footer_active_subpage=licensing
      verdict: REDISTRIBUTABLE
      verified_on: 2026-11-07
      verified_by: scripts/verify_licenses.py
    in_repo: derived
    filters_applied:
      - "dropped columns: textmining, textmining_transferred"
      - "dropped columns: *_transferred (all channels)"
      - "dropped column: combined_score"

  - name: gpcrdb
    role: evidence
    channel: structure
    version: "fetched-2026-11-07"
    version_is_dated: false
    release_date: null
    retrieval_date: 2026-11-07
    cutoff_compliant: no
    cutoff_note: >-
      GPCRdb publishes release notes but no downloadable past releases and no version-pinned
      API. The state at C is not retrievable. Restricted to generic residue numbering, which
      is stable across releases; ligand annotations are EXCLUDED from this run. Declared as
      an accepted exposure in prereg/loop-v0.3.yaml with the restriction as the mitigation.
    url: https://gpcrdb.org/services/residues/extended/
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
    bytes: 0
    record_count: 0
    record_count_definition: residues with generic numbering for target set
    license:
      name: Creative Commons Attribution 4.0 International
      url: https://docs.gpcrdb.org/legal_notice.html
      verdict: REDISTRIBUTABLE
      verified_on: 2026-11-07
      verified_by: manual
    in_repo: derived
    filters_applied:
      - "generic numbering only; ligand and bioactivity fields discarded at ingest"
```

Three things this example is designed to show.
`cutoff_note` carries a **quantified** gap, not an apology.
A source with `cutoff_compliant: no` is still usable if its contribution is restricted to something release-invariant, and the restriction is machine-checkable via `filters_applied`.
And the ground-truth source appears twice — once at `C` for orphan status and once at `F` for the assignment — because conflating them is how a time split silently becomes a random split.

---

## 6. Cold-start minimal data set

The smallest configuration that runs the loop end to end on one target.
Every source here is **key-free**, needs **no registration**, and is either CC0, CC BY 4.0, or derived-facts-only with a usable archive.
Nothing on the `AVOID` list appears, and nothing requires an AWS account, a dbGaP DAR, or a paid tier.

| # | Source | Pin | What it supplies | Size |
|---|---|---|---|---|
| 1 | **UniProt Swiss-Prot** | `release-2018_01`, single entry via UniSave | Sequence, existing annotations, orphan check | ~50 KB |
| 2 | **InterPro** | current release, REST per-accession | Domain assignment, family prior baseline | ~20 KB |
| 3 | **RCSB PDB** | snapshot `20180101`, target's entries only | Experimental structure if any; L5 flag if a holo structure exists | 0–5 MB |
| 4 | **AlphaFold DB** | v4 single entry — **only for cutoff ≥ 2021**; otherwise omit and rely on 3 | Predicted apo structure, pLDDT, PAE | ~2 MB |
| 5 | **ChEBI** | `rel159` (2018-01-01), 3-star subset | Candidate library backbone + ligand ID namespace | ~80 MB |
| 6 | **LIPID MAPS** | current LMSD, **curated entries only** | Lipid candidates — the part ChEBI covers worst | ~20 MB |
| 7 | **Rhea** | release 100 (2018-11-26) | `chebi_pH7_3_mapping.tsv` for protonation; reaction plausibility | ~30 MB |
| 8 | **GtoPdb** | `v2017.5` (orphan status) + `v2026.1` (ground truth) | Benchmark item construction and scoring | ~60 MB |
| 9 | **GTEx** | V7 median TPM | Co-expression channel | ~15 MB |
| 10 | **Europe PMC** | REST, date-filtered at the tool boundary | Literature channel | streamed |

Total on-disk: roughly **200 MB**, downloadable in minutes on a normal connection.

Channel coverage with this set:

| Channel | Covered? | By what |
|---|---|---|
| Structure | ✅ | PDB snapshot (+ AlphaFold for the 2021 cutoff) |
| Chemistry | ✅ | ChEBI + LIPID MAPS candidate library; Rhea for protonation and plausibility |
| Literature | ✅ | Europe PMC with the L1 date filter |
| Co-expression | ✅ | GTEx V7 |
| Genetics | ❌ | **Deliberately omitted.** Adding GWAS Catalog `releases/2017/12/` restores it for ~2 GB; cold start runs the `−genetics` ablation by default |
| Ground truth | ✅ | GtoPdb at two versions |

Notes on the substitutions this set makes.

**ChEBI 3-star + LIPID MAPS curated replaces HMDB** as the candidate library.
This is a real downgrade: it loses HMDB's concentration and tissue-localisation data, and its coverage of human metabolites is narrower.
We report the library's size and composition in every run record so the comparison to papers that used HMDB is not silently flattering.

**GTEx V7 replaces ARCHS4** for co-expression.
GTEx is smaller and bulk-tissue only, but it is dated, licensed, and has usable confound metadata (`SMTSISCH`, `SMRIN`), which ARCHS4 does not.

**STRING is omitted from cold start**, because the release that matches a 2018 cutoff no longer exists and explaining the v11.0 approximation is more cost than the channel is worth for a single-target demo.
It is in the full configuration with the gap declared.

Three things the cold-start set deliberately cannot do, so that nobody mistakes it for the full configuration: no genetics channel, no structural-neighbour transfer (that needs a Foldseek index over AlphaFold DB), and no `sealed`-split evaluation.
It produces one ranked hypothesis list with a calibrated probability for one target, which is enough to demonstrate the loop and to run the physics regression tests in [04-EVALUATION.md §6](04-EVALUATION.md).

---

## 7. Consolidated unverified items

Everything below must be resolved, or the affected source dropped, before the repo is donated.
An honest gap is better than a wrong claim, but an unresolved gap at release time is neither.

| # | Item | Why it matters | How to resolve |
|---|---|---|---|
| 1 | HMDB terms verbatim text | `hmdb.ca` returns HTTP 403 to automated clients; the NC status is confirmed from two routes but the exact wording was not rendered | Human browser check of `hmdb.ca/about` and `/citing`. Does not change the `AVOID` verdict |
| 2 | HMDB current version number | Secondary sources say 5.0 (2021); no official confirmation | Same. Low priority given `AVOID` |
| 3 | BindingDB UCSD archive vintages | We claim quarterly archives exist but do not know whether any predate 2018 | Human browser at `https://library.ucsd.edu/dc/collection/bb03870458` (proof-of-work wall) |
| 4 | STRING v10.5 licensing and site availability | We pin v11.0 and must state why v10.5 is unusable | Human browser at `https://version-10-5.string-db.org/` (Cloudflare) |
| 5 | PDBe-KB per-contributor annotation licences | Blanket CC BY 4.0 may not override ~30 partners' own terms | Read the PDBe-KB partner list; until then, fetch-only |
| 6 | PDBe-KB update cadence | No official statement | Ask PDBe, or record observed mtimes and say so |
| 7 | AlphaFold `collaborations/` dataset licences (esp. AlphaMissense) | Historically NC elsewhere | Read each dataset's own terms before touching `collaborations/` |
| 8 | AlphaFold v5 release date and content | FTP directory exists; CHANGELOG does not document it | Compare `v5/` manifest against v4/v6 |
| 9 | InterPro member databases other than InterPro/Pfam/PRINTS/SFLD | CC0 is asserted only for those four | Check PANTHER, PROSITE, SMART, CDD, CATH-Gene3D terms individually if we redistribute their signatures |
| 10 | Reactome v63 release date | Needed to justify it as the pre-cutoff pin | `https://reactome.org/about/news` |
| 11 | Human-GEM: explicit statement that the root licence covers `model/` | Strong inference, not an explicit sentence | Open an issue on `SysBioChalmers/Human-GEM` |
| 12 | Recon3D under the new `bigg.bio` CC BY 4.0 collections | It is not listed among them | `bigg.bio` maintainers. Does not change `AVOID` today |
| 13 | GPCRdb reconstruction via `protwis/gpcrdb_data` git history | The only route to a dated GPCRdb | Inspect the repo's history and coverage |
| 14 | Open Targets `publicationYear` null rates per `sourceId` | Determines whether date filtering is a real L1 control or a partial one | Compute null rates on release 26.09 |
| 15 | TCRD numeric TDL thresholds | Cited in [00-PROBLEM.md](00-PROBLEM.md) as the Tdark definition | `https://www.druggablegenome.net/IDGProteinFamilies` |
| 16 | `TCRDv6_DataSourcesLicenses.xlsx` contents | Required before any TCRD redistribution, even derived | Download from the habanero server |
| 17 | Europe PMC date-field semantics | We rely on `FIRST_PDATE` and `FIRST_IDATE`; only the names are documented | Ask Europe PMC, or characterise empirically and document the method |
| 18 | Europe PMC and bioRxiv API rate limits | Undocumented; affects retrieval budget | Empirical, documented as such |
| 19 | PubChem PUG REST rate limits | Docs page is reCAPTCHA-gated | Empirical |
| 20 | ZINC — everything in §1.2 | All `docking.org` hosts refused or captcha-blocked automated access | Human browser. Does not change `AVOID` |
| 21 | Metabolomics GWAS Server licence | No terms found; TLS chain broken | Contact Helmholtz Munich. Until then, excluded |
| 22 | mGWAS-Explorer licence | No licence text found | Contact the Xia lab. Until then, excluded |
| 23 | Shin 2014 / Lotta 2021 / "Schlosser 2023" / "Chen 2023" sumstats | Two of these citations did not resolve to a matching paper | DOI-level pass. Reach mQTL data through the GWAS Catalog's per-study Usage License column instead |
| 24 | LIPID MAPS update cadence | No schedule published | Observational; record "Last updated" per fetch |
| 25 | HPA `/api/search_download.php` | Known by reputation, not tested | Test it, or use the per-dataset TSVs |

---

## 8. Compliance checklist before release

- [ ] `scripts/verify_licenses.py` run within 30 days, all verdicts unchanged
- [ ] No hostname on the `AVOID` list appears in any file under `src/` or `loops/` — asserted by `tests/controls/test_no_avoid_sources.py`
- [ ] Every directory under `data/third_party/` has a `LICENSE` and a `NOTICE`
- [ ] `ATTRIBUTION.md` lists every vendored dataset with source, version, licence and URL
- [ ] PubMed `NOTICE` carries NLM attribution, no-endorsement and the staleness disclaimer
- [ ] GTEx `NOTICE` carries the acknowledgement string with the retrieval date and the staleness notice
- [ ] No share-alike source appears with `in_repo: raw` in any committed manifest
- [ ] Every open item in §7 is either resolved or the affected source is dropped
- [ ] `git log -p` grep for `hmdb`, `kegg`, `drugbank`, `archs4`, `zinc`, `recon3d` returns nothing but this document

---

*Written material in this repository is licensed CC BY 4.0. Third-party data referenced here is licensed by its own terms, recorded per source above.*
