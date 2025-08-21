import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Grid,
  IconButton,
  Collapse,
  Alert,
  Chip,
  Divider,
} from '@mui/material';
import {
  Send,
  ContentCopy,
  ExpandMore,
  ExpandLess,
  CloudUpload,
} from '@mui/icons-material';
import { toast } from 'react-toastify';
import api from '../../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const commonEndpoints = {
  auth: [
    { method: 'POST', path: '/auth/token/', description: 'Get JWT tokens' },
    { method: 'POST', path: '/auth/token/refresh/', description: 'Refresh token' },
    { method: 'POST', path: '/auth/login/', description: 'Login' },
    { method: 'POST', path: '/auth/logout/', description: 'Logout' },
    { method: 'GET', path: '/auth/user/', description: 'Get current user' },
  ],
  encounters: [
    { method: 'GET', path: '/encounters/', description: 'List encounters' },
    { method: 'POST', path: '/encounters/', description: 'Create encounter' },
    { method: 'GET', path: '/encounters/{id}/', description: 'Get encounter' },
    { method: 'PATCH', path: '/encounters/{id}/', description: 'Update encounter' },
    { method: 'DELETE', path: '/encounters/{id}/', description: 'Delete encounter' },
    { method: 'POST', path: '/encounters/{id}/process/', description: 'Process audio' },
    { method: 'POST', path: '/encounters/{id}/generate-soap/', description: 'Generate SOAP' },
  ],
  patients: [
    { method: 'GET', path: '/patients/', description: 'List patients' },
    { method: 'POST', path: '/patients/', description: 'Create patient' },
    { method: 'GET', path: '/patients/{id}/', description: 'Get patient' },
    { method: 'PATCH', path: '/patients/{id}/', description: 'Update patient' },
    { method: 'DELETE', path: '/patients/{id}/', description: 'Delete patient' },
  ],
  checklist: [
    { method: 'GET', path: '/checklist/templates/', description: 'List templates' },
    { method: 'POST', path: '/checklist/templates/', description: 'Create template' },
    { method: 'GET', path: '/checklist/templates/{id}/', description: 'Get template' },
  ],
  analytics: [
    { method: 'GET', path: '/analytics/dashboard/', description: 'Dashboard stats' },
    { method: 'GET', path: '/analytics/encounters/', description: 'Encounter stats' },
    { method: 'GET', path: '/analytics/patients/', description: 'Patient stats' },
  ],
};

