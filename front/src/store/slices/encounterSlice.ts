import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { encounterService } from '../../services/encounterService';
import { toast } from 'react-toastify';

export interface Encounter {
  id: number;
  patient: number;
  patient_name?: string;
  encounter_date: string;
  audio_file?: string;
  transcription?: string;
  soap_note?: string;
  chief_complaint?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

interface EncounterState {
  encounters: Encounter[];
  currentEncounter: Encounter | null;
  loading: boolean;
  error: string | null;
  totalCount: number;
  currentPage: number;
  pageSize: number;
}

const initialState: EncounterState = {
  encounters: [],
  currentEncounter: null,
  loading: false,
  error: null,
  totalCount: 0,
  currentPage: 1,
  pageSize: 10,
};

export const fetchEncounters = createAsyncThunk(
  'encounters/fetchAll',
  async (params?: { page?: number; pageSize?: number; search?: string }) => {
    const response = await encounterService.getEncounters(params);
    return response;
  }
);

export const fetchEncounterById = createAsyncThunk(
  'encounters/fetchById',
  async (id: number) => {
    const response = await encounterService.getEncounterById(id);
    return response;
  }
);

export const createEncounter = createAsyncThunk(
  'encounters/create',
  async (data: FormData) => {
    const response = await encounterService.createEncounter(data);
    return response;
  }
);

export const updateEncounter = createAsyncThunk(
  'encounters/update',
  async ({ id, data }: { id: number; data: Partial<Encounter> }) => {
    const response = await encounterService.updateEncounter(id, data);
    return response;
  }
);

export const deleteEncounter = createAsyncThunk(
  'encounters/delete',
  async (id: number) => {
    await encounterService.deleteEncounter(id);
    return id;
  }
);

export const processAudio = createAsyncThunk(
  'encounters/processAudio',
  async (id: number) => {
    const response = await encounterService.processAudio(id);
    return response;
  }
);

const encounterSlice = createSlice({
  name: 'encounters',
  initialState,
  reducers: {
    setCurrentPage: (state, action) => {
      state.currentPage = action.payload;
    },
    setPageSize: (state, action) => {
      state.pageSize = action.payload;
    },
    clearCurrentEncounter: (state) => {
      state.currentEncounter = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch encounters
      .addCase(fetchEncounters.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchEncounters.fulfilled, (state, action) => {
        state.loading = false;
        state.encounters = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(fetchEncounters.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch encounters';
        toast.error(state.error);
      })
      // Fetch encounter by ID
      .addCase(fetchEncounterById.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchEncounterById.fulfilled, (state, action) => {
        state.loading = false;
        state.currentEncounter = action.payload;
      })
      .addCase(fetchEncounterById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch encounter';
        toast.error(state.error);
      })
      // Create encounter
      .addCase(createEncounter.pending, (state) => {
        state.loading = true;
      })
      .addCase(createEncounter.fulfilled, (state, action) => {
        state.loading = false;
        state.encounters.unshift(action.payload);
        state.totalCount += 1;
        toast.success('Encounter created successfully');
      })
      .addCase(createEncounter.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create encounter';
        toast.error(state.error);
      })
      // Update encounter
      .addCase(updateEncounter.fulfilled, (state, action) => {
        const index = state.encounters.findIndex(e => e.id === action.payload.id);
        if (index !== -1) {
          state.encounters[index] = action.payload;
        }
        if (state.currentEncounter?.id === action.payload.id) {
          state.currentEncounter = action.payload;
        }
        toast.success('Encounter updated successfully');
      })
      // Delete encounter
      .addCase(deleteEncounter.fulfilled, (state, action) => {
        state.encounters = state.encounters.filter(e => e.id !== action.payload);
        state.totalCount -= 1;
        toast.success('Encounter deleted successfully');
      })
      // Process audio
      .addCase(processAudio.pending, (state) => {
        state.loading = true;
      })
      .addCase(processAudio.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.encounters.findIndex(e => e.id === action.payload.id);
        if (index !== -1) {
          state.encounters[index] = action.payload;
        }
        if (state.currentEncounter?.id === action.payload.id) {
          state.currentEncounter = action.payload;
        }
        toast.success('Audio processing started');
      })
      .addCase(processAudio.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to process audio';
        toast.error(state.error);
      });
  },
});

export const { setCurrentPage, setPageSize, clearCurrentEncounter } = encounterSlice.actions;
export default encounterSlice.reducer;