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
  
  // FIXED: Hardcoded to marathi, removed UI setter
  const targetLang = 'marathi'; 
  
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

    const soapEnglish = generatedResult.soap_english || {};
    const soapTarget = generatedResult.soap_marathi || {}; // Explicitly look for Marathi

    try {
      await createSession({
        patient_id: Number(selectedPatientId),
        source_type: sourceType,
        transcript: transcriptText || '',
        target_lang: 'marathi',
        input_lang: generatedResult.input_language || asrLanguage || null,
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
    setLoadingText('Processing NER, LLM & RAG (Marathi)...');

    const start = Date.now();
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    const formData = new FormData();
    formData.append('file', jsonFile);
    formData.append('target_lang', 'marathi'); // Forced

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
      setError(err?.response?.data?.detail || 'Pipeline Error.');
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
    setLoadingText('Transcribing audio...');
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
      setError(err?.response?.data?.detail || 'ASR Error.');
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
      setError('Please transcribe audio first.');
      return;
    }

    setLoading(true);
    setShowSoapLoading(true);
    setError(null);
    setSaveNotice(null);
    setLoadingText('Generating Marathi SOAP...');
    const start = Date.now();
    setLiveElapsed('0.00s');
    liveTimerRef.current = setInterval(() => {
      setLiveElapsed(((Date.now() - start) / 1000).toFixed(2) + 's');
    }, 200);

    try {
      const response = await axios.post(`${API_BASE}/api/generate-from-transcript`, {
        conversation: transcript,
        target_lang: 'marathi', // Forced
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
      setError(err?.response?.data?.detail || 'Failed to generate SOAP.');
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
    setLoadingText('Running Marathi Pipeline...');
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
    formData.append('target_lang', 'marathi'); // Forced

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
      setError(err?.response?.data?.detail || 'End-to-end pipeline failed.');
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
    <div className="max-w-5xl mx-auto p-12">
      <LoadingAnimation isOpen={loading && showSoapLoading} />
      {loading && (
        <div className="fixed top-6 right-6 bg-white/90 px-3 py-2 rounded-lg shadow-sm text-sm font-medium">
          Time: {liveElapsed}
        </div>
      )}

      {!result ? (
        <div className="space-y-8 animate-in fade-in duration-500">
          <div className="text-center">
            <h1 className="text-4xl font-black text-slate-900 tracking-tight">Marathi Clinical Analysis</h1>
            <p className="text-slate-500 font-medium mt-2 tracking-wide">मराठी SOAP नोट्स व्युत्पन्न करण्यासाठी सेशन अपलोड करा.</p>
          </div>

          {/* Patient Selection Block */}
          <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex-1">
                <label className="block text-sm font-bold text-slate-600 mb-2">रुग्ण निवडा (Select Patient)</label>
                <select
                  value={selectedPatientId}
                  onChange={(e) => {
                    setSelectedPatientId(e.target.value ? Number(e.target.value) : '');
                    setError(null);
                    setSaveNotice(null);
                  }}
                  className="w-full p-3 border rounded-xl"
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
                {loadingPatients ? 'Loading...' : selectedPatient ? `Selected: ${selectedPatient.full_name}` : 'Select a patient.'}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3">
            <button onClick={() => setMode('json')} className={`px-5 py-2 rounded-xl font-bold ${mode === 'json' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'}`}>JSON Session</button>
            <button onClick={() => setMode('audio')} className={`px-5 py-2 rounded-xl font-bold ${mode === 'audio' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'}`}>Audio</button>
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
                    <input type="file" className="hidden" accept=".json" onChange={handleJsonFileChange} />
                  </label>
                ) : (
                  <div className="w-full bg-slate-50 rounded-[2rem] p-10 border border-slate-200 flex flex-col items-center">
                    <FileJson size={40} className="text-brand-600 mb-2" />
                    <p className="text-xl font-black text-slate-800">{jsonFile.name}</p>
                    <button onClick={() => setJsonFile(null)} className="mt-4 text-red-500 font-bold text-xs uppercase tracking-widest">Remove File</button>
                  </div>
                )}

                {/* REMOVED: Target Language Dropdown (now hardcoded to Marathi) */}

                <button
                  disabled={loading || !jsonFile || !selectedPatientId}
                  onClick={handleGenerateFromJson}
                  className="w-full mt-10 bg-brand-600 text-white py-6 rounded-3xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400 transition"
                >
                  {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={24} />}
                  Generate Marathi SOAP
                </button>
              </>
            ) : (
              <>
                {!audioFile ? (
                  <label className="w-full h-64 flex flex-col items-center justify-center border-4 border-dashed border-slate-100 rounded-[2.5rem] cursor-pointer hover:bg-brand-50 hover:border-brand-200 transition-all group">
                    <div className="bg-brand-100 text-brand-600 p-5 rounded-3xl mb-3 group-hover:scale-110 transition">
                      <UploadCloud size={42} />
                    </div>
                    <p className="text-lg font-black text-slate-700">Select Audio File</p>
                    <input type="file" className="hidden" accept="audio/*" onChange={handleAudioFileChange} />
                  </label>
                ) : (
                  <div className="w-full bg-slate-50 rounded-[2rem] p-8 border border-slate-200 flex flex-col items-center">
                    <UploadCloud size={36} className="text-brand-600 mb-2" />
                    <p className="text-lg font-black text-slate-800 text-center break-all">{audioFile.name}</p>
                    <button onClick={() => setAudioFile(null)} className="mt-4 text-red-500 font-bold text-xs uppercase tracking-widest">Remove File</button>
                  </div>
                )}

                {/* REMOVED: Target/ASR Language Grid (now hardcoded) */}

                <button
                  disabled={loading || !audioFile || !selectedPatientId}
                  onClick={handleTranscribeAudio}
                  className="w-full mt-6 bg-slate-800 text-white py-4 rounded-2xl font-black flex items-center justify-center gap-3 hover:bg-black disabled:bg-slate-200"
                >
                   Transcribe Audio
                </button>

                <button
                  disabled={loading || !audioFile || !selectedPatientId}
                  onClick={handleGenerateFromAudioEndToEnd}
                  className="w-full mt-4 bg-brand-600 text-white py-5 rounded-2xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 transition"
                >
                   Run Marathi Pipeline (End-to-End)
                </button>

                <div className="w-full mt-6">
                  <label className="block text-sm font-bold text-slate-600 mb-2">संवाद उतारा (Transcript)</label>
                  <textarea
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    rows={8}
                    className="w-full p-3 border rounded-xl"
                    placeholder="Transcript will appear here..."
                  />
                </div>

                <button
                  disabled={loading || !transcript.trim() || !selectedPatientId}
                  onClick={handleGenerateFromTranscript}
                  className="w-full mt-8 bg-brand-600 text-white py-6 rounded-3xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 shadow-xl"
                >
                  Generate Marathi SOAP
                </button>
              </>
            )}
          </div>

          {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl px-5 py-4 font-semibold">{error}</div>}
          {saveNotice && <div className={`rounded-2xl px-5 py-4 font-semibold ${saveNotice.toLowerCase().includes('failed') ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'}`}>{saveNotice}</div>}
        </div>
      ) : (
        <div className="space-y-10 animate-in slide-in-from-bottom-10 duration-700">
          <button onClick={() => setResult(null)} className="font-black text-slate-400 hover:text-brand-600 flex items-center gap-2 uppercase text-xs">
            ← Analyze Another File
          </button>
          
          <SoapNoteViewer data={result} />
          
          {saveNotice && <div className="rounded-2xl px-5 py-4 bg-emerald-50 text-emerald-800 font-semibold">{saveNotice}</div>}
        </div>
      )}
    </div>
  );
}