/** Shapes of the JSON the API returns. They mirror the Pydantic schemas in app/<module>/schemas.py. */

export type Role = 'attendee' | 'organizer' | 'event_admin' | 'platform_admin'
export interface User { id: string; name: string; email: string; role: Role; is_verified: boolean; is_active: boolean; locale: string; created_at: string }
export interface UserBrief { id: string; name: string; email: string }

export interface PayoutAccount { id: string; bank_name: string; account_holder: string; account_last4: string; status: string; is_simulation: boolean }
export interface OrganizerProfile {
  id: string; display_name: string; contact_email: string; contact_phone: string | null; description: string | null
  website: string | null; verification_status: 'not_started' | 'verified'; verified_at: string | null; payout_account: PayoutAccount | null
}
export interface Notification { id: string; type: string; title: string; body: string; link: string | null; is_read: boolean; created_at: string }

export interface Venue { id: string; name: string; description: string | null; city: string; address: string; capacity: number | null; has_seat_map: boolean }
export interface VenueLayout extends Venue {
  sections: { id: string; name: string; price_category: string; rows: { id: string; label: string; seats: { id: string; number: number; is_accessible: boolean }[] }[] }[]
}

export type EventStatus = 'draft' | 'published' | 'unpublished' | 'cancelled'
export type EventClass = 'upcoming' | 'active' | 'completed' | 'cancelled'
export interface EventCard {
  id: string; slug: string; title: string; category: string; images: string[]; timezone: string; start_at: string; end_at: string
  status: EventStatus; visibility: 'public' | 'unlisted' | 'private'; seating: 'general_admission' | 'assigned_seating'
  event_class: EventClass; is_suspended: boolean; is_on_sale: boolean; price_from: number | null; organizer_name: string; venue: Venue
}
export interface TicketTypePublic {
  id: string; type: 'free' | 'paid'; name: string; description: string | null; price: number; order_limit: number; available: number
  sale_start: string | null; sale_end: string | null; on_sale: boolean; unavailable_reason: string | null
}
export interface TicketType {
  id: string; event_id: string; type: 'free' | 'paid'; name: string; description: string | null; price: number; order_limit: number
  quantity: number; available: number; reserved: number; sold: number; refunded: number; checked_in: number; hidden: boolean
  sale_start: string | null; sale_end: string | null
}
export interface EventDetail extends EventCard {
  description: string | null; registration_open_at: string | null; registration_close_at: string | null; capacity: number | null
  refund_policy: 'none' | 'before_event' | 'anytime'; refund_policy_text: string | null; organizer_contact_email: string | null
  paid_sales_active: boolean; can_manage: boolean; ticket_types: TicketTypePublic[]
}
export interface EventStats { capacity: number; tickets_sold: number; tickets_reserved: number; checked_in: number; orders: number; gross_sales: number }
export interface EventManage extends EventCard {
  organizer_id: string; description: string | null; registration_open_at: string | null; registration_close_at: string | null
  capacity: number | null; refund_policy: 'none' | 'before_event' | 'anytime'; refund_policy_text: string | null; access_key: string
  suspended_reason: string | null; duplicated_from_id: string | null; published_at: string | null; cancelled_at: string | null
  created_at: string; paid_sales_active: boolean; ticket_types: TicketType[]; stats: EventStats | null
}

export type SeatStatus = 'available' | 'held' | 'sold' | 'unavailable'
export interface SeatMapSeat { id: string; seat_id: string; number: number; is_accessible: boolean; status: SeatStatus; held_by_me: boolean }
export interface SeatMapSection {
  id: string; name: string; price_category: string; ticket_category_id: string | null; ticket_type_name: string | null
  price: number | null; rows: { label: string; seats: SeatMapSeat[] }[]
}
export interface SeatMap { event_id: string; configured: boolean; sections: SeatMapSection[] }

export interface QuoteLine {
  ticket_category_id: string; event_seat_id: string | null; name: string; quantity: number; unit_price: number; discount: number
  line_total: number; seat_section: string | null; seat_row: string | null; seat_number: number | null
}
export interface Quote {
  lines: QuoteLine[]; quantity: number; subtotal: number; discount_total: number; total: number; currency: string
  promo: { code: string; campaign_name: string; discount_type: 'percent' | 'fixed'; discount_value: number } | null
}
export interface PromoPreview { event_id: string; event_slug: string; code: string; campaign_name: string; discount_type: 'percent' | 'fixed'; discount_value: number; ticket_category_ids: string[] }

