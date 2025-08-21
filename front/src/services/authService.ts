import api from './api';

interface LoginCredentials {
  username: string;
  password: string;
}

interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    is_staff: boolean;
  };
}

interface RefreshResponse {
  access: string;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await api.post('/auth/login/', credentials);
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout/');
    } catch (error) {
      // Ignore logout errors
    }
  },

  async refreshToken(refreshToken: string): Promise<RefreshResponse> {
    const response = await api.post('/auth/token/refresh/', {
      refresh: refreshToken,
    });
    return response.data;
  },

  async getCurrentUser() {
    const response = await api.get('/auth/user/');
    return response.data;
  },

  async changePassword(data: {
    current_password: string;
    new_password: string;
  }) {
    const response = await api.post('/auth/change-password/', data);
    return response.data;
  },

  async register(data: {
    username: string;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }) {
    const response = await api.post('/auth/register/', data);
    return response.data;
  },
};