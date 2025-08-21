import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { Box } from '@mui/material';

import Layout from './components/Layout/Layout';
import PrivateRoute from './components/PrivateRoute/PrivateRoute';
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import Encounters from './pages/Encounters/Encounters';
import Patients from './pages/Patients/Patients';
import AudioUpload from './pages/AudioUpload/AudioUpload';
import Checklist from './pages/Checklist/Checklist';
import Analytics from './pages/Analytics/Analytics';
import Settings from './pages/Settings/Settings';
import ApiTester from './pages/ApiTester/ApiTester';
import { RootState } from './store/store';

function App() {
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  return (
    <Box sx={{ display: 'flex' }}>
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/dashboard" />} />
        <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route index element={<Navigate to="/dashboard" />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="encounters" element={<Encounters />} />
          <Route path="patients" element={<Patients />} />
          <Route path="audio-upload" element={<AudioUpload />} />
          <Route path="checklist" element={<Checklist />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="api-tester" element={<ApiTester />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Box>
  );
}

export default App;