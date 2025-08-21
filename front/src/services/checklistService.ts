import api from './api';
import { ChecklistTemplate, ChecklistItem } from '../store/slices/checklistSlice';

export const checklistService = {
  async getTemplates(): Promise<ChecklistTemplate[]> {
    const response = await api.get('/checklist/templates/');
    return response.data;
  },

  async getTemplateById(id: number): Promise<ChecklistTemplate> {
    const response = await api.get(`/checklist/templates/${id}/`);
    return response.data;
  },

  async createTemplate(
    data: Omit<ChecklistTemplate, 'id' | 'created_at' | 'updated_at'>
  ): Promise<ChecklistTemplate> {
    const response = await api.post('/checklist/templates/', data);
    return response.data;
  },

  async updateTemplate(
    id: number,
    data: Partial<ChecklistTemplate>
  ): Promise<ChecklistTemplate> {
    const response = await api.patch(`/checklist/templates/${id}/`, data);
    return response.data;
  },

  async deleteTemplate(id: number): Promise<void> {
    await api.delete(`/checklist/templates/${id}/`);
  },

  async getItems(templateId: number): Promise<ChecklistItem[]> {
    const response = await api.get(`/checklist/templates/${templateId}/items/`);
    return response.data;
  },

  async createItem(
    templateId: number,
    data: Omit<ChecklistItem, 'id' | 'created_at' | 'updated_at'>
  ): Promise<ChecklistItem> {
    const response = await api.post(
      `/checklist/templates/${templateId}/items/`,
      data
    );
    return response.data;
  },

  async updateItem(
    itemId: number,
    data: Partial<ChecklistItem>
  ): Promise<ChecklistItem> {
    const response = await api.patch(`/checklist/items/${itemId}/`, data);
    return response.data;
  },

  async deleteItem(itemId: number): Promise<void> {
    await api.delete(`/checklist/items/${itemId}/`);
  },

  async duplicateTemplate(templateId: number): Promise<ChecklistTemplate> {
    const response = await api.post(
      `/checklist/templates/${templateId}/duplicate/`
    );
    return response.data;
  },
};