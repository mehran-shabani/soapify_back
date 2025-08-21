import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { analyticsService } from '../../services/analyticsService';

export interface AnalyticsData {
  totalEncounters: number;
  totalPatients: number;
  encountersToday: number;
  encountersThisWeek: number;
  encountersThisMonth: number;
  encountersByStatus: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  encountersByDay: Array<{
    date: string;
    count: number;
  }>;
  averageProcessingTime: number;
  mostCommonComplaints: Array<{
    complaint: string;
    count: number;
  }>;
}

interface AnalyticsState {
  data: AnalyticsData | null;
  loading: boolean;
  error: string | null;
}

const initialState: AnalyticsState = {
  data: null,
  loading: false,
  error: null,
};

export const fetchAnalytics = createAsyncThunk(
  'analytics/fetch',
  async (params?: { startDate?: string; endDate?: string }) => {
    const response = await analyticsService.getAnalytics(params);
    return response;
  }
);

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchAnalytics.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAnalytics.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
      })
      .addCase(fetchAnalytics.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch analytics';
      });
  },
});

export default analyticsSlice.reducer;