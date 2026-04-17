import React, { useState } from 'react';
import axios from 'axios';
import { FileJson, Wand2, Loader2, UploadCloud, X } from 'lucide-react';
import SoapNoteViewer from '../components/SoapNoteViewer';
import LoadingAnimation from '../components/LoadingAnimation';

export default function UploadPage() {
  const API_BASE = 'http://localhost:8000';

  const [mode, setMode] = useState('json');
  const [jsonFile, setJsonFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [targetLang, setTargetLang] = useState('marathi');
  const [asrLanguage, setAsrLanguage] = useState('marathi');
  const [baseModel, setBaseModel] = useState('openai/whisper-small');
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [phq8Score, setPhq8Score] = useState(0);
  const [severity, setSeverity] = useState('unknown');
  const [gender, setGender] = useState('unknown');
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Processing...');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [opStart, setOpStart] = useState(null);
  const [liveElapsed, setLiveElapsed] = useState('0.00s');
  const liveTimerRef = React.useRef(null);

  const handleJsonFileChange = (e) => {
    if (e.target.files[0]) setJsonFile(e.target.files[0]);
  };

  const handleAudioFileChange = (e) => {
    if (e.target.files[0]) setAudioFile(e.target.files[0]);
  };

  const handleGenerateFromJson = async () => {
    if (!jsonFile) return;
    setLoading(true);
    setError(null);
    setLoadingText('Processing NER, LLM & RAG...');
    // start client timer
    const start = Date.now();
    setOpStart(start);
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', jsonFile);
    formData.append('target_lang', targetLang);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-json`, formData);
      // attach client-measured processing time
      const totalMs = Date.now() - (opStart || Date.now());
      const clientTime = (totalMs / 1000).toFixed(2) + 's';
      const data = response.data || {};
      data.metadata = data.metadata || {};
      data.metadata.processing_time = clientTime;
      setResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Pipeline Error. Is the backend running?');
    } finally {
      setLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
      setOpStart(null);
    }
  };

  const handleTranscribeAudio = async () => {
    if (!audioFile) return;
    setLoading(true);
    setError(null);
    setLoadingText('Transcribing audio with Whisper...');
    const start = Date.now();
    setOpStart(start);
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', asrLanguage);
    formData.append('base_model', baseModel);
  formData.append('diarization', String(diarizationEnabled));

    try {
      const response = await axios.post(`${API_BASE}/api/transcribe-audio`, formData);
      const data = response.data || {};
      // attach client measured ASR time
      const totalMs = Date.now() - (opStart || Date.now());
      data._client_processing_time = (totalMs / 1000).toFixed(2) + 's';
      setTranscript(data?.transcript || '');
      // store last ASR timing in state for reference
      // (not setting result yet)
    } catch (err) {
      setError(err?.response?.data?.detail || 'ASR Error. Please check backend + Whisper setup.');
    } finally {
      setLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
      setOpStart(null);
    }
  };

  const handleGenerateFromTranscript = async () => {
    if (!transcript.trim()) {
      setError('Please transcribe audio first (or paste transcript manually).');
      return;
    }

    setLoading(true);
    setError(null);
    setLoadingText('Generating SOAP from transcript...');
    const start = Date.now();
    setOpStart(start);
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-transcript`, {
        conversation: transcript,
        phq8_score: parseInt(phq8Score, 10) || 0,
        severity,
        gender,
        target_lang: targetLang,
      });
      const totalMs = Date.now() - (opStart || Date.now());
      const clientTime = (totalMs / 1000).toFixed(2) + 's';
      const data = response.data || {};
      data.metadata = data.metadata || {};
      data.metadata.processing_time = clientTime;
      setResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to generate SOAP from transcript.');
    } finally {
      setLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
      setOpStart(null);
    }
  };

  // Ensure timer cleanup on unmount
  React.useEffect(() => () => {
    if (liveTimerRef.current) clearInterval(liveTimerRef.current);
  }, []);

  const handleGenerateFromAudioEndToEnd = async () => {
    if (!audioFile) {
      setError('Please select an audio file first.');
      return;
    }

    setLoading(true);
    setError(null);
    setLoadingText('Running end-to-end pipeline: Whisper → SOAP...');
    // start client timer
    const start = Date.now();
    setOpStart(start);
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', asrLanguage);
    formData.append('base_model', baseModel);
  formData.append('diarization', String(diarizationEnabled));
    formData.append('target_lang', targetLang);
    formData.append('phq8_score', String(parseInt(phq8Score, 10) || 0));
    formData.append('severity', severity);
    formData.append('gender', gender);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-audio`, formData);
      const data = response.data || {};
      if (data.asr?.transcript) {
        setTranscript(data.asr.transcript);
      }
      setResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'End-to-end audio pipeline failed.');
    } finally {
      setLoading(false);
      // stop client timer and attach measured time if backend didn't provide processing_time
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
      const totalMs = Date.now() - (opStart || Date.now());
      const clientTime = (totalMs / 1000).toFixed(2) + 's';
      setOpStart(null);
      setLiveElapsed(clientTime);
      setResult((prev) => {
        if (!prev) return prev;
        const meta = prev.metadata || {};
        if (!meta.processing_time) meta.processing_time = clientTime;
        return { ...prev, metadata: meta };
      });
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-12">
      {/* Loading Animation Overlay */}
      <LoadingAnimation isOpen={loading} />
      {loading && (
        <div className="fixed top-6 right-6 bg-white/90 px-3 py-2 rounded-lg shadow-sm text-sm font-medium">
          Time: {liveElapsed}
        </div>
      )}
      
      {!result ? (
        <div className="space-y-8 animate-in fade-in duration-500">
          <div className="text-center">
            <h1 className="text-4xl font-black text-slate-900 tracking-tight">Pipeline Session Analysis</h1>
            <p className="text-slate-500 font-medium mt-2 tracking-wide">Upload session JSON or audio to generate clinical SOAP notes.</p>
          </div>

          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => {
                setMode('json');
                setError(null);
              }}
              className={`px-5 py-2 rounded-xl font-bold ${mode === 'json' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'}`}
            >
              JSON Session
            </button>
            <button
              onClick={() => {
                setMode('audio');
                setError(null);
              }}
              className={`px-5 py-2 rounded-xl font-bold ${mode === 'audio' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'}`}
            >
              Audio (Whisper)
            </button>
          </div>

          <div className="bg-white p-12 rounded-[3rem] border-2 border-slate-100 shadow-2xl shadow-slate-200/50 flex flex-col items-center">
            {mode === 'json' ? (
              <>
                {!jsonFile ? (
                  <label className="w-full h-80 flex flex-col items-center justify-center border-4 border-dashed border-slate-100 rounded-[2.5rem] cursor-pointer hover:bg-brand-50 hover:border-brand-200 transition-all group">
                    <div className="bg-brand-100 text-brand-600 p-6 rounded-3xl mb-4 group-hover:scale-110 transition">
                      <UploadCloud size={48} />
                    </div>
                    <p className="text-lg font-black text-slate-700">Select Session JSON</p>
                    <p className="text-sm text-slate-400 font-bold uppercase tracking-widest mt-2 underline">Browse Files</p>
                    <input type="file" className="hidden" accept=".json" onChange={handleJsonFileChange} />
                  </label>
                ) : (
                  <div className="w-full bg-slate-50 rounded-[2rem] p-10 border border-slate-200 flex flex-col items-center">
                    <div className="bg-white p-4 rounded-2xl shadow-sm mb-4">
                      <FileJson size={40} className="text-brand-600" />
                    </div>
                    <p className="text-xl font-black text-slate-800">{jsonFile.name}</p>
                    <p className="text-slate-400 font-bold text-xs uppercase mt-1">Ready for Pipeline Analysis</p>
                    <button onClick={() => setJsonFile(null)} className="mt-6 text-red-500 font-black text-xs uppercase tracking-widest flex items-center gap-1 hover:text-red-700 transition">
                      <X size={14}/> Remove File
                    </button>
                  </div>
                )}

                <div className="w-full mt-6">
                  <label className="block text-sm font-bold text-slate-600 mb-2">Target language</label>
                  <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="w-full p-3 border rounded-xl"
                  >
                    <option value="marathi">Marathi</option>
                    <option value="hindi">Hindi</option>
                  </select>
                </div>

                <button 
                  disabled={loading || !jsonFile}
                  onClick={handleGenerateFromJson}
                  className="w-full mt-10 bg-brand-600 text-white py-6 rounded-3xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400 transition shadow-xl shadow-brand-100"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={24}/>}
                  {loading ? loadingText : 'Start Pipeline Analysis'}
                </button>
              </>
            ) : (
              <>
                {!audioFile ? (
                  <label className="w-full h-64 flex flex-col items-center justify-center border-4 border-dashed border-slate-100 rounded-[2.5rem] cursor-pointer hover:bg-brand-50 hover:border-brand-200 transition-all group">
                    <div className="bg-brand-100 text-brand-600 p-5 rounded-3xl mb-3 group-hover:scale-110 transition">
                      <UploadCloud size={42} />
                    </div>
                    <p className="text-lg font-black text-slate-700">Select Audio (MP3/WAV/M4A/FLAC/OGG)</p>
                    <p className="text-sm text-slate-400 font-bold uppercase tracking-widest mt-2 underline">Browse Files</p>
                    <input type="file" className="hidden" accept=".mp3,.wav,.m4a,.flac,.ogg,audio/*" onChange={handleAudioFileChange} />
                  </label>
                ) : (
                  <div className="w-full bg-slate-50 rounded-[2rem] p-8 border border-slate-200 flex flex-col items-center">
                    <div className="bg-white p-4 rounded-2xl shadow-sm mb-4">
                      <UploadCloud size={36} className="text-brand-600" />
                    </div>
                    <p className="text-lg font-black text-slate-800 text-center break-all">{audioFile.name}</p>
                    <button onClick={() => setAudioFile(null)} className="mt-4 text-red-500 font-black text-xs uppercase tracking-widest flex items-center gap-1 hover:text-red-700 transition">
                      <X size={14}/> Remove File
                    </button>
                  </div>
                )}

                <div className="w-full mt-6 grid md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">ASR language</label>
                    <select value={asrLanguage} onChange={(e) => setAsrLanguage(e.target.value)} className="w-full p-3 border rounded-xl">
                      <option value="marathi">Marathi</option>
                      <option value="english">English</option>
                      <option value="auto">Auto detect</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">Whisper model</label>
                    <select value={baseModel} onChange={(e) => setBaseModel(e.target.value)} className="w-full p-3 border rounded-xl">
                      <option value="openai/whisper-tiny">openai/whisper-tiny</option>
                      <option value="openai/whisper-small">openai/whisper-small</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">Target language</label>
                    <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="w-full p-3 border rounded-xl">
                      <option value="marathi">Marathi</option>
                      <option value="hindi">Hindi</option>
                    </select>
                  </div>
                </div>

                <div className="w-full mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={diarizationEnabled}
                      onChange={(e) => setDiarizationEnabled(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <span className="text-sm font-semibold text-slate-700">
                      Enable true diarization (pyannote)
                    </span>
                  </label>
                  <p className="text-xs text-slate-500 mt-2">
                    Requires <code>pyannote.audio</code> in <code>whisper_asr_pipeline/.venv_whisper</code> and a valid <code>HF_TOKEN</code> on backend.
                    If unavailable, backend falls back to heuristic speakers.
                  </p>
                </div>

                <button 
                  disabled={loading || !audioFile}
                  onClick={handleTranscribeAudio}
                  className="w-full mt-6 bg-slate-800 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-3 hover:bg-black disabled:bg-slate-200 disabled:text-slate-400 transition"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <UploadCloud size={20}/>}
                  {loading ? loadingText : 'Transcribe Audio (Whisper)'}
                </button>

                <button 
                  disabled={loading || !audioFile}
                  onClick={handleGenerateFromAudioEndToEnd}
                  className="w-full mt-4 bg-brand-600 text-white py-5 rounded-2xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400 transition shadow-xl shadow-brand-100"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={22}/>}
                  {loading ? loadingText : 'Run End-to-End (Audio → SOAP)'}
                </button>

                <div className="w-full mt-6">
                  <label className="block text-sm font-bold text-slate-600 mb-2">Transcript (editable)</label>
                  <textarea
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    rows={10}
                    className="w-full p-3 border rounded-xl"
                    placeholder="Transcript will appear here after ASR. You can edit it before SOAP generation."
                  />
                </div>

                <div className="w-full mt-6 grid md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">PHQ-8</label>
                    <input type="number" min="0" max="24" value={phq8Score} onChange={(e) => setPhq8Score(e.target.value)} className="w-full p-3 border rounded-xl" />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">Severity</label>
                    <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-full p-3 border rounded-xl">
                      <option value="unknown">Unknown</option>
                      <option value="minimal">Minimal</option>
                      <option value="mild">Mild</option>
                      <option value="moderate">Moderate</option>
                      <option value="moderately_severe">Moderately Severe</option>
                      <option value="severe">Severe</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">Gender</label>
                    <select value={gender} onChange={(e) => setGender(e.target.value)} className="w-full p-3 border rounded-xl">
                      <option value="unknown">Unknown</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>

                <button 
                  disabled={loading || !transcript.trim()}
                  onClick={handleGenerateFromTranscript}
                  className="w-full mt-8 bg-brand-600 text-white py-6 rounded-3xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400 transition shadow-xl shadow-brand-100"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={24}/>}
                  {loading ? loadingText : 'Generate SOAP from Transcript'}
                </button>

                <p className="w-full mt-3 text-xs text-slate-500 font-medium text-center">
                  Tip: Use <strong>Run End-to-End</strong> for one-click flow, or use the manual two-step flow to edit transcript before SOAP generation.
                </p>
              </>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl px-5 py-4 font-semibold">
              {error}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-10 animate-in slide-in-from-bottom-10 duration-700">
           <button onClick={() => {
             setResult(null);
             setError(null);
           }} className="font-black text-slate-400 hover:text-brand-600 flex items-center gap-2 transition uppercase text-xs tracking-widest">
             ← Analyze Another File
           </button>
           <SoapNoteViewer data={result} />
        </div>
      )}
    </div>
  );
}