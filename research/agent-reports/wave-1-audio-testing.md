---
title: Automated Audio/Voice/Speech Testing
aliases: [Wave 1 - Audio, Audio Testing, Voice Testing]
tags: [research, wave-1, audio, voice, testing]
wave: 1
source_agent: audio-speech-testing
created: 2026-05-17
---

# Automated Audio/Voice/Speech Testing — Field Guide (2024–2026)

> [!abstract] Headline
> **Chromium's `--use-file-for-fake-audio-capture` flag** + **Whisper round-trip with jiwer WER** + **ffprobe smoke checks** is the trinity. The killer LLM-agent-native pattern: **spectrogram-to-PNG** (Claude can `Read` the waveform image; flat = silent).

## 1. TTS output verification

Dominant production pattern: **round-trip TTS→STT with text similarity**, layered with **no-reference neural MOS predictors** and **dumb-but-reliable signal checks** (duration, RMS, silence ratio via `ffprobe`).

| Tool | What | License | Agent fit | Catch |
|---|---|---|---|---|
| **Round-trip TTS→Whisper→jiwer WER/CER** | Synthesize known prompt, transcribe with strong ASR, assert WER < threshold | Free (OSS) | **9/10** — trivially scriptable, deterministic | Tests *intelligibility*, not naturalness or prosody |
| **[UTMOS](https://github.com/sarulab-speech/UTMOS22)** (sarulab) | Predicted MOS from waveform, no reference needed. Pearson ~0.8–0.87 vs human MOS | OSS (BSD) | 8/10 — single Python call returns float | **Saturates at high quality** — top voices all score ~4.0–4.3 |
| **[NISQA](https://github.com/gabrielmittag/NISQA)** | CNN-LSTM predicting MOS + 4 sub-axes | OSS (MIT) | 8/10 | Trained on telephony/codec data; can mis-score studio TTS |
| **[SCOREQ](https://github.com/alessandroragano/scoreq)** | 2024 no-reference quality predictor | OSS | 7/10 | Newer, fewer integrations |
| **PESQ / POLQA / ViSQOL** | Classical *intrusive* metrics — need reference clean recording | PESQ free; POLQA paid | 5/10 | Need ground-truth audio per test case |
| **`ffprobe` + RMS/silence smoke check** | Did API return >N seconds of non-silent audio at right sample rate? | Free | **10/10** — first-line defense | Tells you nothing about correctness, only that bytes flowed |

OpenAI/ElevenLabs/Cartesia don't ship official test harnesses — community pattern is "round-trip + UTMOS + duration sanity." Hamming AI's [Pipecat regression guide](https://hamming.ai/resources/pipecat-bot-testing-automated-qa-regression) recommends round-trip + audio-native eval (not transcript-only).

## 2. STT accuracy testing

| Tool | What | License | Fit | Catch |
|---|---|---|---|---|
| **[jiwer](https://github.com/jitsi/jiwer)** | WER/CER/MER computation with text normalization. De-facto standard. | OSS (Apache) | **10/10** | Garbage in, garbage out — normalization (case, punctuation, numerals) dominates score; use Whisper's `EnglishTextNormalizer` |
| **HuggingFace `evaluate`** (`wer`, `cer`) | Thin wrapper, same idea | OSS | 9/10 | Same as jiwer |
| **Semantic WER / BERTScore / embedding cosine** | Catches "para→4 PM" cases jiwer marks wrong. [AssemblyAI 2025: "WER is lying"](https://www.assemblyai.com/blog/new-word-error-rate-wer-benchmark) | OSS | 8/10 | Slower; thresholds harder to pick |
| **Whisper as oracle** | Use `whisper-large-v3` or `turbo` as "truth" transcriber when no human ground truth | OSS | 8/10 round-trip; 4/10 as "truth" for production STT (circular) | Don't use Whisper to grade Whisper |

**Fixture strategy:** mix pre-recorded human samples (LibriSpeech, Common Voice subset filtered to target language/accent) with TTS-synthesized samples. Synthesized is fast to expand but biased — always keep small human-recorded "golden set" too. Target: <5% WER for clean speech is "production"; voice assistants live in 5–10%.

## 3. Pronunciation assessment testing

The hard one. Three layers:

| Layer | Approach | Tool |
|---|---|---|
| **Phoneme alignment** | Force-align learner's audio to expected transcript, get per-phone start/end | [**Montreal Forced Aligner (MFA)**](https://montreal-forced-aligner.readthedocs.io/) — Kaldi GMM-HMM, OSS, sub-20ms boundary precision, still beats WhisperX/MMS per [2024 ASR forced alignment paper](https://arxiv.org/html/2406.19363v1) |
| **Goodness of Pronunciation (GOP)** | Classical baseline: log-posterior of expected phone given alignment | Kaldi recipes; [`kaldi-gop`](https://github.com/jimbozhang/kaldi-dnn-ali-gop) |
| **Modern intelligibility scoring** | Duolingo's [2025 research post](https://blog.englishtest.duolingo.com/new-research-in-language-learning-a-pronunciation-scoring-model-built-around-intelligibility-not-imitation/) reports beating GOP, Whisper confidence, Microsoft's commercial scorer on CEFR-aligned ratings | No OSS release — pattern: build human-rated golden set on 0–4 CEFR rubric, regression-test scorer against it |

**How indie devs actually test pronunciation scorers:**
1. Record 50–200 utterances spanning skill levels (native, intermediate L2, beginner L2, deliberately bad)
2. Get 2–3 human raters to score each on intelligibility 0–4
3. CI asserts scorer's Pearson correlation with human mean stays above threshold (ρ > 0.7) — *not* that absolute scores match
4. Adversarial fixtures: silence, wrong-language speech, music, noise — assert "rejected" / low confidence

## 4. Voice UI / voice-first app testing frameworks

| Tool | License | Fit | Catch |
|---|---|---|---|
| **[Botium](https://botium-docs.readthedocs.io/)** | OSS core + commercial (Cyara) | 6/10 — heavy for solo dev | Setup tax; YAML-ish conversation specs |
| **[Bespoken](https://bespoken.io/)** | Paid SaaS | 4/10 — overkill, assistant-platform-focused | Pricing; not aimed at custom apps |
| **[Hamming AI](https://hamming.ai/)** | Commercial | 6/10 if building Pipecat/LiveKit | Paid, agent-focused not language-learning |

**Honest take for solo dev:** skip these. Build pytest-based harness with the primitives in §1–3. Commercial platforms aimed at call-center voice agents.

## 5. Audio fixtures / regression test sets

| Dataset | Content | License | Use |
|---|---|---|---|
| **[Mozilla Common Voice](https://commonvoice.mozilla.org/en/datasets)** | 100+ languages, crowd-recorded, accent/age/gender metadata | CC0 | **Best for L2/accent diversity** |
| **[LibriSpeech](https://www.openslr.org/12)** | 1000h English audiobook, clean read speech | CC-BY 4.0 | STT regression baseline (clean) |
| **[FLEURS](https://huggingface.co/datasets/google/fleurs)** | 102 languages, parallel sentences, ~12h/lang | CC-BY 4.0 | **Multilingual TTS/STT eval** |
| **[VoxPopuli](https://github.com/facebookresearch/voxpopuli)** | EU parliament speech, 16 langs | CC0 | Accented EU speech |
| **[L2-ARCTIC](https://psi.engr.tamu.edu/l2-arctic-corpus/)** | L2 English speakers from 6 L1s with annotations | Research license | **Pronunciation scoring ground truth** |
| **[speechocean762](https://www.openslr.org/101/)** | 5000 utterances, expert pronunciation scores at sentence/word/phone level | CC-BY 4.0 | **Best public pronunciation benchmark** |

Build small "regression test set": ~50 fixtures committed to repo (LFS), each `(audio.wav, expected_transcript.txt, expected_score_range.json)` triple. Run on every PR.

## 6. Headless Web Audio testing (browser side)

The Chromium magic incantation (Playwright `launchOptions.args`):

```
--use-fake-ui-for-media-stream
--use-fake-device-for-media-stream
--use-file-for-fake-audio-capture=/path/to/fixture.wav%noloop
--autoplay-policy=no-user-gesture-required
```

WAV must be **1 channel, 48 kHz**. `%noloop` suffix prevents replaying (default is loop). References: [Mad Devs writeup](https://maddevs.io/writeups/testing-web-apps-with-speech-and-image-recognition/), [omarelb TIL](https://omarelb.substack.com/p/til-2-set-up-playwright-with-fake), [dkarlovi speech-recognition demo](https://dkarlovi.github.io/testing-speech-recognition/).

| Tool | Fit | Catch |
|---|---|---|
| **Playwright + Chromium fake-audio flags** | **9/10** — actually works, no real mic needed | **Chromium only**; WebKit/Firefox don't support (open [issue #5444](https://github.com/microsoft/playwright/issues/5444)) |
| **MediaRecorder capture in test** | 7/10 — capture TTS playback to `Blob`, dump to disk, analyze | Need to plumb audio out of page context |
| **Web Audio API offline rendering** (`OfflineAudioContext`) | 8/10 for deterministic synthesis testing | Doesn't help with `getUserMedia` testing |

## 7. Spectral "did audio happen" checks

Cheap stuff that catches 80% of regressions:

| Check | Tool | One-liner |
|---|---|---|
| Duration | `ffprobe -i out.wav -show_entries format=duration` | Assert >0.5s and <30s |
| RMS energy | `librosa.feature.rms(y=y).mean()` | Assert > 0.01 (not silence) |
| Silence ratio | `librosa.effects.split(y, top_db=30)` | Assert non-silent portion > 50% |
| Sample rate / channels | `ffprobe -show_streams` | Assert matches expected |
| **Spectrogram PNG** | `librosa.display.specshow` → `plt.savefig()` | **Save as artifact so LLM with vision (Claude) can `Read` it** |
| Clipping | `np.max(np.abs(y)) < 0.99` | Catch overdriven output |

The spectrogram-to-PNG trick is the **most LLM-agent-native pattern**: flat or empty spectrogram is instantly visible to Claude through `Read`.

## 8. LLM/agent-friendly audio tooling (2025–2026)

Genuinely new, not yet mature. Two threads:

- **[AudioToolAgent](https://arxiv.org/html/2510.02995v1)** (Oct 2025) — LLM orchestrator calls audio-language models as HTTP tools. SOTA on MMAU/MMAR/MMAU-Pro
- **[AU-Harness](https://arxiv.org/abs/2509.08031)** — unified eval harness for audio-language models
- **Audio-LLMs as judges:** GPT-4o-audio, Gemini 2.5 Pro audio input, Qwen2-Audio, Phi-4-multimodal can take audio in and return text judgments. Pattern: feed TTS output to GPT-4o-audio with rubric → structured JSON score. Catch: cost, latency, judge has own biases.

No "audioconfirm" service yet — closest is rolling it yourself with Whisper + fuzzy match.

## Recommended audio verification stack for solo dev

In priority order — bolt these together for self-verifying voice app:

1. **`ffprobe` + `librosa` smoke layer** (free, 30 min). Every audio output gets duration + RMS + silence + sample-rate assertions. Catches 80% of "API silently broke" for ~0 cost.
2. **Whisper (large-v3 or turbo) + `jiwer` round-trip** (free, OSS). Every TTS call: synthesize → transcribe → assert normalized WER < 0.1. Workhorse.
3. **Chromium fake-audio flags in Playwright** (free). `--use-file-for-fake-audio-capture=fixture.wav%noloop` for `getUserMedia → MediaRecorder → /api/transcribe` flow in CI.
4. **Curated 50-fixture regression set**: pull from Common Voice (target language), L2-ARCTIC, speechocean762; record 10–20 your own. Commit under `tests/fixtures/audio/` (LFS if >100MB).
5. **UTMOS as TTS quality gate** (free, OSS). One float per generated clip; alert when rolling 7-day mean drops >0.2.
6. **GPT-4o-audio or Gemini 2.5 as "rubric judge"** for pronunciation scoring tests (paid, ~$0.01/clip). Use as human-rater stand-in for correlating against your scorer. Run weekly, not per-PR (cost).

Optional later: MFA for true phoneme-level forced alignment. Skip Botium/Bespoken/Hamming unless building voice agent.

## Sources

- [Hamming AI: Pipecat regression testing](https://hamming.ai/resources/pipecat-bot-testing-automated-qa-regression)
- [Hamming AI: ASR/STT/TTS guide](https://hamming.ai/blog/the-ultimate-guide-to-asr-stt-tts-for-voice-agents)
- [Maxim: Top 5 voice agent evaluation tools 2025](https://www.getmaxim.ai/articles/top-5-voice-agent-evaluation-tools-in-2025/)
- [TTSDS2 — robust objective TTS eval (2025)](https://www.isca-archive.org/ssw_2025/minixhofer25_ssw.pdf)
- [UTMOS overview](https://www.emergentmind.com/topics/utmos)
- [NISQA repo](https://github.com/gabrielmittag/NISQA)
- [jiwer](https://github.com/jitsi/jiwer)
- [AssemblyAI: WER benchmark caveats](https://www.assemblyai.com/blog/new-word-error-rate-wer-benchmark)
- [Duolingo: intelligibility-based pronunciation scoring](https://blog.englishtest.duolingo.com/new-research-in-language-learning-a-pronunciation-scoring-model-built-around-intelligibility-not-imitation/)
- [Montreal Forced Aligner docs](https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/index.html)
- [Mad Devs: Playwright fake audio/video](https://maddevs.io/writeups/testing-web-apps-with-speech-and-image-recognition/)
- [TIL: Playwright fake audio setup](https://omarelb.substack.com/p/til-2-set-up-playwright-with-fake)
- [Mozilla Common Voice](https://commonvoice.mozilla.org/en/datasets)
- [librosa RMS docs](https://librosa.org/doc/main/generated/librosa.feature.rms.html)
- [AudioToolAgent (2025)](https://arxiv.org/html/2510.02995v1)

## Related notes

- [[wave-1-general-verification-harnesses]] · [[wave-1-game-testing]] · [[wave-1-llm-eval-frameworks]]
- [[00-architecture-overview]] · Used in v0.2 Audio add-on
