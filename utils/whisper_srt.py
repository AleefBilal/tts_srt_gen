import torch
import os
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment
import textwrap
from typing import List, Dict


MODEL_ID = "openai/whisper-small"   # docker path
# MODEL_ID = "distil-whisper/distil-large-v2"

_device = "cuda" if torch.cuda.is_available() else "cpu"
_torch_dtype = torch.float16 if _device == "cuda" else torch.float32
_device_id = 0 if _device == "cuda" else -1

# ---- internal cache (singleton per process) ----
_asr_pipeline = None


def get_asr_pipeline():
    """
    Lazy-loads and returns a cached Whisper ASR pipeline.
    Safe to call multiple times.
    """
    global _asr_pipeline

    if _asr_pipeline is not None:
        return _asr_pipeline


    processor = AutoProcessor.from_pretrained(MODEL_ID)
    _asr_pipeline = pipeline(
        "automatic-speech-recognition",
        model=AutoModelForSpeechSeq2Seq.from_pretrained(
            MODEL_ID,
            torch_dtype=_torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True
        ).to(_device),
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        device=_device_id,
        torch_dtype=_torch_dtype,
    )

    return _asr_pipeline


def preload_model():
    """
    Optional eager-loading hook.
    Call this at startup if you want to warm the model.
    """
    _ = get_asr_pipeline()



import os
import re
import textwrap
from typing import List, Dict


# ---------- timestamp formatting ----------

def _format_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1_000
    ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------- sentence splitting ----------

def _split_sentences(text: str) -> List[str]:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


# ---------- subtitle wrapping ----------

def _wrap_text_2_lines(text: str, max_chars: int = 32) -> List[str]:
    lines = textwrap.wrap(
        text,
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )

    blocks = []
    for i in range(0, len(lines), 2):
        blocks.append("\n".join(lines[i:i + 2]))

    return blocks


# ---------- timing adjustment ----------

def _adjust_chunk(chunk: Dict, start_pad=0.05, end_pad=0.25, min_dur=0.5) -> Dict:
    start, end = chunk["timestamp"]
    start = max(0.0, start - start_pad)
    end = end + end_pad
    if end - start < min_dur:
        end = start + min_dur
    return {"text": chunk["text"], "timestamp": (start, end)}


# ---------- force subtitle splitting ----------

def _split_chunk(chunk: Dict, max_chars: int = 32) -> List[Dict]:
    text = chunk["text"]
    start, end = chunk["timestamp"]
    duration = end - start

    sentences = _split_sentences(text)
    units = sentences if len(sentences) > 1 else [text]

    subtitle_blocks = []
    for unit in units:
        subtitle_blocks.extend(_wrap_text_2_lines(unit, max_chars))

    per_block = duration / len(subtitle_blocks)
    output = []

    for i, block in enumerate(subtitle_blocks):
        s = start + i * per_block
        e = s + per_block
        output.append({
            "text": block,
            "timestamp": (s, e),
        })

    return output


# ---------- SRT generation ----------

def _generate_srt(chunks: List[Dict]) -> str:
    srt = ""
    for i, c in enumerate(chunks, 1):
        srt += f"{i}\n"
        srt += f"{_format_timestamp(c['timestamp'][0])} --> {_format_timestamp(c['timestamp'][1])}\n"
        srt += f"{c['text']}\n\n"
    return srt


# ---------- public API ----------

def audio_to_srt(audio_path: str, language: str = "en") -> str:
    if _asr_pipeline is None:
        preload_model()
    result = _asr_pipeline(
        audio_path,
        return_timestamps=True,
        generate_kwargs={"task": "transcribe", "language": language},
    )

    final_chunks = []

    for chunk in result["chunks"]:
        chunk = _adjust_chunk(chunk)
        final_chunks.extend(_split_chunk(chunk, max_chars=32))

    out_path = os.path.splitext(audio_path)[0] + ".srt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(_generate_srt(final_chunks))

    return out_path
