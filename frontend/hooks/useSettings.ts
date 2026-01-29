/**
 * useSettings - React Query hooks for settings data fetching.
 *
 * Provides type-safe hooks for:
 * - Fetching application settings
 * - Updating settings
 * - API key validation
 * - Health checks
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query';

import {
  getSettings,
  updateSettings,
  resetSettings,
  validateApiKeys,
  testApiKey,
  updateApiKeys,
  getHealthCheck,
  getSystemInfo,
} from '@/lib/api';

import type {
  Settings,
  SettingsInput,
  ApiKeyConfig,
  ApiKeyValidation,
  HealthCheckResponse,
} from '@/lib/api/types';

// =============================================================================
// Query Keys
// =============================================================================

/** Query key factory for settings */
export const settingsKeys = {
  all: ['settings'] as const,
  detail: () => [...settingsKeys.all, 'detail'] as const,
  apiKeys: () => [...settingsKeys.all, 'api-keys'] as const,
  apiKeyValidation: () => [...settingsKeys.apiKeys(), 'validation'] as const,
  health: () => ['health'] as const,
  systemInfo: () => ['system-info'] as const,
};

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

/** API key service types */
type ApiKeyService = 'google_places' | 'openai' | 'hunter' | 'google_sheets';

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Hook for fetching application settings.
 *
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: settings, isLoading } = useSettings();
 *
 * if (settings?.api_keys.openai_configured) {
 *   console.log('OpenAI is configured');
 * }
 * ```
 */
export function useSettings(
  options?: Omit<UseQueryOptions<Settings, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: settingsKeys.detail(),
    queryFn: getSettings,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    ...options,
  });
}

/**
 * Hook for validating all API keys.
 *
 * @param enabled - Whether to run the validation
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: validations, refetch } = useValidateApiKeys(false);
 *
 * // Trigger validation
 * const handleValidate = () => refetch();
 * ```
 */
export function useValidateApiKeys(
  enabled: boolean = false,
  options?: Omit<
    UseQueryOptions<ApiKeyValidation[], Error>,
    'queryKey' | 'queryFn' | 'enabled'
  >
) {
  return useQuery({
    queryKey: settingsKeys.apiKeyValidation(),
    queryFn: validateApiKeys,
    enabled,
    staleTime: 0, // Always fetch fresh
    gcTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * Hook for fetching system health.
 *
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: health } = useHealthCheck();
 *
 * if (health?.status !== 'healthy') {
 *   console.warn('System is not healthy');
 * }
 * ```
 */
export function useHealthCheck(
  options?: Omit<
    UseQueryOptions<HealthCheckResponse, Error>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: settingsKeys.health(),
    queryFn: getHealthCheck,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Refetch every minute
    ...options,
  });
}

/**
 * Hook for fetching system information.
 *
 * @param options - Additional React Query options
 *
 * @example
 * ```tsx
 * const { data: systemInfo } = useSystemInfo();
 *
 * console.log(`Version: ${systemInfo?.version}`);
 * ```
 */
export function useSystemInfo(
  options?: Omit<UseQueryOptions<SystemInfo, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: settingsKeys.systemInfo(),
    queryFn: getSystemInfo,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    ...options,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Hook for updating settings.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: update } = useUpdateSettings();
 *
 * update({
 *   ui: { theme: 'dark' },
 *   default_scrape_config: { max_results: 50 },
 * });
 * ```
 */
export function useUpdateSettings(
  options?: UseMutationOptions<Settings, Error, SettingsInput>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateSettings,
    onSuccess: (updatedSettings) => {
      queryClient.setQueryData(settingsKeys.detail(), updatedSettings);
    },
    ...options,
  });
}

/**
 * Hook for resetting settings to defaults.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: reset } = useResetSettings();
 *
 * reset();
 * ```
 */
export function useResetSettings(
  options?: UseMutationOptions<Settings, Error, void>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resetSettings,
    onSuccess: (defaultSettings) => {
      queryClient.setQueryData(settingsKeys.detail(), defaultSettings);
    },
    ...options,
  });
}

/**
 * Hook for updating API keys.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: saveApiKeys } = useUpdateApiKeys();
 *
 * saveApiKeys({
 *   openai_api_key: 'sk-...',
 * });
 * ```
 */
export function useUpdateApiKeys(
  options?: UseMutationOptions<Settings, Error, ApiKeyConfig>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateApiKeys,
    onSuccess: (updatedSettings) => {
      queryClient.setQueryData(settingsKeys.detail(), updatedSettings);
      // Invalidate API key validation
      queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeyValidation() });
    },
    ...options,
  });
}

/**
 * Hook for testing a specific API key.
 *
 * @param options - Additional mutation options
 *
 * @example
 * ```tsx
 * const { mutate: testKey, isPending } = useTestApiKey();
 *
 * testKey({
 *   service: 'openai',
 *   apiKey: 'sk-...',
 * });
 * ```
 */
export function useTestApiKey(
  options?: UseMutationOptions<
    ApiKeyTestResult,
    Error,
    { service: ApiKeyService; apiKey: string }
  >
) {
  return useMutation({
    mutationFn: ({ service, apiKey }) => testApiKey(service, apiKey),
    ...options,
  });
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch settings data.
 *
 * @param queryClient - Query client instance
 */
export async function prefetchSettings(
  queryClient: ReturnType<typeof useQueryClient>
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: settingsKeys.detail(),
    queryFn: getSettings,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Prefetch health check data.
 *
 * @param queryClient - Query client instance
 */
export async function prefetchHealthCheck(
  queryClient: ReturnType<typeof useQueryClient>
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: settingsKeys.health(),
    queryFn: getHealthCheck,
    staleTime: 30 * 1000,
  });
}
