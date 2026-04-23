import React, { useState } from 'react';
import axios from 'axios';
import { FileJson, Wand2, Loader2, UploadCloud, X } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import SoapNoteViewer from '../components/SoapNoteViewer';
import LoadingAnimation from '../components/LoadingAnimation';
import { API_BASE_URL } from '../lib/api';
import { createSession, fetchPatients } from '../services/clinicApi';

export default function UploadPage() {
  const API_BASE = API_BASE_URL;
  const [searchParams] = useSearchParams();
  const patientIdFromUrl = Number(searchParams.get('patient_id') || 0) || '';

  const [mode, setMode] = useState('json');
  const [jsonFile, setJsonFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [targetLang, setTargetLang] = useState('marathi');
  const [asrLanguage] = useState('english');
  const DEFAULT_ASR_MODEL = import.meta.env.VITE_ASR_BASE_MODEL || 'muktan174/whisper-medium-ekacare-medical';
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Processing...');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [liveElapsed, setLiveElapsed] = useState('0.00s');
  const [transcriptionMeta, setTranscriptionMeta] = useState(null);
  const [showSoapLoading, setShowSoapLoading] = useState(false);
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(patientIdFromUrl);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [saveNotice, setSaveNotice] = useState(null);
  const liveTimerRef = React.useRef(null);

  const selectedPatient = patients.find((p) => Number(p.id) === Number(selectedPatientId));

  const ensurePatientSelected = () => {
    if (selectedPatientId) return true;
    setError('Please select a patient before running transcription or SOAP generation.');
    return false;
  };

  const loadPatients = async () => {
    setLoadingPatients(true);
    try {
      const data = await fetchPatients('', 200);
      setPatients(data.patients || []);
    } catch {
      // Allow SOAP generation even if patient lookup fails.
    } finally {
      setLoadingPatients(false);
    }
  };

  const persistSession = async ({ sourceType, generatedResult, transcriptText }) => {
    if (!selectedPatientId || !generatedResult) {
      setSaveNotice('SOAP generated (not saved: select a patient).');
      return;
    }

    const effectiveTargetLang =
      generatedResult?.target_language ||
      generatedResult?.metadata?.target_language ||
      targetLang ||
      'marathi';
    const soapEnglish = generatedResult.soap_english || {};
    const soapTarget = generatedResult[`soap_${effectiveTargetLang}`] || {};

    try {
      await createSession({
        patient_id: Number(selectedPatientId),
        source_type: sourceType,
        transcript: transcriptText || '',
        target_lang: effectiveTargetLang,
  input_lang: generatedResult.input_language || generatedResult?.metadata?.input_language || asrLanguage || null,
        soap_english: soapEnglish,
        soap_target: soapTarget,
        full_result: generatedResult,
      });
      setSaveNotice('Session saved to patient history.');
    } catch (err) {
      setSaveNotice(err?.response?.data?.detail || 'SOAP generated, but session save failed.');
    }
  };

  const handleJsonFileChange = (e) => {
    if (e.target.files[0]) setJsonFile(e.target.files[0]);
  };

  const handleAudioFileChange = (e) => {
    if (e.target.files[0]) setAudioFile(e.target.files[0]);
  };

  const handleGenerateFromJson = async () => {
    if (!jsonFile) return;
    if (!ensurePatientSelected()) return;
    setLoading(true);
  setShowSoapLoading(true);
    setError(null);
    setSaveNotice(null);
    setLoadingText('Processing NER, LLM & RAG...');

    const start = Date.now();
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', jsonFile);
    formData.append('target_lang', targetLang);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-json`, formData);
      const totalMs = Date.now() - start;
      const clientTime = (totalMs / 1000).toFixed(2) + 's';
      const data = response.data || {};
      data.metadata = data.metadata || {};
      data.metadata.processing_time = clientTime;
  data.metadata.session_to_soap_time = clientTime;
      setResult(data);
      await persistSession({ sourceType: 'json', generatedResult: data, transcriptText: transcript });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Pipeline Error. Is the backend running?');
    } finally {
      setLoading(false);
  setShowSoapLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
    }
  };

  const handleTranscribeAudio = async () => {
    if (!audioFile) return;
    if (!ensurePatientSelected()) return;
    setLoading(true);
  setShowSoapLoading(false);
    setError(null);
    setLoadingText('Transcribing audio with Whisper...');
    const start = Date.now();
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', asrLanguage);
  formData.append('base_model', DEFAULT_ASR_MODEL);
  formData.append('diarization', 'false');

    try {
      const response = await axios.post(`${API_BASE}/api/transcribe-audio`, formData);
      const data = response.data || {};
      const totalMs = Date.now() - start;
      data._client_processing_time = (totalMs / 1000).toFixed(2) + 's';
      setTranscript(data?.transcript || '');
  setTranscriptionMeta(data);
  setResult(null);
  setSaveNotice(null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'ASR Error. Please check backend + Whisper setup.');
    } finally {
      setLoading(false);
  setShowSoapLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
    }
  };

  const handleGenerateFromTranscript = async () => {
    if (!ensurePatientSelected()) return;
    if (!transcript.trim()) {
      setError('Please transcribe audio first (or paste transcript manually).');
      return;
    }

    setLoading(true);
  setShowSoapLoading(true);
    setError(null);
    setSaveNotice(null);
    setLoadingText('Generating SOAP from transcript...');
    const start = Date.now();
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-transcript`, {
        conversation: transcript,
        target_lang: targetLang,
      });
      const totalMs = Date.now() - start;
      const clientTime = (totalMs / 1000).toFixed(2) + 's';
      const data = response.data || {};
      data.metadata = data.metadata || {};
      data.metadata.processing_time = clientTime;
  data.metadata.session_to_soap_time = clientTime;
      setResult(data);
      await persistSession({ sourceType: 'transcript', generatedResult: data, transcriptText: transcript });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to generate SOAP from transcript.');
    } finally {
      setLoading(false);
  setShowSoapLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
    }
  };

  const handleGenerateFromAudioEndToEnd = async () => {
    if (!ensurePatientSelected()) return;
    if (!audioFile) {
      setError('Please select an audio file first.');
      return;
    }

    setLoading(true);
  setShowSoapLoading(true);
    setError(null);
    setSaveNotice(null);
    setLoadingText('Running end-to-end pipeline: Whisper → SOAP...');
    const start = Date.now();
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('language', asrLanguage);
  formData.append('base_model', DEFAULT_ASR_MODEL);
  formData.append('diarization', 'false');
    formData.append('target_lang', targetLang);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-audio`, formData);
      const data = response.data || {};
      if (data.asr?.transcript) {
        setTranscript(data.asr.transcript);
      }
      setTranscriptionMeta(data.asr || null);
      setResult(data);
      await persistSession({
        sourceType: 'audio',
        generatedResult: data,
        transcriptText: data.asr?.transcript || transcript,
      });
    } catch (err) {
      setError(err?.response?.data?.detail || 'End-to-end audio pipeline failed.');
    } finally {
      setLoading(false);
  setShowSoapLoading(false);
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
      const totalMs = Date.now() - start;
      const clientTime = (totalMs / 1000).toFixed(2) + 's';
      setLiveElapsed(clientTime);
      setResult((prev) => {
        if (!prev) return prev;
        const meta = prev.metadata || {};
        if (!meta.processing_time) meta.processing_time = clientTime;
        if (!meta.session_to_soap_time) meta.session_to_soap_time = clientTime;
        return { ...prev, metadata: meta };
      });
    }
  };

  React.useEffect(() => {
    loadPatients();
  }, []);

  React.useEffect(() => {
    if (patientIdFromUrl) {
      setSelectedPatientId(patientIdFromUrl);
    }
  }, [patientIdFromUrl]);

  React.useEffect(() => () => {
    if (liveTimerRef.current) clearInterval(liveTimerRef.current);
  }, []);

  return (
    <div className="mx-auto w-full max-w-6xl">
  <LoadingAnimation isOpen={loading && showSoapLoading} />
      {loading && (
        <div className="fixed right-6 top-6 rounded-xl border border-slate-200 bg-white/95 px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur">
          Time: {liveElapsed}
        </div>
      )}

      {!result ? (
        <div className="animate-in fade-in duration-500 space-y-7">
          <div className="surface-card rounded-[2rem] p-8 text-center">
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-brand-600">Clinical Workflow</p>
            <h1 className="mt-2 text-4xl font-black tracking-tight text-slate-900">Pipeline Session Analysis</h1>
            <p className="mt-2 font-medium tracking-wide text-slate-600">Upload session JSON or audio to generate clinically structured SOAP notes.</p>
          </div>

          <div className="surface-card rounded-2xl p-5">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex-1">
                <label className="block text-sm font-bold text-slate-600 mb-2">Patient for this session</label>
                <select
                  value={selectedPatientId}
                  onChange={(e) => {
                    setSelectedPatientId(e.target.value ? Number(e.target.value) : '');
                    setError(null);
                    setSaveNotice(null);
                  }}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/70 p-3 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200"
                >
                  <option value="">Select patient</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      #{p.id} • {p.full_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="text-sm text-slate-500 md:text-right">
                {loadingPatients ? 'Loading patients...' : selectedPatient ? `Selected: ${selectedPatient.full_name}` : 'Select a patient to continue.'}
                <div className="mt-1">
                  <Link to="/" className="text-brand-600 font-semibold hover:underline">Create/Search patients</Link>
                  {selectedPatientId ? (
                    <>
                      {' '}
                      •{' '}
                      <Link to={`/history?patient_id=${selectedPatientId}`} className="text-brand-600 font-semibold hover:underline">View patient history</Link>
                    </>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          <div className="mx-auto flex w-fit items-center gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm">
            <button
              onClick={() => {
                setMode('json');
                setError(null);
              }}
              className={`rounded-xl px-6 py-2 text-sm font-bold transition ${mode === 'json' ? 'bg-brand-600 text-white shadow-md shadow-brand-100' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              JSON Session
            </button>
            <button
              onClick={() => {
                setMode('audio');
                setError(null);
              }}
              className={`rounded-xl px-6 py-2 text-sm font-bold transition ${mode === 'audio' ? 'bg-brand-600 text-white shadow-md shadow-brand-100' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              Audio
            </button>
          </div>

          <div className="surface-card flex flex-col items-center rounded-[2.2rem] border p-10 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
            {mode === 'json' ? (
              <>
                {!jsonFile ? (
                  <label className="group flex h-80 w-full cursor-pointer flex-col items-center justify-center rounded-[2.2rem] border-4 border-dashed border-slate-200 bg-slate-50/50 transition-all hover:border-brand-200 hover:bg-brand-50/60">
                    <div className="bg-brand-100 text-brand-600 p-6 rounded-3xl mb-4 group-hover:scale-110 transition">
                      <UploadCloud size={48} />
                    </div>
                    <p className="text-lg font-black text-slate-700">Select Session JSON</p>
                    <p className="text-sm text-slate-400 font-bold uppercase tracking-widest mt-2 underline">Browse Files</p>
                    <input type="file" className="hidden" accept=".json" onChange={handleJsonFileChange} />
                  </label>
                ) : (
                  <div className="flex w-full flex-col items-center rounded-[2rem] border border-slate-200 bg-slate-50 p-10">
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
                  <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50/70 p-3 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200">
                    <option value="marathi">Marathi</option>
                    <option value="hindi">Hindi</option>
                    <option value="english">English</option>
                  </select>
                </div>

                <button
                  disabled={loading || !jsonFile || !selectedPatientId}
                  onClick={handleGenerateFromJson}
                  className="mt-10 flex w-full items-center justify-center gap-3 rounded-3xl bg-brand-600 py-5 text-lg font-black text-white shadow-xl shadow-brand-100 transition hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={24} />}
                  {loading ? loadingText : 'Start Pipeline Analysis'}
                </button>
              </>
            ) : (
              <>
                {!audioFile ? (
                  <label className="group flex h-64 w-full cursor-pointer flex-col items-center justify-center rounded-[2.2rem] border-4 border-dashed border-slate-200 bg-slate-50/50 transition-all hover:border-brand-200 hover:bg-brand-50/60">
                    <div className="bg-brand-100 text-brand-600 p-5 rounded-3xl mb-3 group-hover:scale-110 transition">
                      <UploadCloud size={42} />
                    </div>
                    <p className="text-lg font-black text-slate-700">Select Audio (MP3/WAV/M4A/FLAC/OGG)</p>
                    <p className="text-sm text-slate-400 font-bold uppercase tracking-widest mt-2 underline">Browse Files</p>
                    <input type="file" className="hidden" accept=".mp3,.wav,.m4a,.flac,.ogg,audio/*" onChange={handleAudioFileChange} />
                  </label>
                ) : (
                  <div className="flex w-full flex-col items-center rounded-[2rem] border border-slate-200 bg-slate-50 p-8">
                    <div className="bg-white p-4 rounded-2xl shadow-sm mb-4">
                      <UploadCloud size={36} className="text-brand-600" />
                    </div>
                    <p className="text-lg font-black text-slate-800 text-center break-all">{audioFile.name}</p>
                    <button onClick={() => setAudioFile(null)} className="mt-4 text-red-500 font-black text-xs uppercase tracking-widest flex items-center gap-1 hover:text-red-700 transition">
                      <X size={14}/> Remove File
                    </button>
                  </div>
                )}

                <div className="w-full mt-6 grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">ASR language</label>
                    <select value={asrLanguage} disabled className="w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-100 p-3 text-slate-600">
                      <option value="english">English</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-600 mb-2">Target language</label>
                    <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50/70 p-3 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200">
                      <option value="marathi">Marathi</option>
                      <option value="hindi">Hindi</option>
                      <option value="english">English</option>
                    </select>
                  </div>
                </div>

                <button
                  disabled={loading || !audioFile || !selectedPatientId}
                  onClick={handleTranscribeAudio}
                  className="mt-6 flex w-full items-center justify-center gap-3 rounded-2xl bg-slate-800 py-4 font-black text-white transition hover:bg-black disabled:bg-slate-200 disabled:text-slate-400"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <UploadCloud size={20} />}
                  {loading ? loadingText : 'Transcribe Audio'}
                </button>

                {transcript && !result && (
                  <div className="mt-5 w-full rounded-2xl border border-blue-200 bg-blue-50/80 p-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-3">
                      <h4 className="text-sm font-black text-blue-800 uppercase tracking-wider">Transcription Output</h4>
                      <span className="text-xs font-semibold text-blue-700">
                        ASR time: {transcriptionMeta?._client_processing_time || (transcriptionMeta?.processing_s ? `${transcriptionMeta.processing_s}s` : '—')}
                      </span>
                    </div>
                    <p className="text-xs text-blue-700 mb-2">
                      Transcription is ready. You can edit below or run end-to-end to generate SOAP.
                    </p>
                  </div>
                )}

                <button
                  disabled={loading || !audioFile || !selectedPatientId}
                  onClick={handleGenerateFromAudioEndToEnd}
                  className="mt-4 flex w-full items-center justify-center gap-3 rounded-2xl bg-brand-600 py-5 text-lg font-black text-white shadow-xl shadow-brand-100 transition hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={22} />}
                  {loading ? loadingText : 'Run End-to-End (Audio → SOAP)'}
                </button>

                <div className="w-full mt-6">
                  <label className="block text-sm font-bold text-slate-600 mb-2">Transcript (editable)</label>
                  <textarea
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    rows={10}
                    className="w-full rounded-xl border border-slate-200 bg-white p-3 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200"
                    placeholder="Transcript will appear here after ASR. You can edit it before SOAP generation."
                  />
                </div>

                <button
                  disabled={loading || !transcript.trim() || !selectedPatientId}
                  onClick={handleGenerateFromTranscript}
                  className="mt-8 flex w-full items-center justify-center gap-3 rounded-3xl bg-brand-600 py-6 text-lg font-black text-white shadow-xl shadow-brand-100 transition hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={24} />}
                  {loading ? loadingText : 'Generate SOAP from Transcript'}
                </button>

                <p className="w-full mt-3 text-xs text-slate-500 font-medium text-center">
                  Tip: Use <strong>Run End-to-End</strong> for one-click flow, or use the manual two-step flow to edit transcript before SOAP generation.
                </p>
              </>
            )}
          </div>

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 font-semibold text-red-700">
              {error}
            </div>
          )}
          {saveNotice && (
            <div className={`rounded-2xl px-5 py-4 font-semibold ${saveNotice.toLowerCase().includes('failed') ? 'border border-amber-200 bg-amber-50 text-amber-800' : 'border border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
              {saveNotice}
            </div>
          )}
        </div>
      ) : (
        <div className="animate-in slide-in-from-bottom-10 duration-700 space-y-8">
          <button
            onClick={() => {
              setResult(null);
              setError(null);
            }}
            className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-500 transition hover:text-brand-600"
          >
            ← Analyze Another File
          </button>
          <SoapNoteViewer data={result} />
          <div className="surface-card rounded-2xl border border-indigo-200/80 bg-indigo-50/60 px-5 py-4">
            <p className="text-xs font-black uppercase tracking-wider text-indigo-700">Session → SOAP Time</p>
            <p className="text-lg font-black text-indigo-900">
              {result?.metadata?.session_to_soap_time || result?.metadata?.processing_time || '—'}
            </p>
          </div>
          {saveNotice && (
            <div className={`rounded-2xl px-5 py-4 font-semibold ${saveNotice.toLowerCase().includes('failed') ? 'border border-amber-200 bg-amber-50 text-amber-800' : 'border border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
              {saveNotice}
            </div>
          )}
        </div>
      )}
    </div>
  );
}