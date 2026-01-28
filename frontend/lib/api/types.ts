/**
 * TypeScript type definitions for the Lead-Gen API.
 *
 * These types mirror the Python Pydantic models from the backend
 * to ensure type safety across the full stack.
 */

// =============================================================================
// Enums
// =============================================================================

/** Source of lead data */
export type LeadSource =
  | 'google_places'
  | 'yelp'
  | 'manual'
  | 'import'
  | 'referral';

/** Lead processing status */
export type LeadStatus =
  | 'new'
  | 'enriched'
  | 'contacted'
  | 'responded'
  | 'converted'
  | 'rejected'
  | 'archived';

/** Workflow execution status */
export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

/** Types of workflow steps */
export type StepType =
  | 'scrape'
  | 'enrich'
  | 'generate'
  | 'export'
  | 'filter'
  | 'transform'
  | 'notify'
  | 'wait';

/** Supported message languages */
export type MessageLanguage = 'sk' | 'cs' | 'de' | 'en';

/** Message tone/style */
export type MessageTone =
  | 'professional'
  | 'friendly'
  | 'casual'
  | 'formal'
  | 'enthusiastic';

/** Type of outreach message */
export type MessageType =
  | 'cold_email'
  | 'follow_up'
  | 'introduction'
  | 'partnership'
  | 'feedback_request';

/** Export destination type */
export type ExportDestination = 'sheets' | 'csv' | 'json' | 'database';

/** Enrichment provider */
export type EnrichmentProvider = 'hunter' | 'clearbit' | 'manual';

// =============================================================================
// Location & Metrics
// =============================================================================

/** Geographic location data */
export interface Location {
  latitude: number;
  longitude: number;
  formatted_address: string;
  street: string;
  city: string;
  region: string;
  postal_code: string;
  country: string;
  country_code: string;
}

/** Business opening hours */
export interface OpeningHours {
  monday: string;
  tuesday: string;
  wednesday: string;
  thursday: string;
  friday: string;
  saturday: string;
  sunday: string;
  timezone: string;
}

/** Business metrics and ratings */
export interface BusinessMetrics {
  rating: number | null;
  review_count: number;
  price_level: number | null;
  user_ratings_total: number;
  rating_quality: 'unknown' | 'excellent' | 'good' | 'average' | 'poor';
}

// =============================================================================
// GDPR Compliance
// =============================================================================

/** GDPR consent record */
export interface GDPRConsent {
  given: boolean;
  timestamp: string | null;
  source: string | null;
  version: string | null;
  ip_address: string | null;
  withdrawable: boolean;
}

// =============================================================================
// Lead Models
// =============================================================================

/** Email enrichment data from Hunter.io or similar */
export interface EmailEnrichment {
  email: string;
  confidence: number;
  type: 'generic' | 'personal' | 'role-based';
  first_name: string;
  last_name: string;
  position: string;
  department: string;
  linkedin_url: string | null;
  twitter_handle: string;
  phone_number: string;
  verified: boolean;
  verified_at: string | null;
  sources: string[];
}

/** Base Lead model */
export interface Lead {
  // Identity
  id: string;
  place_id: string;

  // Core business info
  name: string;
  phone: string;
  website: string | null;
  email: string | null;

  // Location
  location: Location | null;

  // Business details
  business_type: string;
  categories: string[];
  metrics: BusinessMetrics;
  opening_hours: OpeningHours | null;

  // Source metadata
  source: LeadSource;
  source_url: string | null;
  scraped_at: string;

  // Processing status
  status: LeadStatus;
  status_updated_at: string;

  // GDPR Compliance
  gdpr_consent: GDPRConsent;
  gdpr_legal_basis: string;
  gdpr_retention_until: string | null;
  gdpr_pseudonymized_id: string;

  // Processing metadata
  correlation_id: string | null;
  tags: string[];
  notes: string;

  // Computed fields
  display_name: string;
  has_contact_info: boolean;
  quality_score: number;
}

/** Lead with email enrichment data */
export interface EnrichedLead extends Lead {
  // Enrichment data
  enrichments: EmailEnrichment[];
  enriched_at: string | null;
  enrichment_source: string;

  // Additional contacts found
  additional_emails: string[];
  additional_phones: string[];

  // Company data (from enrichment)
  company_size: string;
  company_industry: string;
  company_founded: number | null;
  company_linkedin: string | null;

  // Computed fields
  best_email: string | null;
  contact_person: string | null;
  enrichment_quality: 'none' | 'high' | 'medium' | 'low';
}

/** Input for creating/updating a lead */
export interface LeadInput {
  name: string;
  phone?: string;
  email?: string;
  website?: string;
  business_type?: string;
  location?: Partial<Location>;
  tags?: string[];
  notes?: string;
  status?: LeadStatus;
}

