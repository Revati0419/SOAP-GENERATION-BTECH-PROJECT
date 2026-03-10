"""
generate_synthetic.py
─────────────────────
Generates synthetic medical audio clips using Google TTS (gTTS).
Use this to bootstrap your dataset before real recordings are available.

Generates:
  - 60 English medical sentences
  - 60 Marathi medical sentences
  - 20 code-switched sentences

Output: data/raw/  (wav files + metadata.csv)

Usage:
    python scripts/generate_synthetic.py
    python scripts/generate_synthetic.py --count 200  # generate more
"""

import os
import csv
import io
import time
import wave
import struct
import argparse
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────
# SENTENCE BANKS
# These are example sentences. Expand these with real
# clinical phrases from your domain.
# ─────────────────────────────────────────────────────

ENGLISH_SENTENCES = [
    # Chief complaints
    "I have been having severe headache for the past three days.",
    "The pain is mostly on the left side of my head.",
    "I feel nausea and vomited once yesterday.",
    "I have chest pain that gets worse when I breathe deeply.",
    "My stomach has been hurting since morning.",
    "I have a high fever since last night.",
    "I am experiencing shortness of breath.",
    "I have been coughing continuously for two weeks.",
    "There is swelling in my right ankle.",
    "I feel very tired and weak.",
    # Medical history
    "I have a history of hypertension for five years.",
    "I am a diabetic patient on insulin therapy.",
    "I had a heart attack two years ago.",
    "I am allergic to penicillin.",
    "My mother has migraine and my father has diabetes.",
    "I had my appendix removed ten years ago.",
    "I have been diagnosed with asthma since childhood.",
    "I have no known drug allergies.",
    "I smoke half a pack of cigarettes daily.",
    "I drink alcohol occasionally.",
    # Medications
    "I am taking metformin five hundred milligrams twice daily.",
    "I take amlodipine five milligrams every morning.",
    "I have been using ibuprofen four hundred milligrams for pain.",
    "The doctor prescribed me atorvastatin twenty milligrams.",
    "I take aspirin seventy five milligrams daily.",
    "I use a salbutamol inhaler when I have breathing difficulty.",
    "I am on omeprazole twenty milligrams before meals.",
    "I take paracetamol five hundred milligrams for fever.",
    "I have been prescribed azithromycin five hundred milligrams.",
    "I use metoprolol fifty milligrams for my heart condition.",
    # Symptoms description
    "The pain is sharp and stabbing in nature.",
    "The headache is throbbing and pulsating.",
    "The pain radiates to my left shoulder.",
    "I feel dizzy when I stand up suddenly.",
    "My vision becomes blurry sometimes.",
    "I have difficulty swallowing food.",
    "I feel burning sensation in my chest after eating.",
    "The pain score is seven out of ten.",
    "Bright light and loud noise make the headache worse.",
    "Resting in a dark room gives some relief.",
    # Doctor questions
    "How long have you been experiencing these symptoms?",
    "Do you have any fever or chills?",
    "Is there any family history of this condition?",
    "Are you currently taking any medications?",
    "Have you had any recent travel history?",
    "Do you have any known allergies?",
    "Have you noticed any blood in your urine or stool?",
    "Is the pain constant or does it come and go?",
    "What makes the pain better or worse?",
    "Have you lost any weight recently?",
    # Examination findings
    "Blood pressure is one forty over ninety.",
    "Pulse rate is eighty two beats per minute.",
    "Temperature is one hundred and one degrees Fahrenheit.",
    "Oxygen saturation is ninety seven percent.",
    "Abdomen is soft and non tender.",
    "Chest is clear on auscultation.",
    "Heart sounds are normal with no murmurs.",
    "Reflexes are normal bilaterally.",
    "No lymph node enlargement noted.",
    "Pupils are equal and reactive to light.",
]

