"""Pipeline semplificata: un solo DB, nessun normalizzatore di identificativi (si passa l'id cosi' com'e').
LLM ed encoder classificano in PARALLELO sullo stesso testo; le regole ATECO restano un terzo voto,
perche' costano zero e intercettano gli ATECO da holding senza bisogno di alcun modello."""
from __future__ import annotations

import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .agent import CollectorAgent
from .db import DB, record_to_text
from .encoder import Encoder, EncoderPrediction
from .evidence import Bundle, add_evidence, build_bundle
from .llm import LLMClient
from .llm_classifier import LLMResult, classify_record
from .rules import entity_type, rules_vote_from_ateco
from .sources import CameraleSource, WebEvidenceProvider
from .vocab import VOCAB, VOCAB_VERSION

Status = Literal["accepted", "accepted_with_flags", "needs_review", "insufficient_evidence", "not_found"]


class Decision(BaseModel):
    status: Status
    nis2_key: Optional[str] = None
    secondary_keys: list[str] = Field(default_factory=list)
    settore_nis2: Optional[str] = None
    sottosettore_nis2: Optional[str] = None
    annex: Optional[str] = None
    tipologia_soggetto: Optional[str] = None
    tipologia_note: Optional[str] = None
    flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Result(BaseModel):
    record_id: str
    decision: Decision
    llm: Optional[LLMResult] = None
    encoder_key: Optional[str] = None
    encoder_prob: Optional[float] = None
    encoder_top3: list = Field(default_factory=list)
    rules_key: Optional[str] = None
    n_evidence: int = 0
    web_failed: bool = False
    agent_steps: list = Field(default_factory=list)  # popolato solo se cfg.collector e' configurato
    elapsed_s: float = 0.0
    vocab_version: str = VOCAB_VERSION


@dataclass
class PipelineConfig:
    db: DB
    llm: LLMClient
    encoder: Optional[Encoder] = None
    camerale: Optional[CameraleSource] = None  # InfoCamere: piu' aggiornato del DB (nato da uno scraping passato)
    web: Optional[WebEvidenceProvider] = None
    encoder_threshold: float = 0.6  # sotto questa probabilita' l'encoder si astiene dal voto
    max_web_items: int = 6
    max_repairs: int = 2
    collector: Optional[CollectorAgent] = None  # se presente, decide LUI le ricerche web (sostituisce la query fissa)


def format_result(r: Result) -> str:
    d = r.decision
    out = [f"[{r.record_id}] stato: {d.status}"]
    if d.nis2_key:
        out.append(f"  settore: {d.settore_nis2} / {d.sottosettore_nis2}  [{d.nis2_key}, Allegato {d.annex}]")
        if d.secondary_keys:
            out.append(f"  altri settori: {', '.join(d.secondary_keys)}")
        out.append(f"  tipologia: {d.tipologia_soggetto}  ({d.tipologia_note})")
    llm_key = r.llm.output.nis2_key if (r.llm and r.llm.ok and r.llm.output) else None
    out.append(f"  voti: llm={llm_key!r} | encoder={r.encoder_key!r} (p={r.encoder_prob}) | regole={r.rules_key!r}")
    if r.encoder_top3:
        out.append(f"  encoder top-3: {[(k, round(p, 3)) for k, p in r.encoder_top3]}")
    if r.llm and not r.llm.ok:
        out.append(f"  ! llm non valido: {r.llm.error}")
    out.append(f"  evidenze: {r.n_evidence}" + (" (web non disponibile)" if r.web_failed else ""))
    for st in r.agent_steps:
        extra = f" -> {st.get('n_results')} risultati" if st.get("n_results") is not None else ""
        err = f" ERRORE: {st['error']}" if st.get("error") else ""
        out.append(f"  agente: {st['action']}" + (f" {st['query']!r}" if st.get("query") else "") + extra + err
                   + (f" ({st['reason']})" if st.get("reason") else ""))
    if d.flags:
        out.append(f"  flag: {d.flags}")
    for n in d.notes:
        out.append(f"  nota: {n}")
    out.append(f"  {r.elapsed_s}s")
    return "\n".join(out)


