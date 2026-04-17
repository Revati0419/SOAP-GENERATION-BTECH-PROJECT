import librosa
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

# ---- CONFIG ----
MODEL_ID = "muktan174/whisper-medium-ekacare-medical"  # or openai/whisper-small
SAMPLE_RATE = 16000
MAX_AUDIO_LEN = 30  # seconds

# Language map for Whisper decoder prompt
LANG_CODE_TO_WHISPER = {
    "hi": "hindi",
    "en": "english",
    "mr": "marathi",
}

# Device-safe load
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = WhisperProcessor.from_pretrained(MODEL_ID)
model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID).to(device)
model.eval()

def transcribe_audio(audio_path, language="mr"):
    """
    Transcribe one audio file.

    Args:
        audio_path (str): .wav/.mp3/.m4a path
        language (str): 'hi', 'en', 'mr'
    Returns:
        str: transcription
    """
    audio_array, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)

    # trim to max length
    max_samples = int(MAX_AUDIO_LEN * SAMPLE_RATE)
    audio_array = audio_array[:max_samples]

    input_features = processor.feature_extractor(
        audio_array,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt"
    ).input_features.to(device)

    whisper_lang = LANG_CODE_TO_WHISPER.get(language, "marathi")
    forced_ids = processor.get_decoder_prompt_ids(language=whisper_lang, task="transcribe")

    with torch.no_grad():
        predicted_ids = model.generate(
            input_features,
            forced_decoder_ids=forced_ids,
            max_new_tokens=225
        )

    return processor.tokenizer.decode(predicted_ids[0], skip_special_tokens=True)

# Example:
# print(transcribe_audio("/content/my_medical_audio.wav", language="mr"))