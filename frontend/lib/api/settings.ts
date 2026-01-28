/**
 * Settings API functions.
 *
 * Provides type-safe functions for application settings:
 * - Get and update settings
 * - API key validation
 * - Configuration management
 */

import { apiClient } from './client';
import type {
  Settings,
  SettingsInput,
  ApiKeyConfig,
  ApiKeyValidation,
  SuccessResponse,
  HealthCheckResponse,
  DashboardStats,
} from './types';

// =============================================================================
// Types
// =============================================================================

/** API key test result */
interface ApiKeyTestResult {
  service: string;
  valid: boolean;
  error: string | null;
  response_time_ms: number;
  quota_info?: {
    used: number;
    limit: number;
    remaining: number;
    reset_at: string | null;
  };
}

/** System information */
interface SystemInfo {
  version: string;
  environment: 'development' | 'staging' | 'production';
  python_version: string;
  database_type: string;
  uptime_seconds: number;
  memory_usage_mb: number;
}

// =============================================================================
// Settings Operations
// =============================================================================

/**
 * Get current application settings.
 *
 * @returns Current settings (API keys are masked)
 *
 * @example
 * ```ts
 * const settings = await getSettings();
 * console.log(settings.api_keys.openai_configured);
 * ```
 */
export async function getSettings(): Promise<Settings> {
  return apiClient.get<Settings>('/settings');
}

/**
 * Update application settings.
 *
 * @param data - Settings to update
 * @returns Updated settings
 *
 * @example
 * ```ts
 * const settings = await updateSettings({
 *   default_scrape_config: { max_results: 30 },
 *   ui: { theme: 'dark' },
 * });
 * ```
 */
export async function updateSettings(data: SettingsInput): Promise<Settings> {
  return apiClient.patch<Settings>('/settings', data);
}

/**
 * Reset settings to defaults.
 *
 * @returns Default settings
 */
export async function resetSettings(): Promise<Settings> {
  return apiClient.post<Settings>('/settings/reset');
}

// =============================================================================
// API Key Operations
// =============================================================================

/**
 * Update API keys.
 *
 * @param keys - API key configuration
 * @returns Updated settings
 *
 * @example
 * ```ts
 * await updateApiKeys({
 *   openai_api_key: 'sk-...',
 *   hunter_api_key: '...',
 * });
 * ```
 */
export async function updateApiKeys(keys: ApiKeyConfig): Promise<Settings> {
  return apiClient.patch<Settings>('/settings/api-keys', { api_keys: keys });
}

/**
 * Validate all configured API keys.
 *
 * @returns Validation results for each service
 *
 * @example
 * ```ts
 * const validations = await validateApiKeys();
 * validations.forEach(v => {
 *   if (!v.valid) {
 *     console.error(`${v.service} API key invalid: ${v.error}`);
 *   }
 * });
 * ```
 */
export async function validateApiKeys(): Promise<ApiKeyValidation[]> {
  return apiClient.get<ApiKeyValidation[]>('/settings/api-keys/validate');
}

/**
 * Test a specific API key.
 *
 * @param service - Service name (google_places, openai, hunter, google_sheets)
 * @param apiKey - API key to test
 * @returns Test result
 *
 * @example
 * ```ts
 * const result = await testApiKey('openai', 'sk-...');
 * if (result.valid) {
 *   console.log('API key is valid!');
 * }
 * ```
 */
export async function testApiKey(
  service: 'google_places' | 'openai' | 'hunter' | 'google_sheets',
  apiKey: string
): Promise<ApiKeyTestResult> {
  return apiClient.post<ApiKeyTestResult>('/settings/api-keys/test', {
    service,
    api_key: apiKey,
  });
}

/**
 * Remove an API key.
 *
 * @param service - Service to remove API key for
 * @returns Updated settings
 */
export async function removeApiKey(
  service: 'google_places' | 'openai' | 'hunter' | 'google_sheets'
): Promise<Settings> {
  return apiClient.delete<Settings>(`/settings/api-keys/${service}`);
}

// =============================================================================
// Health & Status
// =============================================================================

/**
 * Get system health check.
 *
 * @returns Health status of all services
 *
 * @example
 * ```ts
 * const health = await getHealthCheck();
 * if (health.status !== 'healthy') {
 *   console.warn('System degraded:', health);
 * }
 * ```
 */
export async function getHealthCheck(): Promise<HealthCheckResponse> {
  return apiClient.get<HealthCheckResponse>('/health');
}

/**
 * Get system information.
 *
 * @returns System info
 */
