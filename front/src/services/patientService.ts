import api from './api';
import { Patient } from '../store/slices/patientSlice';

interface PatientListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Patient[];
}

export const patientService = {
  async getPatients(params?: { search?: string }): Promise<PatientListResponse> {
    const response = await api.get('/patients/', {
      params: {
        search: params?.search,
      },
    });
    return response.data;
  },

  async getPatientById(id: number): Promise<Patient> {
    const response = await api.get(`/patients/${id}/`);
    return response.data;
  },

  async createPatient(
    data: Omit<Patient, 'id' | 'created_at' | 'updated_at'>
  ): Promise<Patient> {
    const response = await api.post('/patients/', data);
    return response.data;
  },

  async updatePatient(id: number, data: Partial<Patient>): Promise<Patient> {
    const response = await api.patch(`/patients/${id}/`, data);
    return response.data;
  },

  async deletePatient(id: number): Promise<void> {
    await api.delete(`/patients/${id}/`);
  },

  async getPatientEncounters(patientId: number): Promise<any[]> {
    const response = await api.get(`/patients/${patientId}/encounters/`);
    return response.data;
  },

  async searchPatients(query: string): Promise<PatientListResponse> {
    const response = await api.get('/patients/search/', {
      params: { q: query },
    });
    return response.data;
  },

  async exportPatientData(patientId: number): Promise<Blob> {
    const response = await api.get(`/patients/${patientId}/export/`, {
      responseType: 'blob',
    });
    return response.data;
  },
};