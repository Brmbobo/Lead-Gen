/**
 * Leads API functions.
 *
 * Provides type-safe functions for all lead-related API operations:
 * - List, get, update, delete leads
 * - Export leads to various formats
 * - Bulk operations
 */

import { apiClient } from './client';
import type {
  Lead,
  EnrichedLead,
  LeadInput,
  LeadListParams,
  LeadExportParams,
  PaginatedResponse,
  SuccessResponse,
  LeadStatus,
} from './types';

// =============================================================================
// Types
// =============================================================================

/** Response when exporting to Google Sheets */
interface SheetsExportResponse {
  success: boolean;
  spreadsheet_url: string;
  rows_exported: number;
}

/** Response when exporting to file */
interface FileExportResponse {
  success: boolean;
  download_url: string;
  filename: string;
  rows_exported: number;
}

/** Lead statistics */
interface LeadStats {
  total: number;
  by_status: Record<LeadStatus, number>;
  by_source: Record<string, number>;
  avg_quality_score: number;
  with_email: number;
  with_phone: number;
}

/** Bulk operation result */
interface BulkOperationResult {
  success: boolean;
  processed: number;
  failed: number;
  errors: Array<{ id: string; error: string }>;
}

// =============================================================================
// Lead CRUD Operations
// =============================================================================

/**
 * Get paginated list of leads.
 *
 * @param params - Filtering and pagination parameters
 * @returns Paginated list of leads
 *
 * @example
 * ```ts
 * const { items, total } = await getLeads({ page: 1, status: 'new' });
 * ```
 */
export async function getLeads(
  params: LeadListParams = {}
): Promise<PaginatedResponse<Lead>> {
  const queryParams: Record<string, string | number | undefined | string[]> = {
    page: params.page,
    page_size: params.page_size,
    status: params.status,
    source: params.source,
    business_type: params.business_type,
    city: params.city,
    min_quality_score: params.min_quality_score,
    search: params.search,
    sort_by: params.sort_by,
    sort_order: params.sort_order,
    tags: params.tags,
  };

  return apiClient.get<PaginatedResponse<Lead>>('/leads', queryParams);
}

/**
 * Get a single lead by ID.
 *
 * @param id - Lead ID
 * @returns Lead details
 *
 * @example
 * ```ts
 * const lead = await getLead('abc123');
 * ```
 */
export async function getLead(id: string): Promise<Lead> {
  return apiClient.get<Lead>(`/leads/${id}`);
}

/**
 * Get enriched lead with email data.
 *
 * @param id - Lead ID
 * @returns Enriched lead details
 */
export async function getEnrichedLead(id: string): Promise<EnrichedLead> {
  return apiClient.get<EnrichedLead>(`/leads/${id}/enriched`);
}

/**
 * Create a new lead.
 *
 * @param data - Lead data
 * @returns Created lead
 *
 * @example
 * ```ts
 * const lead = await createLead({
 *   name: 'Zubar Bratislava',
 *   phone: '+421900123456',
 *   business_type: 'dentist',
 * });
 * ```
 */
export async function createLead(data: LeadInput): Promise<Lead> {
  return apiClient.post<Lead>('/leads', data);
}

/**
 * Update an existing lead.
 *
 * @param id - Lead ID
 * @param data - Updated lead data
 * @returns Updated lead
 *
 * @example
 * ```ts
 * const lead = await updateLead('abc123', { status: 'contacted' });
 * ```
 */
export async function updateLead(id: string, data: Partial<LeadInput>): Promise<Lead> {
  return apiClient.patch<Lead>(`/leads/${id}`, data);
}

/**
 * Delete a lead.
 *
 * @param id - Lead ID
 * @returns Success response
 *
 * @example
 * ```ts
 * await deleteLead('abc123');
 * ```
 */
export async function deleteLead(id: string): Promise<SuccessResponse> {
  return apiClient.delete<SuccessResponse>(`/leads/${id}`);
}

// =============================================================================
// Lead Status Operations
// =============================================================================

/**
 * Update lead status.
 *
 * @param id - Lead ID
 * @param status - New status
 * @returns Updated lead
 */
export async function updateLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
  return apiClient.patch<Lead>(`/leads/${id}/status`, { status });
}

/**
 * Bulk update lead statuses.
 *
 * @param ids - Array of lead IDs
 * @param status - New status for all leads
 * @returns Bulk operation result
 */
export async function bulkUpdateStatus(
  ids: string[],
  status: LeadStatus
): Promise<BulkOperationResult> {
  return apiClient.post<BulkOperationResult>('/leads/bulk/status', { ids, status });
}

// =============================================================================
// Lead Export Operations
// =============================================================================

/**
 * Export leads to specified format.
 *
 * @param params - Export parameters
 * @returns Export result (URL or success info)
 *
 * @example
 * ```ts
 * // Export to CSV
 * const result = await exportLeads({ format: 'csv', status: ['new', 'enriched'] });
 *
 * // Export to Google Sheets
 * const result = await exportLeads({
 *   format: 'sheets',
 *   spreadsheet_id: 'abc123',
 *   worksheet_name: 'Leads',
 * });
 * ```
 */