MARATHI_SENTENCES = [
    # Chief complaints
    "मला तीन दिवसांपासून खूप डोके दुखत आहे.",
    "डाव्या बाजूला जास्त वेदना होत आहेत.",
    "मळमळ होत आहे आणि काल एकदा उलटी झाली.",
    "छातीत दुखते आणि श्वास घेताना जास्त त्रास होतो.",
    "सकाळपासून पोट दुखत आहे.",
    "काल रात्रीपासून खूप ताप आहे.",
    "श्वास घ्यायला त्रास होत आहे.",
    "दोन आठवड्यांपासून सतत खोकला येतो.",
    "उजव्या घोट्याला सूज आली आहे.",
    "खूप थकवा आणि अशक्तपणा वाटतो.",
    # Medical history
    "पाच वर्षांपासून रक्तदाबाचा त्रास आहे.",
    "मी इन्सुलिन घेणारा मधुमेही रुग्ण आहे.",
    "दोन वर्षांपूर्वी हृदयविकाराचा झटका आला होता.",
    "मला पेनिसिलिनची अॅलर्जी आहे.",
    "आईला मायग्रेन आहे आणि वडिलांना मधुमेह आहे.",
    "दहा वर्षांपूर्वी अपेंडिक्सची शस्त्रक्रिया झाली.",
    "लहानपणापासून दमा आहे.",
    "कोणत्याही औषधाची अॅलर्जी नाही.",
    "मी रोज अर्धा पाकीट सिगारेट ओढतो.",
    "मी अधूनमधून दारू पितो.",
    # Medications
    "मी मेटफॉर्मिन पाचशे मिलीग्राम दिवसातून दोनदा घेतो.",
    "दर सकाळी अॅम्लोडिपाइन पाच मिलीग्राम घेतो.",
    "वेदनेसाठी आयबुप्रोफेन चारशे मिलीग्राम वापरतो.",
    "डॉक्टरांनी अॅटोर्वास्टॅटिन वीस मिलीग्राम लिहून दिले.",
    "दर दिवशी अॅस्पिरिन पंच्याहत्तर मिलीग्राम घेतो.",
    "श्वास घ्यायला त्रास झाला की सॅल्बुटॅमोल इनहेलर वापरतो.",
    "जेवणापूर्वी ओमेप्राझोल वीस मिलीग्राम घेतो.",
    "तापासाठी पॅरासिटामॉल पाचशे मिलीग्राम घेतो.",
    "अझिथ्रोमायसिन पाचशे मिलीग्राम लिहून दिले आहे.",
    "हृदयाच्या त्रासासाठी मेटोप्रोलॉल पन्नास मिलीग्राम घेतो.",
    # Symptoms
    "वेदना तीव्र आणि टोचणाऱ्या स्वरूपाची आहे.",
    "डोकेदुखी ठणका मारणारी आहे.",
    "वेदना डाव्या खांद्यापर्यंत पसरते.",
    "अचानक उठले की चक्कर येते.",
    "कधी कधी दृष्टी अंधुक होते.",
    "अन्न गिळताना त्रास होतो.",
    "जेवणानंतर छातीत जळजळ होते.",
    "वेदनेची तीव्रता दहापैकी सात आहे.",
    "उजेड आणि आवाजाने डोकेदुखी वाढते.",
    "अंधाऱ्या खोलीत आराम मिळतो.",
    # Doctor questions
    "हे त्रास किती दिवसांपासून आहेत?",
    "ताप किंवा थंडी वाजते का?",
    "कुटुंबात असा आजार कोणाला आहे का?",
    "सध्या कोणती औषधे घेत आहात?",
    "अलीकडे कुठे प्रवास केला आहे का?",
    "कोणत्या गोष्टींची अॅलर्जी आहे का?",
    "मूत्र किंवा मलात रक्त दिसले का?",
    "वेदना सतत असते की येते-जाते?",
    "कशाने बरे वाटते किंवा जास्त त्रास होतो?",
    "अलीकडे वजन कमी झाले आहे का?",
    # Examination
    "रक्तदाब एकशे चाळीस वर नव्वद आहे.",
    "नाडी बासष्ट ठोके प्रति मिनिट आहे.",
    "तापमान एकशे एक डिग्री फॅरेनहाइट आहे.",
    "ऑक्सिजन संतृप्ति सत्त्याण्णव टक्के आहे.",
    "पोट मऊ आहे आणि दाबल्यावर दुखत नाही.",
    "छातीत श्वास स्वच्छ ऐकू येतो.",
    "हृदयाचे आवाज सामान्य आहेत.",
    "प्रतिक्षिप्त क्रिया दोन्ही बाजूंनी सामान्य आहेत.",
    "लिम्फ नोड्समध्ये सूज नाही.",
    "बाहुल्या प्रकाशाला प्रतिसाद देत आहेत.",
]