/** Parameters for listing leads */
export interface LeadListParams {
  page?: number;
  page_size?: number;
  status?: LeadStatus;
  source?: LeadSource;
  business_type?: string;
  city?: string;
  min_quality_score?: number;
  search?: string;
  sort_by?: 'name' | 'scraped_at' | 'quality_score' | 'status';
  sort_order?: 'asc' | 'desc';
  tags?: string[];
}

/** Parameters for exporting leads */
export interface LeadExportParams {
  format: 'csv' | 'json' | 'sheets';
  status?: LeadStatus[];
  min_quality_score?: number;
  include_messages?: boolean;
  spreadsheet_id?: string;
  worksheet_name?: string;
}

// =============================================================================
// Workflow Models
// =============================================================================

/** Retry configuration for workflow steps */
export interface RetryPolicy {
  max_retries: number;
  base_delay_seconds: number;
  max_delay_seconds: number;
  exponential_base: number;
}

/** Rate limiting configuration */
export interface RateLimitPolicy {
  requests_per_minute: number;
  burst_size: number | null;
}

/** Configuration for scraping step */
export interface ScrapeConfig {
  query: string;
  location: string;
  radius_km: number;
  max_results: number;
  language: string;
  region: string;
  business_types: string[];
  min_rating: number | null;
  min_reviews: number | null;
  open_now: boolean;
}

/** Configuration for enrichment step */
export interface EnrichConfig {
  provider: EnrichmentProvider;
  find_emails: boolean;
  verify_emails: boolean;
  find_social: boolean;
  max_enrichments_per_lead: number;
}

/** Configuration for message generation step */
export interface GenerateConfig {
  template_id: string;
  model: string;
  temperature: number;
  max_tokens: number;
  language: string;
  tone: string;
  use_business_name: boolean;
  use_location: boolean;
  use_rating: boolean;
  generate_subject: boolean;
  generate_body: boolean;
  include_signature: boolean;
  sender_name: string;
  sender_company: string;
  sender_position: string;
  sender_email: string;
  sender_phone: string;
  value_proposition: string;
  call_to_action: string;
}

/** Configuration for export step */
export interface ExportConfig {
  destination: ExportDestination;
  spreadsheet_id: string;
  worksheet_name: string;
  append_mode: boolean;
  output_path: string;
  include_messages: boolean;
  fields: string[];
}

/** Configuration for filter step */
export interface FilterConfig {
  min_quality_score: number | null;
  required_fields: string[];
  include_statuses: string[];
  include_categories: string[];
  exclude_statuses: string[];
  exclude_domains: string[];
  deduplicate_by: string;
}

/** Single step in a workflow */
export interface WorkflowStep {
  id: string;
  name: string;
  type: StepType;

  // Configuration (one of these based on type)
  scrape_config: ScrapeConfig | null;
  enrich_config: EnrichConfig | null;
  generate_config: GenerateConfig | null;
  export_config: ExportConfig | null;
  filter_config: FilterConfig | null;

  // Execution settings
  enabled: boolean;
  retry_policy: RetryPolicy;
  timeout_seconds: number;
  run_if: string;
  skip_on_error: boolean;

  // Runtime state
  status: WorkflowStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string;
  output_count: number;
}

/** Complete workflow configuration */
export interface Workflow {
  // Identity
  id: string;
  name: string;
  description: string;
  version: string;

  // Steps
  steps: WorkflowStep[];

  // Global settings
  rate_limits: Record<string, RateLimitPolicy>;
  default_retry_policy: RetryPolicy;

  // Execution settings
  parallel_steps: boolean;
  stop_on_error: boolean;
  max_leads: number | null;
  dry_run: boolean;

  // Scheduling
  schedule_cron: string;
  enabled: boolean;

  // Metadata
  created_at: string;
  updated_at: string;
  created_by: string;
  tags: string[];

  // Runtime state
  status: WorkflowStatus;
  current_step_index: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string;
  total_leads_processed: number;

  // Computed fields
  total_steps: number;
  completed_steps: number;
  progress_percent: number;
}

/** Input for creating a workflow */
export interface WorkflowInput {
  name: string;
  description?: string;
  steps: Partial<WorkflowStep>[];
  tags?: string[];
  max_leads?: number;
  schedule_cron?: string;
}

/** Configuration for running a workflow */
export interface WorkflowRunConfig {
  dry_run?: boolean;
  max_leads?: number;
  skip_steps?: string[];
  override_config?: Record<string, unknown>;
}

/** Workflow execution result */
export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: WorkflowStatus;
  started_at: string;
  completed_at: string | null;
  current_step: string | null;
  leads_processed: number;
  error_message: string | null;
  step_results: WorkflowStepResult[];
}

/** Result of a single workflow step */
export interface WorkflowStepResult {
  step_id: string;
  step_name: string;
  status: WorkflowStatus;
  started_at: string;
  completed_at: string | null;
  input_count: number;
  output_count: number;
  error_message: string | null;
  duration_seconds: number | null;
}

