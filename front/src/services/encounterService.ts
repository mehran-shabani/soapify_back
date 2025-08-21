import api from './api';
import { Encounter } from '../store/slices/encounterSlice';

interface EncounterListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Encounter[];
}

export const encounterService = {
  async getEncounters(params?: {
    page?: number;
    pageSize?: number;
    search?: string;
  }): Promise<EncounterListResponse> {
    const response = await api.get('/encounters/', {
      params: {
        page: params?.page || 1,
        page_size: params?.pageSize || 10,
        search: params?.search,
      },
    });
    return response.data;
  },

  async getEncounterById(id: number): Promise<Encounter> {
    const response = await api.get(`/encounters/${id}/`);
    return response.data;
  },

  async createEncounter(data: FormData): Promise<Encounter> {
    const response = await api.post('/encounters/', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async updateEncounter(
    id: number,
    data: Partial<Encounter>
  ): Promise<Encounter> {
    const response = await api.patch(`/encounters/${id}/`, data);
    return response.data;
  },

  async deleteEncounter(id: number): Promise<void> {
    await api.delete(`/encounters/${id}/`);
  },

  async processAudio(id: number): Promise<Encounter> {
    const response = await api.post(`/encounters/${id}/process/`);
    return response.data;
  },

  async generateSOAP(id: number): Promise<Encounter> {
    const response = await api.post(`/encounters/${id}/generate-soap/`);
    return response.data;
  },

  async downloadSOAP(id: number, format: 'pdf' | 'docx' = 'pdf'): Promise<Blob> {
    const response = await api.get(`/encounters/${id}/download/`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },

  async getTranscription(id: number): Promise<{ transcription: string }> {
    const response = await api.get(`/encounters/${id}/transcription/`);
    return response.data;
  },

  async updateTranscription(
    id: number,
    transcription: string
  ): Promise<Encounter> {
    const response = await api.patch(`/encounters/${id}/transcription/`, {
      transcription,
    });
    return response.data;
  },

  async searchEncounters(query: string): Promise<EncounterListResponse> {
    const response = await api.get('/encounters/search/', {
      params: { q: query },
    });
    return response.data;
  },
};