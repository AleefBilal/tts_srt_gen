import runpod
import uuid
import os
import logging
import shutil
import torch
from pathlib import Path
import torchaudio as ta

from chatterbox.tts_turbo import ChatterboxTurboTTS
from utils.s3 import download_file, upload_audio
from utils.utility import load_environment, classify_env, get_env
from utils.whisper_srt import preload_model, audio_to_srt

logging.basicConfig(level=logging.INFO)

# ---- Load models once (cold start) ----
tts_model = ChatterboxTurboTTS.from_pretrained(device="cuda")
preload_model()  # loads whisper once

DEFAULT_REF_AUDIO = "utils/default_ref.wav"
SEED = 123

def handler(event):
    workdir = None

    try:
        inp = event["input"]

        prompts = inp["prompts"]              # list[str]
        ref_audio_path = inp.get("ref_audio")
        generate_srt = inp.get("generate_srt", False)
        level = inp.get("level")

        # ---- Environment selection ----
        try:
            if level:
                load_environment(level)
            elif ref_audio_path:
                _, _, bucket, *_ = ref_audio_path.split("/")
                level = classify_env(bucket)
                load_environment(level)
            else:
                load_environment()
        except Exception:
            load_environment()

        # ---- Working directory ----
        workdir = Path("/tmp") / str(uuid.uuid4())
        workdir.mkdir(parents=True, exist_ok=True)

        # ---- Reference audio ----
        if ref_audio_path:
            ref_audio = workdir / "ref.wav"
            download_file(ref_audio_path, str(ref_audio))
        else:
            ref_audio = Path(DEFAULT_REF_AUDIO)

        bucket = get_env("LAMBDA_BUCKET")
        results = []

        # ---- Batch generation ----
        for idx, prompt in enumerate(prompts):
            logging.info(f"🎙️ Generating audio [{idx+1}/{len(prompts)}]")

            wav = tts_model.generate(
                text=prompt,
                audio_prompt_path=str(ref_audio),
            )

            audio_file = workdir / f"tts_{idx}.wav"
            ta.save(str(audio_file), wav, tts_model.sr)

            audio_key = f"video_gen/tts/{uuid.uuid4()}.wav"
            audio_s3 = upload_audio(str(audio_file), bucket, audio_key)

            srt_s3 = None
            if generate_srt:
                logging.info("📝 Generating SRT")
                srt_path = audio_to_srt(str(audio_file))
                srt_key = f"video_gen/srt/{uuid.uuid4()}.srt"
                srt_s3 = upload_audio(srt_path, bucket, srt_key)

                # remove local srt
                os.remove(srt_path)

            # remove local audio
            os.remove(audio_file)

            results.append(
                {
                    "prompt_index": idx,
                    "audio_path": audio_s3,
                    "srt_path": srt_s3,
                    "sample_rate": tts_model.sr,
                }
            )

        return {
            "count": len(results),
            "results": results,
        }

    except Exception as e:
        logging.exception("❌ Batch TTS failed")
        return {"error": str(e)}

    finally:
        if workdir and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

        torch.cuda.empty_cache()


runpod.serverless.start({"handler": handler})
