import api from './api';
import { AnalyticsData } from '../store/slices/analyticsSlice';

export const analyticsService = {
  async getAnalytics(params?: {
    startDate?: string;
    endDate?: string;
  }): Promise<AnalyticsData> {
    const response = await api.get('/analytics/dashboard/', { params });
    return response.data;
  },

  async getEncounterStats(params?: {
    startDate?: string;
    endDate?: string;
    groupBy?: 'day' | 'week' | 'month';
  }) {
    const response = await api.get('/analytics/encounters/', { params });
    return response.data;
  },

  async getPatientStats() {
    const response = await api.get('/analytics/patients/');
    return response.data;
  },

  async getProcessingStats() {
    const response = await api.get('/analytics/processing/');
    return response.data;
  },

  async getChiefComplaintStats(limit: number = 10) {
    const response = await api.get('/analytics/chief-complaints/', {
      params: { limit },
    });
    return response.data;
  },

  async getUserActivityStats() {
    const response = await api.get('/analytics/user-activity/');
    return response.data;
  },

  async exportAnalytics(params: {
    startDate: string;
    endDate: string;
    format: 'csv' | 'xlsx' | 'pdf';
  }): Promise<Blob> {
    const response = await api.get('/analytics/export/', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};