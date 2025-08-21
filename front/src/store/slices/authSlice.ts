import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { authService } from '../../services/authService';
import { toast } from 'react-toastify';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

interface AuthState {
  user: User | null;
  access: string | null;
  refresh: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  access: localStorage.getItem('access'),
  refresh: localStorage.getItem('refresh'),
  isAuthenticated: !!localStorage.getItem('access'),
  loading: false,
  error: null,
};

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }) => {
    const response = await authService.login(credentials);
    return response;
  }
);

export const logout = createAsyncThunk('auth/logout', async () => {
  await authService.logout();
});

export const refreshToken = createAsyncThunk(
  'auth/refresh',
  async (_, { getState }) => {
    const state = getState() as { auth: AuthState };
    const refreshToken = state.auth.refresh;
    if (!refreshToken) throw new Error('No refresh token');
    const response = await authService.refreshToken(refreshToken);
    return response;
  }
);

export const getCurrentUser = createAsyncThunk(
  'auth/getCurrentUser',
  async () => {
    const response = await authService.getCurrentUser();
    return response;
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{ access: string; refresh: string }>
    ) => {
      state.access = action.payload.access;
      state.refresh = action.payload.refresh;
      state.isAuthenticated = true;
      localStorage.setItem('access', action.payload.access);
      localStorage.setItem('refresh', action.payload.refresh);
    },
    clearAuth: (state) => {
      state.user = null;
      state.access = null;
      state.refresh = null;
      state.isAuthenticated = false;
      state.error = null;
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false;
        state.access = action.payload.access;
        state.refresh = action.payload.refresh;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        localStorage.setItem('access', action.payload.access);
        localStorage.setItem('refresh', action.payload.refresh);
        toast.success('Login successful!');
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Login failed';
        toast.error(state.error);
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.access = null;
        state.refresh = null;
        state.isAuthenticated = false;
        state.error = null;
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        toast.success('Logged out successfully');
      })
      // Get current user
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(getCurrentUser.rejected, (state) => {
        state.user = null;
      })
      // Refresh token
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.access = action.payload.access;
        localStorage.setItem('access', action.payload.access);
      })
      .addCase(refreshToken.rejected, (state) => {
        state.user = null;
        state.access = null;
        state.refresh = null;
        state.isAuthenticated = false;
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
      });
  },
});

export const { setCredentials, clearAuth } = authSlice.actions;
export default authSlice.reducer;