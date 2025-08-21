import React, { useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';
import {
  Assignment,
  People,
  CheckCircle,
  Pending,
  TrendingUp,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { fetchAnalytics } from '../../store/slices/analyticsSlice';
import { RootState, AppDispatch } from '../../store/store';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function Dashboard() {
  const dispatch = useDispatch<AppDispatch>();
  const { data: analytics, loading } = useSelector(
    (state: RootState) => state.analytics
  );

  useEffect(() => {
    dispatch(fetchAnalytics());
  }, [dispatch]);

  if (loading) {
    return <LinearProgress />;
  }

  const stats = [
    {
      title: 'Total Encounters',
      value: analytics?.totalEncounters || 0,
      icon: <Assignment />,
      color: '#1976d2',
    },
    {
      title: 'Total Patients',
      value: analytics?.totalPatients || 0,
      icon: <People />,
      color: '#388e3c',
    },
    {
      title: 'Completed Today',
      value: analytics?.encountersToday || 0,
      icon: <CheckCircle />,
      color: '#f57c00',
    },
    {
      title: 'Pending',
      value: analytics?.encountersByStatus?.pending || 0,
      icon: <Pending />,
      color: '#d32f2f',
    },
  ];

  const statusData = analytics?.encountersByStatus
    ? Object.entries(analytics.encountersByStatus).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Grid container spacing={3}>
        {/* Stats Cards */}
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Box
                    sx={{
                      backgroundColor: stat.color,
                      color: 'white',
                      p: 1,
                      borderRadius: 1,
                      mr: 2,
                    }}
                  >
                    {stat.icon}
                  </Box>
                  <Typography color="textSecondary" variant="body2">
                    {stat.title}
                  </Typography>
                </Box>
                <Typography variant="h4">{stat.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {/* Encounters Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Encounters Trend
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={analytics?.encountersByDay || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#8884d8"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Status Pie Chart */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Encounter Status
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Common Complaints */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Most Common Chief Complaints
            </Typography>
            <Grid container spacing={2}>
              {analytics?.mostCommonComplaints?.slice(0, 5).map((complaint, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Typography variant="body1">{complaint.complaint}</Typography>
                    <Typography variant="h6" color="primary">
                      {complaint.count}
                    </Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}