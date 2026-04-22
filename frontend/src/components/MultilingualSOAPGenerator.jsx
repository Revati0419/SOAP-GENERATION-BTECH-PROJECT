import { useState } from 'react';
import LoadingAnimation from './LoadingAnimation';
import SoapNoteViewer from './SoapNoteViewer';
import { apiUrl } from '../lib/api';

export default function MultilingualSOAPGenerator() {
  const [transcript, setTranscript] = useState('');
  const [phq8Score, setPhq8Score] = useState(0);
  const [severity, setSeverity] = useState('unknown');
  const [gender, setGender] = useState('unknown');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(apiUrl('/api/generate-from-transcript'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation: transcript,
          phq8_score: parseInt(phq8Score),
          severity: severity,
          gender: gender,
          target_lang: 'marathi', // Forced to Marathi
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate SOAP note');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-slate-800">Marathi SOAP Generator</h1>
      
      <LoadingAnimation isOpen={loading} />
      
      {!result ? (
        <form onSubmit={handleSubmit} className="space-y-4 mb-8 bg-white p-8 rounded-3xl border border-slate-100 shadow-sm">
          {/* Transcript Input */}
          <div>
            <label className="block text-sm font-bold mb-2 text-slate-700">
              संवाद उतारा (Conversation Transcript)
            </label>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              className="w-full h-48 p-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              placeholder="डॉक्टर आणि रुग्ण यांच्यातील संवाद येथे पेस्ट करा..."
              required
            />
          </div>

          {/* Patient Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-bold mb-2 text-slate-700">PHQ-8 Score</label>
              <input
                type="number"
                min="0"
                max="24"
                value={phq8Score}
                onChange={(e) => setPhq8Score(e.target.value)}
                className="w-full p-3 border border-slate-200 rounded-xl"
              />
            </div>
            
            <div>
              <label className="block text-sm font-bold mb-2 text-slate-700">Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full p-3 border border-slate-200 rounded-xl bg-white"
              >
                <option value="unknown">Unknown</option>
                <option value="minimal">Minimal</option>
                <option value="mild">Mild</option>
                <option value="moderate">Moderate</option>
                <option value="moderately_severe">Moderately Severe</option>
                <option value="severe">Severe</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-bold mb-2 text-slate-700">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full p-3 border border-slate-200 rounded-xl bg-white"
              >
                <option value="unknown">Unknown</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-4 rounded-xl font-bold text-lg hover:bg-blue-700 disabled:bg-slate-300 transition-all shadow-lg shadow-blue-100"
          >
            {loading ? 'प्रक्रिया सुरू आहे...' : 'SOAP नोट तयार करा'}
          </button>
        </form>
      ) : (
        <div className="space-y-6">
            <button 
                onClick={() => setResult(null)}
                className="text-sm font-bold text-blue-600 hover:underline mb-4"
            >
                ← नवीन नोट तयार करा (Create New Note)
            </button>
            <SoapNoteViewer data={result} />
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-2xl mb-4 font-medium">
          <strong>Error:</strong> {error}
        </div>
      )}
    </div>
  );
}