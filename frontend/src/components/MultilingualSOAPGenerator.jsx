// Example React component for the new multilingual API

import { useState } from 'react';
import LoadingAnimation from './LoadingAnimation';
import { apiUrl } from '../lib/api';

export default function MultilingualSOAPGenerator() {
  const [transcript, setTranscript] = useState('');
  const [phq8Score, setPhq8Score] = useState(0);
  const [severity, setSeverity] = useState('unknown');
  const [gender, setGender] = useState('unknown');
  const [targetLang, setTargetLang] = useState('marathi');
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
          target_lang: targetLang,
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
      <h1 className="text-3xl font-bold mb-6">Multilingual SOAP Generator</h1>
      
      {/* Loading Animation Overlay */}
      <LoadingAnimation isOpen={loading} />
      
      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        {/* Transcript Input */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Conversation Transcript
            <span className="text-gray-500 ml-2">(Marathi, Hindi, English, or Mixed)</span>
          </label>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            className="w-full h-48 p-3 border rounded-lg"
            placeholder={`Example (Marathi):
डॉक्टर: आज तुम्हाला कसे वाटते?
रुग्ण: मला झोप येत नाही रात्री. खूप चिंता वाटते.

Example (Hindi):
डॉक्टर: आज आप कैसा महसूस कर रहे हैं?
मरीज: मुझे नींद नहीं आ रही है।

Example (English):
Doctor: How are you feeling today?
Patient: I'm not sleeping well at night.`}
            required
          />
        </div>

        {/* Patient Info */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">PHQ-8 Score</label>
            <input
              type="number"
              min="0"
              max="24"
              value={phq8Score}
              onChange={(e) => setPhq8Score(e.target.value)}
              className="w-full p-2 border rounded"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full p-2 border rounded"
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
            <label className="block text-sm font-medium mb-2">Gender</label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="unknown">Unknown</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        {/* Target Language */}
        <div>
          <label className="block text-sm font-medium mb-2">Output Language</label>
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className="w-full p-2 border rounded"
          >
            <option value="marathi">Marathi (मराठी)</option>
            <option value="hindi">Hindi (हिन्दी)</option>
          </select>
          <p className="text-sm text-gray-500 mt-1">
            English SOAP note will always be included
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Generating SOAP Note...' : 'Generate SOAP Note'}
        </button>
      </form>

      {/* Error Display */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div className="space-y-6">
          {/* Metadata */}
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold mb-2">Detection Info</h3>
            <p>Detected Language: <strong>{result.input_language}</strong></p>
            <p>Output Language: <strong>{result.target_language}</strong></p>
            <p>Processing Time: <strong>{result.metadata?.processing_time}</strong></p>
          </div>

          {/* English SOAP */}
          <div className="border rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4">English SOAP Note</h2>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-green-700">SUBJECTIVE</h3>
                <p className="whitespace-pre-wrap">{result.soap_english?.subjective}</p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-blue-700">OBJECTIVE</h3>
                <p className="whitespace-pre-wrap">{result.soap_english?.objective}</p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-orange-700">ASSESSMENT</h3>
                <p className="whitespace-pre-wrap">{result.soap_english?.assessment}</p>
              </div>
              
              <div>
                <h3 className="text-lg font-semibold text-purple-700">PLAN</h3>
                <p className="whitespace-pre-wrap">{result.soap_english?.plan}</p>
              </div>
            </div>
          </div>

          {/* Translated SOAP */}
          {result[`soap_${targetLang}`] && targetLang !== 'english' && (
            <div className="border rounded-lg p-6 bg-yellow-50">
              <h2 className="text-2xl font-bold mb-4">
                {targetLang === 'marathi' ? 'मराठी SOAP नोट' : 'हिन्दी SOAP नोट'}
              </h2>
              
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold text-green-700">
                    {targetLang === 'marathi' ? 'व्यक्तिनिष्ठ' : 'व्यक्तिपरक'}
                  </h3>
                  <p className="whitespace-pre-wrap">{result[`soap_${targetLang}`]?.subjective}</p>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-blue-700">वस्तुनिष्ठ</h3>
                  <p className="whitespace-pre-wrap">{result[`soap_${targetLang}`]?.objective}</p>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-orange-700">मूल्यांकन</h3>
                  <p className="whitespace-pre-wrap">{result[`soap_${targetLang}`]?.assessment}</p>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold text-purple-700">योजना</h3>
                  <p className="whitespace-pre-wrap">{result[`soap_${targetLang}`]?.plan}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