export async function getSystemInfo(): Promise<SystemInfo> {
  return apiClient.get<SystemInfo>('/system/info');
}

/**
 * Get dashboard statistics.
 *
 * @returns Dashboard stats including lead counts, activity, etc.
 *
 * @example
 * ```ts
 * const stats = await getDashboardStats();
 * console.log(`Total leads: ${stats.total_leads}`);
 * ```
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient.get<DashboardStats>('/dashboard/stats');
}

// =============================================================================
// Google Sheets Configuration
// =============================================================================

/**
 * Upload Google Sheets credentials file.
 *
 * @param file - credentials.json file
 * @returns Success response
 */
export async function uploadSheetsCredentials(file: File): Promise<SuccessResponse> {
  return apiClient.uploadFile<SuccessResponse>(
    '/settings/google-sheets/credentials',
    file,
    'credentials'
  );
}

/**
 * Get Google Sheets authorization URL.
 *
 * @returns Authorization URL for OAuth flow
 */
export async function getSheetsAuthUrl(): Promise<{ url: string }> {
  return apiClient.get<{ url: string }>('/settings/google-sheets/auth-url');
}

/**
 * Complete Google Sheets OAuth flow.
 *
 * @param code - OAuth authorization code
 * @returns Success response
 */
export async function completeSheetsAuth(code: string): Promise<SuccessResponse> {
  return apiClient.post<SuccessResponse>('/settings/google-sheets/auth-callback', { code });
}

/**
 * List available Google Spreadsheets.
 *
 * @returns List of spreadsheets the user has access to
 */
export async function listSpreadsheets(): Promise<
  Array<{
    id: string;
    name: string;
    created_at: string;
    modified_at: string;
  }>
> {
  return apiClient.get('/settings/google-sheets/spreadsheets');
}

// =============================================================================
// Export Configuration
// =============================================================================

/**
 * Get default export fields.
 *
 * @returns List of available export fields
 */
export async function getExportFields(): Promise<
  Array<{
    name: string;
    label: string;
    type: string;
    default_included: boolean;
  }>
> {
  return apiClient.get('/settings/export/fields');
}

/**
 * Update default export configuration.
 *
 * @param config - Export configuration
 * @returns Updated settings
 */
export async function updateExportConfig(
  config: SettingsInput['default_export_config']
): Promise<Settings> {
  return updateSettings({ default_export_config: config });
}

// =============================================================================
// GDPR Configuration
// =============================================================================

/**
 * Get GDPR settings.
 *
 * @returns GDPR configuration
 */
export async function getGDPRSettings(): Promise<Settings['gdpr']> {
  const settings = await getSettings();
  return settings.gdpr;
}

/**
 * Update GDPR settings.
 *
 * @param config - GDPR configuration
 * @returns Updated settings
 */
export async function updateGDPRSettings(
  config: Partial<Settings['gdpr']>
): Promise<Settings> {
  return updateSettings({ gdpr: config });
}

// =============================================================================
// Rate Limit Configuration
// =============================================================================

/**
 * Get current rate limits.
 *
 * @returns Rate limit configuration for all services
 */
export async function getRateLimits(): Promise<Settings['rate_limits']> {
  const settings = await getSettings();
  return settings.rate_limits;
}

/**
 * Update rate limits.
 *
 * @param limits - Rate limit configuration
 * @returns Updated settings
 */
export async function updateRateLimits(
  limits: SettingsInput['rate_limits']
): Promise<Settings> {
  return updateSettings({ rate_limits: limits });
}

// =============================================================================
// UI Preferences
// =============================================================================

/**
 * Get UI preferences.
 *
 * @returns UI configuration
 */
export async function getUIPreferences(): Promise<Settings['ui']> {
  const settings = await getSettings();
  return settings.ui;
}

/**
 * Update UI preferences.
 *
 * @param prefs - UI preferences
 * @returns Updated settings
 */
export async function updateUIPreferences(
  prefs: Partial<Settings['ui']>
): Promise<Settings> {
  return updateSettings({ ui: prefs });
}

/**
 * Set UI theme.
 *
 * @param theme - Theme setting
 * @returns Updated settings
 */
export async function setTheme(theme: 'light' | 'dark' | 'system'): Promise<Settings> {
  return updateUIPreferences({ theme });
}

/**
 * Set UI language.
 *
 * @param language - Language code
 * @returns Updated settings
 */
export async function setLanguage(language: 'sk' | 'cs' | 'de' | 'en'): Promise<Settings> {
  return updateUIPreferences({ language });
}