export default function ApiTester() {
  const [method, setMethod] = useState('GET');
  const [endpoint, setEndpoint] = useState('');
  const [headers, setHeaders] = useState('{\n  "Content-Type": "application/json"\n}');
  const [body, setBody] = useState('');
  const [response, setResponse] = useState('');
  const [status, setStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleSendRequest = async () => {
    setLoading(true);
    setResponse('');
    setStatus(null);

    try {
      let parsedHeaders = {};
      try {
        parsedHeaders = JSON.parse(headers);
      } catch (e) {
        toast.error('Invalid headers JSON');
        setLoading(false);
        return;
      }

      let requestBody: any = null;
      if (body && method !== 'GET') {
        if (selectedFile) {
          const formData = new FormData();
          formData.append('audio_file', selectedFile);
          if (body) {
            try {
              const bodyData = JSON.parse(body);
              Object.keys(bodyData).forEach((key) => {
                formData.append(key, bodyData[key]);
              });
            } catch (e) {
              // Body is not JSON, ignore
            }
          }
          requestBody = formData;
          delete parsedHeaders['Content-Type']; // Let browser set it for FormData
        } else {
          try {
            requestBody = JSON.parse(body);
          } catch (e) {
            requestBody = body;
          }
        }
      }

      const config: any = {
        method,
        url: endpoint,
        headers: parsedHeaders,
      };

      if (requestBody) {
        config.data = requestBody;
      }

      const res = await api.request(config);
      setStatus(res.status);
      setResponse(JSON.stringify(res.data, null, 2));
      toast.success(`Request successful: ${res.status}`);
    } catch (error: any) {
      setStatus(error.response?.status || 0);
      setResponse(
        JSON.stringify(
          error.response?.data || { error: error.message },
          null,
          2
        )
      );
      toast.error(`Request failed: ${error.response?.status || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleEndpointClick = (endpointInfo: any) => {
    setMethod(endpointInfo.method);
    setEndpoint(endpointInfo.path);
    
    // Set default body for POST/PATCH requests
    if (endpointInfo.method === 'POST' || endpointInfo.method === 'PATCH') {
      switch (endpointInfo.path) {
        case '/auth/token/':
          setBody('{\n  "username": "admin",\n  "password": "admin123"\n}');
          break;
        case '/auth/login/':
          setBody('{\n  "username": "admin",\n  "password": "admin123"\n}');
          break;
        case '/encounters/':
          setBody('{\n  "patient": 1,\n  "chief_complaint": "Test complaint"\n}');
          break;
        case '/patients/':
          setBody('{\n  "first_name": "John",\n  "last_name": "Doe",\n  "date_of_birth": "1990-01-01",\n  "gender": "male"\n}');
          break;
        default:
          setBody('{}');
      }
    } else {
      setBody('');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        API Tester
      </Typography>
      
      <Grid container spacing={3}>
        {/* Request Section */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Request
            </Typography>
            
            {/* Method and Endpoint */}
            <Box display="flex" gap={2} mb={2}>
              <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Method</InputLabel>
                <Select
                  value={method}
                  label="Method"
                  onChange={(e) => setMethod(e.target.value)}
                >
                  <MenuItem value="GET">GET</MenuItem>
                  <MenuItem value="POST">POST</MenuItem>
                  <MenuItem value="PUT">PUT</MenuItem>
                  <MenuItem value="PATCH">PATCH</MenuItem>
                  <MenuItem value="DELETE">DELETE</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Endpoint"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="/api/endpoint"
              />
            </Box>

            {/* Common Endpoints */}
            <Box mb={2}>
              <Typography variant="subtitle2" gutterBottom>
                Common Endpoints:
              </Typography>
              {Object.entries(commonEndpoints).map(([category, endpoints]) => (
                <Box key={category} mb={1}>
                  <Box
                    display="flex"
                    alignItems="center"
                    onClick={() =>
                      setExpandedCategory(
                        expandedCategory === category ? null : category
                      )
                    }
                    sx={{ cursor: 'pointer' }}
                  >
                    <IconButton size="small">
                      {expandedCategory === category ? (
                        <ExpandLess />
                      ) : (
                        <ExpandMore />
                      )}
                    </IconButton>
                    <Typography variant="body2" fontWeight="bold">
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </Typography>
                  </Box>
                  <Collapse in={expandedCategory === category}>
                    <Box pl={4}>
                      {endpoints.map((ep, index) => (
                        <Box
                          key={index}
                          display="flex"
                          alignItems="center"
                          gap={1}
                          mb={0.5}
                          sx={{
                            cursor: 'pointer',
                            '&:hover': { backgroundColor: 'action.hover' },
                            p: 0.5,
                            borderRadius: 1,
                          }}
                          onClick={() => handleEndpointClick(ep)}
                        >
                          <Chip
                            label={ep.method}
                            size="small"
                            color={
                              ep.method === 'GET'
                                ? 'primary'
                                : ep.method === 'POST'
                                ? 'success'
                                : ep.method === 'DELETE'
                                ? 'error'
                                : 'warning'
                            }
                          />
                          <Typography variant="body2">{ep.path}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            - {ep.description}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Collapse>
                </Box>
              ))}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Request Tabs */}
            <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
              <Tab label="Headers" />
              <Tab label="Body" />
              <Tab label="File Upload" />
            </Tabs>

            <TabPanel value={tabValue} index={0}>
              <TextField
                fullWidth
                multiline
                rows={6}
                value={headers}
                onChange={(e) => setHeaders(e.target.value)}
                placeholder="Enter headers as JSON"
              />
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <TextField
                fullWidth
                multiline
                rows={10}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Enter request body"
                disabled={method === 'GET'}
              />
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              <Alert severity="info" sx={{ mb: 2 }}>
                File upload is mainly used for audio files in encounter creation
              </Alert>
              <Button
                variant="outlined"
                component="label"
                startIcon={<CloudUpload />}
              >
                Upload File
                <input
                  type="file"
                  hidden
                  onChange={handleFileChange}
                  accept="audio/*"
                />
              </Button>
              {selectedFile && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Selected: {selectedFile.name}
                </Typography>
              )}
            </TabPanel>

            <Button
              fullWidth
              variant="contained"
              startIcon={<Send />}
              onClick={handleSendRequest}
              disabled={loading || !endpoint}
              sx={{ mt: 2 }}
            >
              {loading ? 'Sending...' : 'Send Request'}
            </Button>
          </Paper>
        </Grid>

        {/* Response Section */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">Response</Typography>
              {status && (
                <Chip
                  label={`Status: ${status}`}
                  color={status >= 200 && status < 300 ? 'success' : 'error'}
                />
              )}
            </Box>
            
            <Box position="relative" mt={2}>
              {response && (
                <IconButton
                  size="small"
                  onClick={() => copyToClipboard(response)}
                  sx={{ position: 'absolute', top: 8, right: 8 }}
                >
                  <ContentCopy />
                </IconButton>
              )}
              <TextField
                fullWidth
                multiline
                rows={20}
                value={response}
                placeholder="Response will appear here..."
                InputProps={{
                  readOnly: true,
                  sx: { fontFamily: 'monospace' },
                }}
              />
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}