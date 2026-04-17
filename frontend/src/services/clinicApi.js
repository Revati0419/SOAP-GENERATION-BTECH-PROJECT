import axios from 'axios';
import { apiUrl } from '../lib/api';

export async function fetchPatients(query = '', limit = 50) {
  const { data } = await axios.get(apiUrl('/api/patients'), {
    params: { query: query || undefined, limit },
  });
  return data;
}

export async function createPatient(payload) {
  const { data } = await axios.post(apiUrl('/api/patients'), payload);
  return data;
}

export async function fetchStats() {
  const { data } = await axios.get(apiUrl('/api/stats'));
  return data;
}

export async function createSession(payload) {
  const { data } = await axios.post(apiUrl('/api/sessions'), payload);
  return data;
}

export async function fetchPatientSessions(patientId, limit = 100) {
  const { data } = await axios.get(apiUrl(`/api/patients/${patientId}/sessions`), {
    params: { limit },
  });
  return data;
}

export async function fetchRecentSessions(limit = 100) {
  const { data } = await axios.get(apiUrl('/api/sessions'), {
    params: { limit },
  });
  return data;
}
