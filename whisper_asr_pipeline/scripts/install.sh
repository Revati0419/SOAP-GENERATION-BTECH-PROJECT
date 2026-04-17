#!/bin/bash
# install.sh — One-shot installer for Whisper ASR pipeline (CPU-optimised)

set -e
echo "========================================"
echo "  Whisper Medical ASR — Installer"
echo "========================================"

echo ""
echo "[1/5] Upgrading pip..."
pip install --upgrade pip --quiet

echo ""
echo "[2/5] Installing core ML libraries..."
pip install \
  transformers==4.40.0 \
  datasets==2.19.0 \
  accelerate==0.29.3 \
  torch==2.2.2 \
  torchaudio==2.2.2 \
  --quiet

echo ""
echo "[3/5] Installing audio processing libraries..."
pip install \
  librosa==0.10.1 \
  soundfile==0.12.1 \
  audioread==3.0.1 \
  "pydub==0.25.1" \
  "pymp3==0.1.0" \
  --quiet

# Install mutagen for MP3 decoding without ffmpeg
pip install mutagen --quiet || true

echo ""
echo "[4/5] Installing evaluation + utilities..."
pip install \
  jiwer==3.0.3 \
  evaluate==0.4.1 \
  pandas==2.2.1 \
  numpy==1.26.4 \
  tqdm==4.66.2 \
  gtts==2.5.1 \
  --quiet

echo ""
echo "[5/5] Verifying installations..."
python -c "
import transformers, datasets, torch, librosa, jiwer, evaluate
print('  transformers:', transformers.__version__)
print('  datasets:    ', datasets.__version__)
print('  torch:       ', torch.__version__)
print('  librosa:     ', librosa.__version__)
print('  jiwer:       ', jiwer.__version__)
print('')
print('  CPU cores available:', torch.get_num_threads())
print('  All packages verified OK!')
"

echo ""
echo "[Optional] True diarization support (pyannote)..."
echo "  If you need robust speaker separation (Doctor/Patient), run:"
echo "    pip install \"pyannote.audio>=3.1,<4\""
echo "  and set: export HF_TOKEN=your_hf_token"

echo ""
echo "========================================"
echo "  Installation complete!"
echo "  Next: python src/01_prepare_data.py"
echo "========================================"
