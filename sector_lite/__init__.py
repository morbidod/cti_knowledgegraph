"""sector_lite: resolver di settore NIS 2 — un DB, InfoCamere (piu' aggiornato) e ricerca web come
evidenze, un LLM classificatore e un encoder (TF-IDF o BERT) come votanti in parallelo, piu' le
regole ATECO. Nessun normalizzatore di identificativi: la stessa chiave passata al DB va anche a InfoCamere."""
from .agent import AgentAction, AgentStep, CollectorAgent, CollectResult
from .csv_db import CsvDB, guess_column_map
from .db import DB, FixtureDB, record_to_text
from .encoder import Encoder, EncoderPrediction, TfidfEncoder, fit_temperature, load_encoder, softmax
from .evidence import Bundle, add_evidence, build_bundle
from .llm import AnthropicClient, GeminiClient, LLMClient, OpenAICompatClient, ScriptedClient, extract_json
from .llm_classifier import LLMOutput, LLMResult, check_grounding, classify_record
from .pipeline import Decision, PipelineConfig, Result, SectorPipeline, format_result
from .rules import RulesVote, entity_type, rules_vote_from_ateco
from .sources import (CachingWebProvider, EvidenceItem, FakeWebProvider, FixtureCamerale, GeminiGroundedSearch,
                      TavilySearch)
from .vocab import VOCAB, VOCAB_VERSION, Sector

__all__ = [n for n in dir() if not n.startswith("_")]