class SectorPipeline:
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg

    def run(self, record_id: str) -> Result:
        t0 = time.time()
        record = self.cfg.db.get(record_id)
        if not record:
            return Result(record_id=record_id, decision=Decision(status="not_found", notes=["id assente dal DB"]),
                         elapsed_s=round(time.time() - t0, 3))

        camerale = None
        if self.cfg.camerale is not None:
            try:
                camerale = self.cfg.camerale.lookup(record_id)
            except Exception:  # noqa: BLE001
                pass  # InfoCamere e' un extra: se non risponde si procede senza (flag piu' sotto)

        agent_steps: list = []
        if self.cfg.collector is not None:
            collected = self.cfg.collector.collect(record, camerale)
            bundle, agent_steps = collected.bundle, collected.steps
            if collected.agent_error:
                agent_steps = agent_steps or [{"action": "error", "error": collected.agent_error}]
        else:
            bundle = build_bundle(record, camerale)
            if self.cfg.web is not None and bundle.denominazione:
                try:
                    found = self.cfg.web.search(f"{bundle.denominazione} attivita' principale servizi erogati")
                    add_evidence(bundle, found[: self.cfg.max_web_items])
                except Exception:  # noqa: BLE001
                    bundle.web_failed = True
        web_failed = bundle.web_failed

        prompt_text = bundle.to_prompt_text()
        if not record_to_text(record).strip() and camerale is None and not bundle.items:
            return Result(record_id=record_id, decision=Decision(status="insufficient_evidence",
                         notes=["nessuna evidenza utilizzabile (record vuoto, InfoCamere e web senza risultati)"]),
                         web_failed=web_failed, elapsed_s=round(time.time() - t0, 3))
        valid_ids = {i.id for i in bundle.items}
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_llm = ex.submit(classify_record, self.cfg.llm, prompt_text, valid_evidence_ids=valid_ids,
                             max_repairs=self.cfg.max_repairs)
            f_enc = ex.submit(self.cfg.encoder.predict, prompt_text) if self.cfg.encoder else None
            llm_res = f_llm.result()
            enc_pred: Optional[EncoderPrediction] = f_enc.result() if f_enc else None

        rules = rules_vote_from_ateco(bundle.best_ateco())
        decision = self._decide(record, llm_res, enc_pred, rules, bundle)
        return Result(record_id=record_id, decision=decision, llm=llm_res,
                     encoder_key=enc_pred.key if enc_pred else None,
                     encoder_prob=round(enc_pred.prob, 4) if enc_pred else None,
                     encoder_top3=[(k, round(p, 4)) for k, p in enc_pred.top3] if enc_pred else [],
                     rules_key=rules.key if rules.informative else None, n_evidence=len(bundle.items),
                     web_failed=web_failed, agent_steps=[s.model_dump() if hasattr(s, "model_dump") else s
                                                        for s in agent_steps],
                     elapsed_s=round(time.time() - t0, 3))

    def run_batch(self, record_ids: list, workers: int = 4) -> list:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(self.run, record_ids))

    # ------------------------------------------------------------------ voto
    def _decide(self, record: dict, llm_res: LLMResult, enc_pred: Optional[EncoderPrediction], rules,
               bundle: Bundle) -> Decision:
        flags: list = []
        if bundle.web_failed:
            flags.append("web_unavailable")
        if bundle.camerale_record is None and self.cfg.camerale is not None:
            flags.append("infocamere_non_disponibile")
        if bundle.ateco_camerale and bundle.ateco_db and bundle.ateco_camerale != bundle.ateco_db:
            flags.append("ateco_aggiornato_da_infocamere")  # il DB (scraping datato) e InfoCamere (aggiornato) divergono
        llm_key = llm_res.output.nis2_key if (llm_res.ok and llm_res.output and llm_res.output.status == "classified") else None
        llm_abstained = llm_res.ok and llm_res.output and llm_res.output.status == "insufficient_evidence"
        if not llm_res.ok:
            flags.append("llm_invalid")
        elif llm_abstained:
            flags.append("llm_abstained")
        elif llm_res.output.basis == "conoscenza_del_modello":
            flags.append("llm_usa_conoscenza_esterna")  # non verificabile sul record: da controllare a campione

        enc_key = enc_pred.key if enc_pred else None
        enc_confident = bool(enc_pred and enc_pred.prob >= self.cfg.encoder_threshold)
        if enc_pred and not enc_confident:
            flags.append("encoder_low_confidence")
        if not rules.informative:
            flags.append("rules_abstained")

        votes = Counter(k for k in [llm_key, enc_key if enc_confident else None, rules.key if rules.informative else None] if k)
        if not votes:
            status = "needs_review" if not llm_res.ok else "insufficient_evidence"
            return Decision(status=status, flags=flags, notes=["nessun votante ha prodotto una chiave utilizzabile"])

        (top_key, top_n), *rest = votes.most_common()
        tie = bool(rest) and rest[0][1] == top_n
        if tie:
            return Decision(status="needs_review", flags=flags, notes=[f"parita' tra voti: {dict(votes)}"])
        model_confirms = (llm_key == top_key) or (enc_pred and enc_confident and enc_key == top_key)
        if not model_confirms:
            # solo le regole votano top_key: senza un modello a confermarlo (llm fallito/dissenziente e
            # nessun encoder confidente d'accordo), un lookup ATECO da solo non basta per accettare in automatico
            flags.append("rules_only_no_model_confirmation")
            return Decision(status="needs_review", flags=flags, notes=[f"solo le regole votano {top_key!r}: {dict(votes)}"])
        if enc_pred and enc_confident and enc_key != top_key:
            flags.append("encoder_dissent")  # l'encoder e' confidente ma vota un'altra chiave: da guardare
        if not llm_key:
            flags.append("llm_did_not_confirm")

        sd = VOCAB[top_key]
        secondary = list(llm_res.output.nis2_secondary_keys) if (llm_res.ok and llm_res.output and llm_key == top_key) else []
        dimensione = (bundle.camerale_record or {}).get("dimensione") or record.get("dimensione")
        tip, tip_note = entity_type(top_key, dimensione)
        if tip == "non_determinabile":
            flags.append("tipologia_provvisoria")
        needs_attention = {"llm_invalid", "encoder_dissent", "llm_did_not_confirm", "llm_usa_conoscenza_esterna",
                           "rules_abstained"}
        status = "accepted_with_flags" if any(f in needs_attention for f in flags) else "accepted"
        return Decision(status=status, nis2_key=top_key, secondary_keys=secondary, settore_nis2=sd.settore,
                        sottosettore_nis2=sd.sottosettore, annex=sd.annex, tipologia_soggetto=tip,
                        tipologia_note=tip_note, flags=flags, notes=[f"voti: {dict(votes)}"])
