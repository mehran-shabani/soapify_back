import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { checklistService } from '../../services/checklistService';
import { toast } from 'react-toastify';

export interface ChecklistItem {
  id: number;
  title: string;
  description?: string;
  category: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChecklistTemplate {
  id: number;
  name: string;
  description?: string;
  items: ChecklistItem[];
  created_at: string;
  updated_at: string;
}

interface ChecklistState {
  templates: ChecklistTemplate[];
  currentTemplate: ChecklistTemplate | null;
  items: ChecklistItem[];
  loading: boolean;
  error: string | null;
}

const initialState: ChecklistState = {
  templates: [],
  currentTemplate: null,
  items: [],
  loading: false,
  error: null,
};

export const fetchTemplates = createAsyncThunk(
  'checklist/fetchTemplates',
  async () => {
    const response = await checklistService.getTemplates();
    return response;
  }
);

export const fetchTemplateById = createAsyncThunk(
  'checklist/fetchTemplateById',
  async (id: number) => {
    const response = await checklistService.getTemplateById(id);
    return response;
  }
);

export const createTemplate = createAsyncThunk(
  'checklist/createTemplate',
  async (data: Omit<ChecklistTemplate, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await checklistService.createTemplate(data);
    return response;
  }
);

export const updateTemplate = createAsyncThunk(
  'checklist/updateTemplate',
  async ({ id, data }: { id: number; data: Partial<ChecklistTemplate> }) => {
    const response = await checklistService.updateTemplate(id, data);
    return response;
  }
);

export const deleteTemplate = createAsyncThunk(
  'checklist/deleteTemplate',
  async (id: number) => {
    await checklistService.deleteTemplate(id);
    return id;
  }
);

export const toggleItemComplete = createAsyncThunk(
  'checklist/toggleItem',
  async ({ itemId, completed }: { itemId: number; completed: boolean }) => {
    const response = await checklistService.updateItem(itemId, { completed });
    return response;
  }
);

const checklistSlice = createSlice({
  name: 'checklist',
  initialState,
  reducers: {
    clearCurrentTemplate: (state) => {
      state.currentTemplate = null;
      state.items = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch templates
      .addCase(fetchTemplates.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTemplates.fulfilled, (state, action) => {
        state.loading = false;
        state.templates = action.payload;
      })
      .addCase(fetchTemplates.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch templates';
        toast.error(state.error);
      })
      // Fetch template by ID
      .addCase(fetchTemplateById.fulfilled, (state, action) => {
        state.currentTemplate = action.payload;
        state.items = action.payload.items;
      })
      // Create template
      .addCase(createTemplate.fulfilled, (state, action) => {
        state.templates.push(action.payload);
        toast.success('Template created successfully');
      })
      // Update template
      .addCase(updateTemplate.fulfilled, (state, action) => {
        const index = state.templates.findIndex(t => t.id === action.payload.id);
        if (index !== -1) {
          state.templates[index] = action.payload;
        }
        if (state.currentTemplate?.id === action.payload.id) {
          state.currentTemplate = action.payload;
        }
        toast.success('Template updated successfully');
      })
      // Delete template
      .addCase(deleteTemplate.fulfilled, (state, action) => {
        state.templates = state.templates.filter(t => t.id !== action.payload);
        toast.success('Template deleted successfully');
      })
      // Toggle item complete
      .addCase(toggleItemComplete.fulfilled, (state, action) => {
        const index = state.items.findIndex(i => i.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      });
  },
});

export const { clearCurrentTemplate } = checklistSlice.actions;
export default checklistSlice.reducer;