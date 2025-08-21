import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import encounterReducer from './slices/encounterSlice';
import patientReducer from './slices/patientSlice';
import checklistReducer from './slices/checklistSlice';
import analyticsReducer from './slices/analyticsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    encounters: encounterReducer,
    patients: patientReducer,
    checklist: checklistReducer,
    analytics: analyticsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;