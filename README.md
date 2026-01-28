# 🎙️ TTS + Subtitles Pipeline (RunPod Serverless)

This repository contains a **production-grade RunPod serverless pipeline** that:

1. Takes text prompts as input
2. Generates **speech audio** using **Chatterbox TTS**
3. Optionally generates **subtitles (SRT)** using **open-source Whisper**
4. Uploads outputs to **S3**
5. Cleans up local artifacts automatically

Designed for **batch processing**, **GPU inference**, and **serverless deployment**.

---

## 🧩 Pipeline Overview

```
Input (JSON)
   ↓
Chatterbox TTS (GPU)
   ↓
Audio (.wav)
   ↓ (optional)
Whisper ASR (GPU)
   ↓
Subtitles (.srt)
   ↓
Upload to S3
   ↓
Clean local files
   ↓
Structured JSON output
```

---

## 🚀 Features

* ✅ **RunPod serverless ready**
* ✅ **Batch TTS** (multiple prompts per request)
* ✅ **Optional subtitle generation**
* ✅ **Whisper GPU inference**
* ✅ **Subtitle-optimized SRT formatting**
* ✅ **Model warm-loading (no cold reloads)**
* ✅ **S3 upload + local cleanup**
* ✅ **Production-safe memory handling**

---

## 📥 Input Format

```json
{
  "input": {
    "prompts": [
      "Hello world",
      "Second sentence"
    ],
    "ref_audio": "s3://bucket/path/ref.wav",
    "generate_srt": true,
    "level": "prod"
  }
}
```

### Input Fields

| Field          | Type           | Required | Description                                |
| -------------- | -------------- | -------- | ------------------------------------------ |
| `prompts`      | `list[string]` | ✅        | Text prompts to convert to speech          |
| `ref_audio`    | `string`       | ❌        | S3 path to reference voice audio           |
| `generate_srt` | `bool`         | ❌        | Whether to generate subtitles              |
| `level`        | `string`       | ❌        | Environment selector (`dev`, `prod`, etc.) |

---

## 📤 Output Format

```json
{
  "count": 2,
  "results": [
    {
      "prompt_index": 0,
      "audio_path": "s3://bucket/video_gen/tts/uuid.wav",
      "srt_path": "s3://bucket/video_gen/srt/uuid.srt",
      "sample_rate": 24000
    },
    {
      "prompt_index": 1,
      "audio_path": "s3://bucket/video_gen/tts/uuid.wav",
      "srt_path": "s3://bucket/video_gen/srt/uuid.srt",
      "sample_rate": 24000
    }
  ]
}
```

### Notes

* Output order matches input order via `prompt_index`
* `srt_path` is `null` if `generate_srt=false`
* All files are uploaded to S3 and removed locally

---

## 🔊 Text-to-Speech (TTS)

* **Engine:** Chatterbox Turbo TTS
* **Execution:** GPU (CUDA)
* **Voice conditioning:** Optional reference audio
* **Output:** WAV audio

The TTS model is **loaded once per process** and reused for all requests.

---

## 📝 Subtitles (ASR)

* **Engine:** Open-source Whisper (Transformers pipeline)
* **Execution:** GPU-accelerated
* **Timestamps:** Segment-level timestamps
* **Post-processing:**

  * Sentence-aware splitting
  * Max 2 lines per subtitle
  * Character-limit enforcement
  * Minimum display duration
  * Subtitle-friendly timing

### Example SRT Output

```
1
00:00:00,180 --> 00:00:03,209
Our clients are completing
projects faster than ever, and

2
00:00:03,220 --> 00:00:05,460
they're not just satisfied,
they're thriving!
```

---

## 🧠 Performance Optimizations

* Models are **preloaded on cold start**
* Whisper and TTS models are reused across requests
* GPU memory is explicitly cleared after execution
* Temporary files are removed immediately after upload

---

## 🐳 Docker & RunPod

This service is intended to run as a **RunPod Serverless Docker**.

### Expected Runtime Capabilities

* NVIDIA GPU (CUDA)
* PyTorch + Transformers
* FFmpeg installed
* S3 credentials available via environment

---

## 🔐 Environment Variables

| Variable                | Description                   |
| ----------------------- | ----------------------------- |
| `LAMBDA_BUCKET`         | Default S3 bucket for uploads |
| `AWS_ACCESS_KEY_ID`     | S3 access                     |
| `AWS_SECRET_ACCESS_KEY` | S3 secret                     |
| `AWS_REGION`            | S3 region                     |

---

## 🧪 Development Notes

* Supports **batch inference**
* Safe for **parallel RunPod workers**
* Each worker loads models once
* Subtitle logic is **platform-agnostic** (burned captions, YouTube, etc.)

---

## 📌 When to Use This Pipeline

* AI video generation
* Voice-over automation
* Talking-head videos
* Captioned social media content
* Accessibility workflows

---

## 🛠️ Future Extensions (Optional)

* Word-level timestamps
* Karaoke-style captions
* CPS (characters/sec) enforcement
* Multi-speaker diarization
* Async batching
* Caption style presets (Reels / YouTube / Shorts)

---

## ✅ Summary

This repository provides a **clean, scalable, serverless-ready solution** for generating **speech + subtitles** using fully open-source models, optimized for GPU inference and real-world production workloads.
