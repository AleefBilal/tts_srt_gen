import torch
import gc
from chatterbox.tts_turbo import ChatterboxTurboTTS
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


model = ChatterboxTurboTTS.from_pretrained(device="cpu")
device = "cuda" if torch.cuda.is_available() else "cpu"
TORCH_DTYPE = torch.float16 if device == "cuda" else torch.float32

# Load once per process
MODEL_ID = "openai/whisper-small"   # docker path
processor = AutoProcessor.from_pretrained(MODEL_ID)
asr_pipeline = pipeline(
    "automatic-speech-recognition",
    model=AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID,
        torch_dtype=TORCH_DTYPE,
        low_cpu_mem_usage=True,
        use_safetensors=True
    ).to(device),
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=128,
    torch_dtype=TORCH_DTYPE,
)

del model
del asr_pipeline
gc.collect()

# mkdir -p ./models/whisper-small && \
#     git clone https://huggingface.co/openai/whisper-small /models/whisper-small || true && \
#     curl -L https://huggingface.co/openai/whisper-small/resolve/main/model.safetensors -o /models/whisper-small/model.safetensors && \
#     curl -L https://huggingface.co/openai/whisper-small/resolve/main/config.json -o /models/whisper-small/config.json && \
#     curl -L https://huggingface.co/openai/whisper-small/resolve/main/tokenizer.json -o /models/whisper-small/tokenizer.json