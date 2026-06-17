# ner_service.py
import re
from typing import List, Dict, Tuple

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# ================= CONFIG =================
MODEL_NAME = "Jean-Baptiste/roberta-large-ner-english"
CONFIDENCE_THRESHOLD = 0.60

TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}\b")

MAIN_TOKENS = 400
OVERLAP = 50
STRIDE = max(1, MAIN_TOKENS - OVERLAP)

STOPWORDS = {
    "like", "do", "the", "a", "an", "us", "ok", "yeah",
    "yes", "no", "i", "we", "you", "they", "it", "that",
    "this", "there", "here"
}

# speaker header regex: captures "Name    3:19", "Stra, 8:27", "Pa 6:08" etc.
SPEAKER_RE = re.compile(
    r"(?m)^(?P<name>[A-Za-z][A-Za-z]{0,14})\s*,?\s*(?P<time>\d{1,2}:\d{2})"
)

app = FastAPI(title="NER Service", version="3.0.0-personmap")


class TextRequest(BaseModel):
    text: str


# ---------- MODEL LOADING ----------
@app.on_event("startup")
def load_model():
    global nlp, tokenizer

    device = 0 if torch.cuda.is_available() else -1
    print(f"\n🚀 Loading model on {'GPU' if device == 0 else 'CPU'}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

    nlp = pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device=device,
    )

    print("✅ Model loaded successfully\n")


# ---------- HELPERS ----------
def normalize_label(raw_label: str) -> str:
    if not raw_label:
        return "ENTITY"
    return raw_label.upper()

def replace_timestamps(text: str) -> str:
    """
    Replace timestamps like 6:19 or 12:45 with a single colon (:)
    """
    return TIMESTAMP_RE.sub(":", text)


def is_valid_entity_text(ent_text: str, label: str) -> bool:
    t = ent_text.strip()
    if not t:
        return False
    # reject pure punctuation / digits
    if not any(ch.isalpha() for ch in t):
        return False
    # reject stopwords
    if t.lower() in STOPWORDS:
        return False
    # if all lowercase and very short, likely not a name
    if t.islower() and len(t) <= 3 and label == "PER":
        return False
    return True


def resolve_exact_duplicates(entities: List[Dict]) -> List[Dict]:
    dedup = {}
    for ent in entities:
        key = (ent["start"], ent["end"], ent["entity"], ent["text"])
        prev = dedup.get(key)
        if prev is None or ent["confidence"] > prev["confidence"]:
            dedup[key] = ent
    return list(dedup.values())


def resolve_overlaps(entities: List[Dict]) -> List[Dict]:
    if not entities:
        return []
    ents = sorted(entities, key=lambda x: (x["start"], - (x["end"] - x["start"])))
    resolved: List[Dict] = []
    for ent in ents:
        if not resolved:
            resolved.append(ent)
            continue
        last = resolved[-1]
        if ent["start"] >= last["end"]:
            resolved.append(ent)
            continue
        # overlap: keep one with higher confidence; tie-breaker: longer
        if ent["confidence"] > last["confidence"]:
            resolved[-1] = ent
        elif ent["confidence"] == last["confidence"]:
            if (ent["end"] - ent["start"]) > (last["end"] - last["start"]):
                resolved[-1] = ent
            # else keep last
        # else keep last
    return resolved


def build_person_map_from_entities(entities: List[Dict], text: str) -> Dict[str, str]:
    """
    Build mapping original_person_text -> <Person_N> based on first appearance order.
    Includes any speaker header names present in entities (we add headers as PER spans before calling this).
    """
    # collect unique person texts with earliest position
    first_pos: Dict[str, int] = {}
    for ent in entities:
        if normalize_label(ent.get("entity", "")) in {"PER", "PERSON"}:
            key = ent["text"].strip()
            if key == "":
                continue
            prev = first_pos.get(key)
            if prev is None or ent["start"] < prev:
                first_pos[key] = ent["start"]

    # sort by first occurrence in doc
    ordered = sorted(first_pos.items(), key=lambda kv: kv[1])
    person_map: Dict[str, str] = {}
    for i, (name, _) in enumerate(ordered, start=1):
        person_map[name] = f"<Person_{i}>"
    return person_map


def build_highlighted(text: str, entities: List[Dict], person_map: Dict[str, str], anonymize_persons: bool = True) -> str:
    """
    Replace entity spans with *...* markers.
    If anonymize_persons=True: PERSON entities are replaced by their person_map placeholder.
    ORG/LOC/MISC are left as original text.
    Entities must be non-overlapping and sorted by start.
    """
    result = []
    last_idx = 0
    for ent in entities:
        start = ent["start"]
        end = ent["end"]
        if start < last_idx:
            continue
        result.append(text[last_idx:start])
        label = normalize_label(ent.get("entity", "ENTITY"))
        ent_text = ent.get("text", text[start:end])
        if anonymize_persons and label in {"PER", "PERSON"}:
            replacement = person_map.get(ent_text.strip(), "<Person>")
        else:
            replacement = ent_text
        result.append(f"*{replacement}*")
        last_idx = end
    result.append(text[last_idx:])
    return "".join(result)