export async function exportLeads(
  params: LeadExportParams
): Promise<SheetsExportResponse | FileExportResponse> {
  return apiClient.post<SheetsExportResponse | FileExportResponse>('/leads/export', params);
}

/**
 * Export leads to CSV file.
 *
 * @param params - Optional filter parameters
 * @returns Download URL for CSV file
 */
export async function exportToCSV(
  params: Omit<LeadExportParams, 'format'> = {}
): Promise<FileExportResponse> {
  return exportLeads({ ...params, format: 'csv' }) as Promise<FileExportResponse>;
}

/**
 * Export leads to JSON file.
 *
 * @param params - Optional filter parameters
 * @returns Download URL for JSON file
 */
export async function exportToJSON(
  params: Omit<LeadExportParams, 'format'> = {}
): Promise<FileExportResponse> {
  return exportLeads({ ...params, format: 'json' }) as Promise<FileExportResponse>;
}

/**
 * Export leads to Google Sheets.
 *
 * @param spreadsheetId - Target spreadsheet ID
 * @param worksheetName - Target worksheet name
 * @param params - Optional filter parameters
 * @returns Spreadsheet URL
 */
export async function exportToSheets(
  spreadsheetId: string,
  worksheetName: string = 'Leads',
  params: Omit<LeadExportParams, 'format' | 'spreadsheet_id' | 'worksheet_name'> = {}
): Promise<SheetsExportResponse> {
  return exportLeads({
    ...params,
    format: 'sheets',
    spreadsheet_id: spreadsheetId,
    worksheet_name: worksheetName,
  }) as Promise<SheetsExportResponse>;
}

// =============================================================================
// Lead Statistics
// =============================================================================

/**
 * Get lead statistics.
 *
 * @returns Lead statistics summary
 */
export async function getLeadStats(): Promise<LeadStats> {
  return apiClient.get<LeadStats>('/leads/stats');
}

// =============================================================================
// Lead Enrichment
// =============================================================================

/**
 * Enrich a single lead with email data.
 *
 * @param id - Lead ID
 * @returns Enriched lead
 */
export async function enrichLead(id: string): Promise<EnrichedLead> {
  return apiClient.post<EnrichedLead>(`/leads/${id}/enrich`);
}

/**
 * Bulk enrich multiple leads.
 *
 * @param ids - Array of lead IDs to enrich
 * @returns Bulk operation result
 */
export async function bulkEnrichLeads(ids: string[]): Promise<BulkOperationResult> {
  return apiClient.post<BulkOperationResult>('/leads/bulk/enrich', { ids });
}

// =============================================================================
// Lead Tags
// =============================================================================

/**
 * Add tags to a lead.
 *
 * @param id - Lead ID
 * @param tags - Tags to add
 * @returns Updated lead
 */
export async function addLeadTags(id: string, tags: string[]): Promise<Lead> {
  return apiClient.post<Lead>(`/leads/${id}/tags`, { tags });
}

/**
 * Remove tags from a lead.
 *
 * @param id - Lead ID
 * @param tags - Tags to remove
 * @returns Updated lead
 */
export async function removeLeadTags(id: string, tags: string[]): Promise<Lead> {
  return apiClient.delete<Lead>(`/leads/${id}/tags`, {
    body: JSON.stringify({ tags }),
  });
}

// =============================================================================
// Bulk Operations
// =============================================================================

/**
 * Bulk delete leads.
 *
 * @param ids - Array of lead IDs to delete
 * @returns Bulk operation result
 */
export async function bulkDeleteLeads(ids: string[]): Promise<BulkOperationResult> {
  return apiClient.post<BulkOperationResult>('/leads/bulk/delete', { ids });
}

/**
 * Bulk add tags to leads.
 *
 * @param ids - Array of lead IDs
 * @param tags - Tags to add
 * @returns Bulk operation result
 */
export async function bulkAddTags(
  ids: string[],
  tags: string[]
): Promise<BulkOperationResult> {
  return apiClient.post<BulkOperationResult>('/leads/bulk/tags', { ids, tags, action: 'add' });
}

// =============================================================================
// GDPR Operations
// =============================================================================

/**
 * Export lead data for GDPR data subject access request.
 *
 * @param id - Lead ID
 * @returns GDPR export data
 */
export async function exportLeadGDPR(id: string): Promise<Record<string, unknown>> {
  return apiClient.get<Record<string, unknown>>(`/leads/${id}/gdpr-export`);
}

/**
 * Delete lead data for GDPR right to erasure.
 *
 * @param id - Lead ID
 * @returns Success response
 */
export async function deleteLeadGDPR(id: string): Promise<SuccessResponse> {
  return apiClient.delete<SuccessResponse>(`/leads/${id}/gdpr-delete`);
}

/**
 * Pseudonymize lead data for GDPR compliance.
 *
 * @param id - Lead ID
 * @returns Updated lead with pseudonymized data
 */
export async function pseudonymizeLead(id: string): Promise<Lead> {
  return apiClient.post<Lead>(`/leads/${id}/pseudonymize`);
}
