import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { patientService } from '../../services/patientService';
import { toast } from 'react-toastify';

export interface Patient {
  id: number;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: 'male' | 'female' | 'other';
  email?: string;
  phone?: string;
  address?: string;
  medical_record_number?: string;
  created_at: string;
  updated_at: string;
}

interface PatientState {
  patients: Patient[];
  currentPatient: Patient | null;
  loading: boolean;
  error: string | null;
  totalCount: number;
}

const initialState: PatientState = {
  patients: [],
  currentPatient: null,
  loading: false,
  error: null,
  totalCount: 0,
};

export const fetchPatients = createAsyncThunk(
  'patients/fetchAll',
  async (params?: { search?: string }) => {
    const response = await patientService.getPatients(params);
    return response;
  }
);

export const fetchPatientById = createAsyncThunk(
  'patients/fetchById',
  async (id: number) => {
    const response = await patientService.getPatientById(id);
    return response;
  }
);

export const createPatient = createAsyncThunk(
  'patients/create',
  async (data: Omit<Patient, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await patientService.createPatient(data);
    return response;
  }
);

export const updatePatient = createAsyncThunk(
  'patients/update',
  async ({ id, data }: { id: number; data: Partial<Patient> }) => {
    const response = await patientService.updatePatient(id, data);
    return response;
  }
);

export const deletePatient = createAsyncThunk(
  'patients/delete',
  async (id: number) => {
    await patientService.deletePatient(id);
    return id;
  }
);

const patientSlice = createSlice({
  name: 'patients',
  initialState,
  reducers: {
    clearCurrentPatient: (state) => {
      state.currentPatient = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch patients
      .addCase(fetchPatients.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPatients.fulfilled, (state, action) => {
        state.loading = false;
        state.patients = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(fetchPatients.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch patients';
        toast.error(state.error);
      })
      // Fetch patient by ID
      .addCase(fetchPatientById.fulfilled, (state, action) => {
        state.currentPatient = action.payload;
      })
      // Create patient
      .addCase(createPatient.fulfilled, (state, action) => {
        state.patients.unshift(action.payload);
        state.totalCount += 1;
        toast.success('Patient created successfully');
      })
      // Update patient
      .addCase(updatePatient.fulfilled, (state, action) => {
        const index = state.patients.findIndex(p => p.id === action.payload.id);
        if (index !== -1) {
          state.patients[index] = action.payload;
        }
        if (state.currentPatient?.id === action.payload.id) {
          state.currentPatient = action.payload;
        }
        toast.success('Patient updated successfully');
      })
      // Delete patient
      .addCase(deletePatient.fulfilled, (state, action) => {
        state.patients = state.patients.filter(p => p.id !== action.payload);
        state.totalCount -= 1;
        toast.success('Patient deleted successfully');
      });
  },
});

export const { clearCurrentPatient } = patientSlice.actions;
export default patientSlice.reducer;