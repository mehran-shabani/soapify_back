import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import {
  Add,
  Search,
  Refresh,
  Edit,
  Delete,
  AudioFile,
  Description,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import {
  fetchEncounters,
  deleteEncounter,
  setCurrentPage,
  setPageSize,
} from '../../store/slices/encounterSlice';
import { RootState, AppDispatch } from '../../store/store';
import { format } from 'date-fns';
import { toast } from 'react-toastify';

export default function Encounters() {
  const dispatch = useDispatch<AppDispatch>();
  const { encounters, loading, totalCount, currentPage, pageSize } = useSelector(
    (state: RootState) => state.encounters
  );
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedEncounterId, setSelectedEncounterId] = useState<number | null>(null);

  useEffect(() => {
    dispatch(fetchEncounters({ page: currentPage, pageSize }));
  }, [dispatch, currentPage, pageSize]);

  const handleSearch = () => {
    dispatch(fetchEncounters({ page: 1, pageSize, search: searchTerm }));
  };

  const handleRefresh = () => {
    dispatch(fetchEncounters({ page: currentPage, pageSize }));
  };

  const handleDelete = async () => {
    if (selectedEncounterId) {
      await dispatch(deleteEncounter(selectedEncounterId));
      setDeleteDialogOpen(false);
      setSelectedEncounterId(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'patient_name',
      headerName: 'Patient',
      width: 200,
      valueGetter: (params) => params.row.patient_name || `Patient #${params.row.patient}`,
    },
    {
      field: 'encounter_date',
      headerName: 'Date',
      width: 150,
      valueFormatter: (params) => {
        if (params.value) {
          return format(new Date(params.value), 'MMM dd, yyyy');
        }
        return '';
      },
    },
    {
      field: 'chief_complaint',
      headerName: 'Chief Complaint',
      width: 250,
      renderCell: (params) => (
        <Typography variant="body2" noWrap>
          {params.value || '-'}
        </Typography>
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={getStatusColor(params.value)}
        />
      ),
    },
    {
      field: 'audio_file',
      headerName: 'Audio',
      width: 80,
      renderCell: (params) => (
        params.value ? <AudioFile color="action" /> : <span>-</span>
      ),
    },
    {
      field: 'soap_note',
      headerName: 'SOAP',
      width: 80,
      renderCell: (params) => (
        params.value ? <Description color="action" /> : <span>-</span>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 150,
      sortable: false,
      renderCell: (params) => (
        <Box>
          <IconButton
            size="small"
            onClick={() => {
              // Navigate to encounter detail
              window.location.href = `/encounters/${params.row.id}`;
            }}
          >
            <Edit />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => {
              setSelectedEncounterId(params.row.id);
              setDeleteDialogOpen(true);
            }}
          >
            <Delete />
          </IconButton>
        </Box>
      ),
    },
  ];

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Encounters</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => {
            window.location.href = '/audio-upload';
          }}
        >
          New Encounter
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Box display="flex" gap={2} mb={3}>
          <TextField
            fullWidth
            placeholder="Search encounters..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleSearch();
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
          <Button variant="outlined" onClick={handleSearch}>
            Search
          </Button>
          <IconButton onClick={handleRefresh}>
            <Refresh />
          </IconButton>
        </Box>

        {loading && <LinearProgress />}

        <DataGrid
          rows={encounters}
          columns={columns}
          paginationModel={{
            page: currentPage - 1,
            pageSize: pageSize,
          }}
          onPaginationModelChange={(model) => {
            dispatch(setCurrentPage(model.page + 1));
            dispatch(setPageSize(model.pageSize));
          }}
          pageSizeOptions={[5, 10, 25, 50]}
          rowCount={totalCount}
          paginationMode="server"
          autoHeight
          disableRowSelectionOnClick
        />
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          Are you sure you want to delete this encounter? This action cannot be undone.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}