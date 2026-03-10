import React, { useState } from 'react';
import axios from 'axios';
import { FileJson, Wand2, Loader2, UploadCloud, X } from 'lucide-react';
import SoapNoteViewer from '../components/SoapNoteViewer';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleGenerate = async () => {
    if (!file) return;
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_lang", "marathi");

    try {
      const response = await axios.post("http://localhost:8000/api/generate-from-json", formData);
      setResult(response.data);
    } catch (err) {
      alert("Pipeline Error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-12">
      {!result ? (
        <div className="space-y-8 animate-in fade-in duration-500">
          <div className="text-center">
            <h1 className="text-4xl font-black text-slate-900 tracking-tight">Pipeline Session Analysis</h1>
            <p className="text-slate-500 font-medium mt-2 tracking-wide">Upload a patient session JSON file to generate clinical notes.</p>
          </div>

          <div className="bg-white p-12 rounded-[3rem] border-2 border-slate-100 shadow-2xl shadow-slate-200/50 flex flex-col items-center">
            {!file ? (
              <label className="w-full h-80 flex flex-col items-center justify-center border-4 border-dashed border-slate-100 rounded-[2.5rem] cursor-pointer hover:bg-brand-50 hover:border-brand-200 transition-all group">
                <div className="bg-brand-100 text-brand-600 p-6 rounded-3xl mb-4 group-hover:scale-110 transition">
                  <UploadCloud size={48} />
                </div>
                <p className="text-lg font-black text-slate-700">Select Session JSON</p>
                <p className="text-sm text-slate-400 font-bold uppercase tracking-widest mt-2 underline">Browse Files</p>
                <input type="file" className="hidden" accept=".json" onChange={handleFileChange} />
              </label>
            ) : (
              <div className="w-full bg-slate-50 rounded-[2rem] p-10 border border-slate-200 flex flex-col items-center">
                <div className="bg-white p-4 rounded-2xl shadow-sm mb-4">
                  <FileJson size={40} className="text-brand-600" />
                </div>
                <p className="text-xl font-black text-slate-800">{file.name}</p>
                <p className="text-slate-400 font-bold text-xs uppercase mt-1">Ready for Pipeline Analysis</p>
                <button onClick={() => setFile(null)} className="mt-6 text-red-500 font-black text-xs uppercase tracking-widest flex items-center gap-1 hover:text-red-700 transition">
                  <X size={14}/> Remove File
                </button>
              </div>
            )}

            <button 
              disabled={loading || !file}
              onClick={handleGenerate}
              className="w-full mt-10 bg-brand-600 text-white py-6 rounded-3xl font-black text-lg flex items-center justify-center gap-3 hover:bg-brand-700 disabled:bg-slate-100 disabled:text-slate-400 transition shadow-xl shadow-brand-100"
            >
              {loading ? <Loader2 className="animate-spin" /> : <Wand2 size={24}/>}
              {loading ? 'Processing NER, LLM & RAG...' : 'Start Pipeline Analysis'}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-10 animate-in slide-in-from-bottom-10 duration-700">
           <button onClick={() => setResult(null)} className="font-black text-slate-400 hover:text-brand-600 flex items-center gap-2 transition uppercase text-xs tracking-widest">
             ← Analyze Another File
           </button>
           <SoapNoteViewer data={result} />
        </div>
      )}
    </div>
  );
}