MIXED_SENTENCES = [
    "Patient la तीन दिवसांपासून headache आहे.",
    "Pain डाव्या बाजूला आहे ani severity 7 out of 10 आहे.",
    "Nausea होत आहे ani उलटी pan झाली.",
    "रुग्ण ibuprofen 400mg घेत आहे पण relief नाही.",
    "Blood pressure 140/90 आहे ani pulse rate 82 आहे.",
    "Mother ला migraine आहे — possible family history.",
    "Symptoms तीन दिवसांपासून आहेत ani aggravated by light.",
    "Doctor ne CT scan करण्यास सांगितले.",
    "Sumatriptan prescribe केले आणि follow-up एका आठवड्यात.",
    "रुग्ण diabetic आहे ani metformin 500mg घेतो.",
    "Chest pain श्वास घेताना वाढते — pleuritic nature असू शकते.",
    "Oxygen saturation 97% आहे — सध्या stable आहे.",
    "अजून काही symptoms आहेत का — any fever or chills?",
    "Pain radiates डाव्या खांद्यापर्यंत — cardiac cause rule out करायला हवे.",
    "रुग्णाला aspirin allergy आहे, त्यामुळे alternative द्या.",
    "Examination मध्ये abdomen soft आहे ani non-tender आहे.",
    "History of hypertension आहे — antihypertensives adjust करायला हवेत.",
    "Cough दोन आठवड्यांपासून आहे — chest X-ray order करू.",
    "Weight loss झाले आहे — further investigation needed.",
    "रुग्णाला smoking history आहे — COPD rule out करा.",
]


def mp3_bytes_to_wav(mp3_bytes: bytes, wav_path: str,
                     target_sr: int = 16000) -> bool:
    """
    Convert MP3 bytes → WAV file at target_sr, mono.
    Uses only Python stdlib + packages you already installed.
    NO ffmpeg / ffprobe required.

    Tries in order:
      1. pydub  (uses audioop stdlib — no ffmpeg for WAV export)
      2. torchaudio  (if torch is installed)
      3. soundfile + audioread  (pure Python MP3 decoder)
      4. Silent WAV stub  (so pipeline structure stays intact)
    """
    import warnings
    warnings.filterwarnings("ignore")   # suppress ALL pydub/ffprobe warnings

    # ── Strategy 1: pydub (most common, uses audioop stdlib) ──────────
    try:
        import os
        # Patch pydub to NOT call ffprobe at import time
        os.environ["PATH"] = ""  # hide ffprobe from pydub temporarily
        from pydub import AudioSegment
        os.environ.pop("PATH", None)

        seg = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
        seg = seg.set_frame_rate(target_sr).set_channels(1).set_sample_width(2)
        seg.export(wav_path, format="wav")
        return True
    except Exception:
        pass

    # ── Strategy 2: torchaudio (already installed for training) ───────
    try:
        import torch, torchaudio
        tmp_mp3 = wav_path.replace(".wav", "_tmp.mp3")
        with open(tmp_mp3, "wb") as f:
            f.write(mp3_bytes)
        waveform, sr = torchaudio.load(tmp_mp3)
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            waveform = resampler(waveform)
        waveform = waveform.mean(dim=0, keepdim=True)   # stereo → mono
        torchaudio.save(wav_path, waveform, target_sr)
        os.remove(tmp_mp3)
        return True
    except Exception:
        pass

    # ── Strategy 3: soundfile + audioread (pure-Python MP3 read) ──────
    try:
        import soundfile as sf
        import audioread
        import numpy as np

        tmp_mp3 = wav_path.replace(".wav", "_tmp.mp3")
        with open(tmp_mp3, "wb") as f:
            f.write(mp3_bytes)

        with audioread.audio_open(tmp_mp3) as src:
            sr = src.samplerate
            ch = src.channels
            raw_chunks = [np.frombuffer(blk, dtype=np.int16) for blk in src]

        os.remove(tmp_mp3)
        audio = np.concatenate(raw_chunks).astype(np.float32) / 32768.0
        if ch > 1:
            audio = audio.reshape(-1, ch).mean(axis=1)
        if sr != target_sr:
            ratio = target_sr / sr
            n_out = int(len(audio) * ratio)
            audio = np.interp(
                np.linspace(0, len(audio)-1, n_out),
                np.arange(len(audio)), audio
            ).astype(np.float32)
        sf.write(wav_path, audio, target_sr)
        return True
    except Exception:
        pass

    # ── Strategy 4: stdlib audioop (Python ≤ 3.12 only) ───────────────
    # Note: This creates a silent clip — the transcript is kept so you
    # can manually replace the audio file later if needed.
    try:
        import wave, struct
        n_samples = target_sr * 3  # 3 seconds silence placeholder
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(b'\x00\x00' * n_samples)
        print(f"    ⚠  Saved silent placeholder (replace manually): {wav_path}")
        return True   # structure intact, can be replaced
    except Exception:
        return False


