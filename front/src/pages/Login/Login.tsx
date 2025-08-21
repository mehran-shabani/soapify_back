import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import { login } from '../../store/slices/authSlice';
import { AppDispatch } from '../../store/store';

const validationSchema = yup.object({
  username: yup.string().required('Username is required'),
  password: yup.string().required('Password is required'),
});

export default function Login() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const formik = useFormik({
    initialValues: {
      username: '',
      password: '',
    },
    validationSchema: validationSchema,
    onSubmit: async (values) => {
      setError(null);
      setLoading(true);
      try {
        await dispatch(login(values)).unwrap();
        navigate('/dashboard');
      } catch (err: any) {
        setError(err.message || 'Login failed. Please check your credentials.');
      } finally {
        setLoading(false);
      }
    },
  });

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            SOAPify Login
          </Typography>
          <Typography variant="body2" color="textSecondary" align="center" sx={{ mb: 3 }}>
            Medical Documentation Platform
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Box component="form" onSubmit={formik.handleSubmit} noValidate>
            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="Username"
              name="username"
              autoComplete="username"
              autoFocus
              value={formik.values.username}
              onChange={formik.handleChange}
              error={formik.touched.username && Boolean(formik.errors.username)}
              helperText={formik.touched.username && formik.errors.username}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={formik.values.password}
              onChange={formik.handleChange}
              error={formik.touched.password && Boolean(formik.errors.password)}
              helperText={formik.touched.password && formik.errors.password}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Sign In'}
            </Button>
          </Box>
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="textSecondary">
              Demo credentials: admin / admin123
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}