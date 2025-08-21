import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import { CloudUpload, Send, CheckCircle } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useDispatch, useSelector } from 'react-redux';
import { createEncounter } from '../../store/slices/encounterSlice';
import { fetchPatients } from '../../store/slices/patientSlice';
import { AppDispatch, RootState } from '../../store/store';
import { toast } from 'react-toastify';

export default function AudioUpload() {
  const dispatch = useDispatch<AppDispatch>();
  const { patients } = useSelector((state: RootState) => state.patients);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [patientId, setPatientId] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [notes, setNotes] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  React.useEffect(() => {
    dispatch(fetchPatients());
  }, [dispatch]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      setUploadSuccess(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.ogg', '.webm'],
    },
    maxFiles: 1,
  });

  const handleSubmit = async () => {
    if (!selectedFile || !patientId) {
      toast.error('Please select a file and patient');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('audio_file', selectedFile);
    formData.append('patient', patientId);
    formData.append('chief_complaint', chiefComplaint);
    if (notes) {
      formData.append('notes', notes);
    }

    try {
      await dispatch(createEncounter(formData)).unwrap();
      setUploadSuccess(true);
      // Reset form
      setSelectedFile(null);
      setPatientId('');
      setChiefComplaint('');
      setNotes('');
      toast.success('Audio uploaded successfully! Processing will begin shortly.');
    } catch (error) {
      toast.error('Failed to upload audio');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Upload Audio Recording
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            {/* File Upload Area */}
            <Box
              {...getRootProps()}
              sx={{
                border: '2px dashed',
                borderColor: isDragActive ? 'primary.main' : 'grey.300',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
                mb: 3,
              }}
            >
              <input {...getInputProps()} />
              <CloudUpload sx={{ fontSize: 48, color: 'action.active', mb: 2 }} />
              {isDragActive ? (
                <Typography>Drop the audio file here...</Typography>
              ) : (
                <Box>
                  <Typography variant="h6">
                    Drag & drop an audio file here, or click to select
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mt={1}>
                    Supported formats: MP3, WAV, M4A, OGG, WebM
                  </Typography>
                </Box>
              )}
            </Box>

            {selectedFile && (
              <Alert severity="info" sx={{ mb: 3 }}>
                Selected file: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </Alert>
            )}

            {/* Form Fields */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Patient</InputLabel>
              <Select
                value={patientId}
                label="Patient"
                onChange={(e) => setPatientId(e.target.value)}
              >
                {patients.map((patient) => (
                  <MenuItem key={patient.id} value={patient.id}>
                    {patient.first_name} {patient.last_name} - {patient.medical_record_number || `ID: ${patient.id}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Chief Complaint"
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
              sx={{ mb: 3 }}
              placeholder="e.g., Chest pain, shortness of breath"
            />

            <TextField
              fullWidth
              label="Additional Notes (Optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              multiline
              rows={4}
              sx={{ mb: 3 }}
              placeholder="Any additional information about the encounter..."
            />

            {uploading && <LinearProgress sx={{ mb: 2 }} />}

            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={handleSubmit}
              disabled={!selectedFile || !patientId || uploading}
              startIcon={uploading ? null : <Send />}
            >
              {uploading ? 'Uploading...' : 'Upload & Process'}
            </Button>

            {uploadSuccess && (
              <Alert severity="success" sx={{ mt: 2 }} icon={<CheckCircle />}>
                Upload successful! The audio is being processed. You can view the status in the Encounters page.
              </Alert>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Processing Information
              </Typography>
              <Typography variant="body2" paragraph>
                Once uploaded, your audio file will be:
              </Typography>
              <ol>
                <li>Transcribed using speech-to-text technology</li>
                <li>Analyzed for medical information</li>
                <li>Converted into a structured SOAP note</li>
              </ol>
              <Typography variant="body2" color="text.secondary" mt={2}>
                Processing typically takes 1-5 minutes depending on the length of the recording.
              </Typography>
            </CardContent>
          </Card>

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Tips for Best Results
              </Typography>
              <ul>
                <li>Use a quiet environment for recording</li>
                <li>Speak clearly and at a moderate pace</li>
                <li>State the patient's chief complaint early in the recording</li>
                <li>Include relevant medical history and symptoms</li>
                <li>Keep recordings under 10 minutes when possible</li>
              </ul>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}