export interface EventBrief { id: string; slug: string; title: string; start_at: string; end_at: string; timezone: string; status: EventStatus; image: string | null; venue_name: string; venue_address: string; venue_city: string }
export type TicketStatus = 'valid' | 'checked_in' | 'cancelled' | 'refunded'
export interface Ticket {
  id: string; code: string; status: TicketStatus; event_id: string; order_id: string; order_number: string; ticket_type: string
  attendee_name: string; attendee_email: string; seat_section: string | null; seat_row: string | null; seat_number: number | null
  issued_at: string; checked_in_at: string | null; qr_payload: string | null; event: EventBrief
}
export type OrderStatus = 'pending' | 'completed' | 'cancelled' | 'refunded' | 'expired'
export interface Payment { id: string; kind: 'ticket_purchase' | 'activation_fee'; order_id: string | null; event_id: string | null; amount: number; processing_fee: number; currency: string; status: 'succeeded' | 'failed'; provider: string; provider_reference: string; is_simulation: boolean; failure_reason: string | null; created_at: string }
export interface Refund { id: string; order_id: string; amount: number; reason: string | null; status: string; is_simulation: boolean; created_at: string }
export interface OrderItem { id: string; ticket_category_id: string; name: string; quantity: number; unit_price: number; discount: number; line_total: number; seat_section: string | null; seat_row: string | null; seat_number: number | null }
export interface Order {
  id: string; number: string; status: OrderStatus; event: EventBrief; quantity: number; subtotal: number; discount_total: number
  total: number; processing_fee: number | null; currency: string; buyer_name: string; buyer_email: string; buyer_phone: string | null
  promo_code: string | null; expires_at: string | null; created_at: string; paid_at: string | null; cancelled_at: string | null
  cancel_reason: string | null; refund_eligible: boolean; is_simulation: boolean; items: OrderItem[]; tickets: Ticket[]
  payments: Payment[]; refunds: Refund[]
}
export interface AttendeeRow { ticket_id: string; code: string; status: TicketStatus; attendee_name: string; attendee_email: string; ticket_type: string; seat: string | null; order_id: string; order_number: string; issued_at: string; checked_in_at: string | null }
export interface SalesSummary { gross_sales: number; discounts: number; refunds: number; processing_fees: number; net_revenue: number; estimated_payout: number; orders: number; refunded_orders: number }

export interface Activation {
  id: string; event_id: string; status: 'pending' | 'active' | 'suspended'; is_active: boolean; fee_amount: number; currency: string
  steps: { key: string; done: boolean }[]; activated_at: string | null; suspended_reason: string | null; is_simulation: boolean
}
export interface CampaignStats { redemptions: number; orders: number; tickets_sold: number; gross_revenue: number; discount_amount: number; net_revenue: number; link_visits: number }
export interface Campaign {
  id: string; event_id: string; name: string; code: string; link: string; discount_type: 'percent' | 'fixed'; discount_value: number
  starts_at: string | null; ends_at: string | null; max_redemptions: number | null; is_active: boolean; ticket_category_ids: string[]
  created_at: string; stats: CampaignStats
}
export interface StaffAssignment { id: string; user: UserBrief; can_undo: boolean; created_at: string }
export interface AuditEntry { id: string; event_id: string | null; actor_id: string | null; actor_name: string; action: string; entity_type: string; entity_id: string; description: string; created_at: string }

export interface Analytics {
  event_id: string; generated_at: string; currency: string; is_simulation: boolean
  capacity: { total: number; sold: number; remaining: number; percent_sold: number }
  revenue: { gross: number; discounts: number; refunds: number; net: number }
  sales_over_time: { date: string; orders: number; tickets: number; revenue: number }[]
  by_ticket_type: { ticket_type_id: string; name: string; price: number; quantity: number; sold: number; remaining: number; revenue: number; checked_in: number }[]
  campaigns: { campaign_id: string; name: string; code: string; is_active: boolean; redemptions: number; tickets: number; gross: number; discount: number; net: number }[]
  attendance: { registered: number; checked_in: number; absent: number; percent: number }
}
export interface OrganizerSummary { events: number; upcoming_events: number; tickets_sold: number; net_revenue: number; checked_in: number }

export type CaseStatus = 'open' | 'in_progress' | 'waiting_for_customer' | 'resolved'
export interface SupportCase {
  id: string; number: string; kind: 'attendee' | 'organizer'; category: string; subject: string; status: CaseStatus; is_escalated: boolean
  requester: UserBrief; assigned_to: UserBrief | null
  context: { event_id: string | null; event_title: string | null; event_slug: string | null; order_id: string | null; order_number: string | null; ticket_id: string | null; ticket_code: string | null }
  created_at: string; updated_at: string; message_count: number; can_manage: boolean
  messages?: { id: string; author_id: string; author_name: string; from_staff: boolean; is_mine: boolean; body: string; created_at: string }[]
}

export interface Page<T> { items: T[]; total: number }
export interface AdminOverview { users: number; organizers: number; events_published: number; events_suspended: number; orders_completed: number; tickets_issued: number; gross_sales: number; refunds_total: number; payment_failures: number; activations_active: number; activations_suspended: number; open_reports: number; open_support_cases: number }
export interface AdminEventRow { id: string; slug: string; title: string; status: EventStatus; visibility: string; is_suspended: boolean; suspended_reason: string | null; start_at: string; organizer: UserBrief; tickets_sold: number; open_reports: number }
export interface AdminOrderRow { id: string; number: string; status: OrderStatus; total: number; quantity: number; buyer_name: string; buyer_email: string; event_id: string; event_title: string; promo_code: string | null; created_at: string }
export interface ActivationRow { id: string; event_id: string; event_title: string; organizer: UserBrief; status: 'pending' | 'active' | 'suspended'; fee_amount: number; fee_paid: boolean; terms_accepted: boolean; activated_at: string | null; suspended_reason: string | null; created_at: string }
export interface ReportRow { id: string; event_id: string; event_title: string; event_slug: string; event_suspended: boolean; reporter: UserBrief; reason: string; status: string; resolution_note: string | null; created_at: string }
export interface PromoActivityRow { campaign_id: string; event_id: string; event_title: string; name: string; code: string; is_active: boolean; max_redemptions: number | null; redemptions: number; discount_amount: number; net_revenue: number }
export interface PlatformSettings { activation_fee_kzt: number; processing_fee_percent: number; order_hold_minutes: number }