# ---------- Extract speaker header spans and add as PER entities ----------
def extract_speaker_headers_as_entities(text: str) -> List[Dict]:
    """
    Find speaker header occurrences and return as entity dicts (label PER, confidence 1.0).
    These will be merged with NER outputs so headers use same person_map.
    """
    ents: List[Dict] = []
    for match in SPEAKER_RE.finditer(text):
        name = match.group("name")
        # span of the name inside the whole text
        # match.start("name") and match.end("name") require Python 3.8+ re match group spans
        try:
            s = match.start("name")
            e = match.end("name")
        except Exception:
            s, e = match.span(0)
        if s < e:
            ents.append({
                "entity": "PER",
                "text": name,
                "start": s,
                "end": e,
                "confidence": 1.0,
            })
    return ents


# ---------- MAIN ENDPOINT ----------
@app.post("/ner")
def run_ner(request: TextRequest):

    text = request.text
    if not text:
        return {}

    # ✅ NEW: remove timestamps before processing
    text = replace_timestamps(text)

    print(f"✅ Text after timestamp removal: {text}", flush=True)

    # 1) tokenize for traversal
    enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)
    offsets = enc["offset_mapping"]
    total_tokens = len(offsets)

    print("\n==============================")
    print(f"📄 Total tokens: {total_tokens}; main={MAIN_TOKENS}; overlap={OVERLAP}; stride={STRIDE}")
    print("==============================\n")

    collected_entities: List[Dict] = []

    # 2) add speaker header spans as high-confidence PERSON entities (so they map to the person_map)
    header_entities = extract_speaker_headers_as_entities(text)
    # add them first
    collected_entities.extend(header_entities)

    # 3) sliding window NER inference
    chunk_index = 0
    for main_start in range(0, total_tokens, STRIDE):
        main_end = min(main_start + MAIN_TOKENS, total_tokens)
        chunk_start = max(0, main_start - OVERLAP)
        chunk_end = min(total_tokens, main_end + OVERLAP)
        if chunk_start >= chunk_end:
            chunk_index += 1
            continue

        chunk_offsets = offsets[chunk_start:chunk_end]
        valid_offsets = [(s, e) for (s, e) in chunk_offsets if e > s]
        if not valid_offsets:
            chunk_index += 1
            continue

        char_start = valid_offsets[0][0]
        char_end = valid_offsets[-1][1]
        segment = text[char_start:char_end]

        if not segment.strip():
            chunk_index += 1
            continue

        results = nlp(segment)
        for r in results:
            score = float(r.get("score", 0.0))
            if score < CONFIDENCE_THRESHOLD:
                continue
            raw_label = r.get("entity_group") or r.get("entity") or ""
            label = normalize_label(raw_label)

            seg_rel_start = int(r["start"])
            seg_rel_end = int(r["end"])
            g_start = char_start + seg_rel_start
            g_end = char_start + seg_rel_end
            g_start = max(0, min(len(text), g_start))
            g_end = max(0, min(len(text), g_end))
            if g_end <= g_start:
                continue
            ent_text = text[g_start:g_end]

            # filter obvious false positives (esp. for PERSON)
            if label in {"PER", "PERSON"}:
                if not is_valid_entity_text(ent_text, label):
                    continue

            collected_entities.append({
                "entity": label,
                "text": ent_text,
                "start": g_start,
                "end": g_end,
                "confidence": round(score, 4),
            })

        chunk_index += 1

    # 4) dedupe and resolve overlaps
    deduped = resolve_exact_duplicates(collected_entities)
    deduped_sorted = sorted(deduped, key=lambda x: x["start"])
    filtered_entities = resolve_overlaps(deduped_sorted)

    # 5) Build person_map from PERSON entities (and headers previously added)
    person_map = build_person_map_from_entities(filtered_entities, text)

    # 6) Build highlighted outputs (use filtered_entities sorted)
    # ensure filtered_entities is sorted and non-overlapping
    filtered_sorted_by_start = sorted(filtered_entities, key=lambda x: x["start"])
    original_highlighted = build_highlighted(text, filtered_sorted_by_start, person_map, anonymize_persons=False)
    anonymized_highlighted = build_highlighted(text, filtered_sorted_by_start, person_map, anonymize_persons=True)

    print(f"✅ Entities detected (after filters & resolve): {len(filtered_sorted_by_start)}")
    print(f"✅ Unique persons mapped: {len(person_map)}\n")

    return {
        "entities": filtered_sorted_by_start,
        "original_highlighted": original_highlighted,
        "anonymized_highlighted": anonymized_highlighted,
        "person_map": person_map,
    }