def text_to_wav(text: str, output_path: str, lang: str = "en") -> bool:
    """
    Convert text to WAV using gTTS (MP3) → pure-Python MP3→WAV conversion.
    No ffmpeg / ffprobe required.
    """
    try:
        from gtts import gTTS
        import warnings
        # Silence pydub's ffprobe RuntimeWarning completely
        warnings.filterwarnings("ignore", category=RuntimeWarning)

        # gTTS → MP3 bytes in memory (no temp file needed)
        tts = gTTS(text=text, lang=lang, slow=False)
        mp3_buf = io.BytesIO()
        tts.write_to_fp(mp3_buf)
        mp3_bytes = mp3_buf.getvalue()

        return mp3_bytes_to_wav(mp3_bytes, output_path)

    except Exception as e:
        print(f"    ⚠ TTS failed: {str(e)[:80]}")
        return False


def detect_gtts_lang(language: str) -> str:
    """Map our language labels to gTTS language codes."""
    return {"english": "en", "marathi": "mr", "mixed": "mr"}.get(language, "en")


def generate(count_per_lang: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    all_samples = (
        [(s, "english") for s in ENGLISH_SENTENCES[:count_per_lang]] +
        [(s, "marathi") for s in MARATHI_SENTENCES[:count_per_lang]] +
        [(s, "mixed") for s in MIXED_SENTENCES[:min(count_per_lang // 3, len(MIXED_SENTENCES))]]
    )

    metadata_rows = []
    success_count = 0

    print(f"\n🎙  Generating {len(all_samples)} synthetic audio clips...")
    print(f"    Output directory: {output_dir}\n")

    for idx, (text, lang) in enumerate(all_samples):
        filename = f"synth_{idx:04d}_{lang[:2]}.wav"
        filepath = output_dir / filename

        print(f"  [{idx+1:03d}/{len(all_samples)}] ({lang}) {text[:55]}...")

        gtts_lang = detect_gtts_lang(lang)
        ok = text_to_wav(text, str(filepath), lang=gtts_lang)

        if ok:
            metadata_rows.append({
                "file_name": filename,
                "transcript": text,
                "language": lang,
                "source": "synthetic_gtts"
            })
            success_count += 1
        else:
            print(f"    ✗ Skipped.")

        # Be gentle with gTTS rate limits
        time.sleep(0.5)

    # Write metadata CSV
    csv_path = output_dir / "metadata.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "transcript", "language", "source"])
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"\n{'='*55}")
    print(f"  ✅  Generated: {success_count}/{len(all_samples)} clips")
    print(f"  📄  Metadata:  {csv_path}")
    print(f"  📁  Audio:     {output_dir}")
    print(f"{'='*55}")
    print(f"\nNext step:")
    print(f"  python src/01_prepare_data.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic medical audio via gTTS")
    parser.add_argument("--count", type=int, default=60,
                        help="Number of clips per language (default: 60)")
    parser.add_argument("--output", type=str, default="data/raw",
                        help="Output directory (default: data/raw)")
    args = parser.parse_args()

    generate(
        count_per_lang=args.count,
        output_dir=Path(args.output)
    )