// =============================================================================
// Outreach Message Models
// =============================================================================

/** Context for message personalization */
export interface PersonalizationContext {
  business_name: string;
  business_type: string;
  city: string;
  region: string;
  country: string;
  contact_name: string;
  contact_position: string;
  rating: number | null;
  review_count: number;
  custom_vars: Record<string, string>;
  sender_name: string;
  sender_company: string;
  sender_position: string;
  sender_email: string;
  sender_phone: string;
  campaign_name: string;
  value_proposition: string;
}

/** Message template with variables */
export interface MessageTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  signature: string;
  language: MessageLanguage;
  tone: MessageTone;
  message_type: MessageType;
  required_variables: string[];
  optional_variables: string[];
  variant_name: string;
  is_control: boolean;
  times_used: number;
  open_rate: number | null;
  reply_rate: number | null;
}

/** Generated outreach message */
export interface OutreachMessage {
  id: string;
  subject: string;
  body: string;
  html_body: string | null;
  language: MessageLanguage;
  tone: MessageTone;
  message_type: MessageType;
  template_id: string | null;
  lead_id: string;
  generated_at: string;
  generation_model: string;
  generation_tokens: number;
  generation_cost_usd: number;
  personalization_context: PersonalizationContext | null;
  personalization_score: number;
  readability_score: number | null;
  sentiment_score: number | null;
  spam_score: number | null;
  sent_at: string | null;
  sent_to: string;
  opened_at: string | null;
  clicked_at: string | null;
  replied_at: string | null;
  bounced: boolean;
  unsubscribed: boolean;
  correlation_id: string | null;
  campaign_id: string;
  sequence_number: number;

  // Computed fields
  word_count: number;
  character_count: number;
  is_sent: boolean;
  is_opened: boolean;
  is_replied: boolean;
  engagement_score: number;
}

// =============================================================================
// Settings Models
// =============================================================================

/** API key configuration for external services */
export interface ApiKeyConfig {
  google_places_api_key?: string;
  openai_api_key?: string;
  hunter_api_key?: string;
  google_sheets_credentials?: Record<string, unknown>;
}

/** Application settings */
export interface Settings {
  // API Keys (masked in response)
  api_keys: {
    google_places_configured: boolean;
    openai_configured: boolean;
    hunter_configured: boolean;
    google_sheets_configured: boolean;
  };

  // Default scraping settings
  default_scrape_config: Partial<ScrapeConfig>;

  // Default enrichment settings
  default_enrich_config: Partial<EnrichConfig>;

  // Default message generation settings
  default_generate_config: Partial<GenerateConfig>;

  // Default export settings
  default_export_config: Partial<ExportConfig>;

  // Rate limits
  rate_limits: Record<string, RateLimitPolicy>;

  // GDPR settings
  gdpr: {
    default_retention_days: number;
    default_legal_basis: string;
    auto_pseudonymize: boolean;
  };

  // UI preferences
  ui: {
    theme: 'light' | 'dark' | 'system';
    language: MessageLanguage;
    items_per_page: number;
  };
}

/** Input for updating settings */
export interface SettingsInput {
  api_keys?: ApiKeyConfig;
  default_scrape_config?: Partial<ScrapeConfig>;
  default_enrich_config?: Partial<EnrichConfig>;
  default_generate_config?: Partial<GenerateConfig>;
  default_export_config?: Partial<ExportConfig>;
  rate_limits?: Record<string, Partial<RateLimitPolicy>>;
  gdpr?: Partial<Settings['gdpr']>;
  ui?: Partial<Settings['ui']>;
}

/** API key validation result */
export interface ApiKeyValidation {
  service: string;
  valid: boolean;
  error: string | null;
  remaining_quota: number | null;
}

// =============================================================================
// API Response Types
// =============================================================================

/** Paginated API response */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

/** API error response */
export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  correlation_id?: string;
  timestamp: string;
}

/** Generic success response */
export interface SuccessResponse<T = void> {
  success: boolean;
  data?: T;
  message?: string;
}

/** Health check response */
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
  services: {
    database: boolean;
    google_places: boolean;
    openai: boolean;
    hunter: boolean;
    google_sheets: boolean;
  };
}

/** Dashboard statistics */
export interface DashboardStats {
  total_leads: number;
  leads_this_week: number;
  leads_change_percent: number;
  emails_found: number;
  email_enrichment_rate: number;
  messages_sent: number;
  message_response_rate: number;
  api_cost_this_month: number;
  active_workflows: number;
  recent_activities: Activity[];
}

/** Activity log entry */
export interface Activity {
  id: string;
  type: 'scrape' | 'enrich' | 'generate' | 'export' | 'error' | 'workflow';
  message: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
  metadata?: Record<string, unknown>;
}
