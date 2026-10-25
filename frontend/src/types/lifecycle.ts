export type MaturityStage =
  | 'ACTIVE'
  | 'MATURING_SOON'
  | 'CRITICAL_WINDOW'
  | 'MATURED'
  | 'EXPIRED';

export type LifecycleValidityStatus =
  | 'VALID'
  | 'PENDING_RENEWAL'
  | 'DEFAULTED'
  | 'RELEASE_APPROVED'
  | 'RELEASED';

export type NotificationChannel =
  | 'IN_APP'
  | 'EMAIL'
  | 'MOCK_SMS';

export type NotificationDeliveryStatus =
  | 'CREATED'
  | 'ATTEMPTED'
  | 'ACCEPTED'
  | 'DELIVERED'
  | 'FAILED'
  | 'MOCKED';

export interface NotificationDeliveryAttempt {
  id: string;
  attempt_number: number;
  attempted_at: string;
  status: NotificationDeliveryStatus;
  provider_name?: string | null;
  provider_reference?: string | null;
  failure_category?: string | null;
  failure_details?: string | null;
  is_mock: boolean;
}

export interface LifecycleNotification {
  id: string;
  instrument_id: string;
  event_type: string;
  milestone_days?: number | null;
  recipient_role: string;
  recipient_user_id?: string | null;
  channel: NotificationChannel;
  status: NotificationDeliveryStatus;
  template_id?: string | null;
  template_version?: string | null;
  rendered_title: string;
  rendered_message: string;
  retry_count: number;
  max_retries: number;
  last_attempted_at?: string | null;
  final_delivered_at?: string | null;
  is_mock: boolean;
  mock_disclaimer?: string | null;
  is_read: boolean;
  read_at?: string | null;
  failure_category?: string | null;
  failure_details?: string | null;
  created_at: string;
  attempts: NotificationDeliveryAttempt[];
}

export interface NotificationListResponse {
  notifications: LifecycleNotification[];
  total_count: number;
}

export interface LifecycleEvaluation {
  id: string;
  instrument_id: string;
  evaluation_date: string;
  days_to_maturity: number;
  maturity_stage: MaturityStage;
  validity_status: LifecycleValidityStatus;
  institution_action_due_date?: string | null;
  officer_action_due_date?: string | null;
  is_overdue: boolean;
  is_escalated: boolean;
  overdue_days: number;
  requires_immediate_action: boolean;
  applied_policy_version: number;
  created_at: string;
}
