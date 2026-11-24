import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

// meta.auth: must be signed in · meta.organizer: organizer or admin · meta.admin: platform admin
const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  { path: '/e/:slug', name: 'event', component: () => import('@/views/EventView.vue'), props: true },
  { path: '/checkout/:id', name: 'checkout', component: () => import('@/views/CheckoutView.vue'), props: true, meta: { auth: true } },
  { path: '/orders', name: 'orders', component: () => import('@/views/OrdersView.vue'), meta: { auth: true } },
  { path: '/orders/:id', name: 'order', component: () => import('@/views/OrderView.vue'), props: true, meta: { auth: true } },
  { path: '/tickets', name: 'tickets', component: () => import('@/views/TicketsView.vue'), meta: { auth: true } },
  { path: '/support', name: 'support', component: () => import('@/views/SupportListView.vue'), meta: { auth: true } },
  { path: '/support/:id', name: 'support-case', component: () => import('@/views/SupportCaseView.vue'), props: true, meta: { auth: true } },
  { path: '/account', name: 'account', component: () => import('@/views/AccountView.vue'), meta: { auth: true } },

  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue') },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue') },
  { path: '/verify-email', name: 'verify-email', component: () => import('@/views/auth/VerifyEmailView.vue') },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('@/views/auth/ForgotPasswordView.vue') },
  { path: '/reset-password', name: 'reset-password', component: () => import('@/views/auth/ResetPasswordView.vue') },

  { path: '/organizer', name: 'organizer', component: () => import('@/views/organizer/DashboardView.vue'), meta: { organizer: true } },
  { path: '/organizer/profile', name: 'organizer-profile', component: () => import('@/views/organizer/ProfileView.vue'), meta: { auth: true } },
  { path: '/organizer/profile/emotional-support', name: 'organizer-emotional-support', component: () => import('@/views/organizer/EmotionalSupportView.vue'), meta: { auth: true } },
  { path: '/organizer/events/new', name: 'event-new', component: () => import('@/views/organizer/EventFormView.vue'), meta: { organizer: true } },
  { path: '/organizer/events/:id/edit', name: 'event-edit', component: () => import('@/views/organizer/EventFormView.vue'), props: true, meta: { organizer: true } },
  {
    path: '/organizer/events/:id',
    component: () => import('@/views/organizer/EventManageLayout.vue'),
    props: true,
    meta: { organizer: true },
    children: [
      { path: '', name: 'manage-overview', component: () => import('@/views/organizer/ManageOverview.vue') },
      { path: 'tickets', name: 'manage-tickets', component: () => import('@/views/organizer/ManageTickets.vue') },
      { path: 'seating', name: 'manage-seating', component: () => import('@/views/organizer/ManageSeating.vue') },
      { path: 'orders', name: 'manage-orders', component: () => import('@/views/organizer/ManageOrders.vue') },
      { path: 'attendees', name: 'manage-attendees', component: () => import('@/views/organizer/ManageAttendees.vue') },
      { path: 'promo', name: 'manage-promo', component: () => import('@/views/organizer/ManagePromo.vue') },
      { path: 'staff', name: 'manage-staff', component: () => import('@/views/organizer/ManageStaff.vue') },
      { path: 'activation', name: 'manage-activation', component: () => import('@/views/organizer/ManageActivation.vue') },
      { path: 'analytics', name: 'manage-analytics', component: () => import('@/views/organizer/ManageAnalytics.vue') },
      { path: 'history', name: 'manage-history', component: () => import('@/views/organizer/ManageHistory.vue') },
      { path: 'support', name: 'manage-support', component: () => import('@/views/organizer/ManageSupport.vue') },
    ],
  },

  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { admin: true },
    children: [
      { path: '', name: 'admin-overview', component: () => import('@/views/admin/AdminOverview.vue') },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/AdminUsers.vue') },
      { path: 'events', name: 'admin-events', component: () => import('@/views/admin/AdminEvents.vue') },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/AdminOrders.vue') },
      { path: 'payments', name: 'admin-payments', component: () => import('@/views/admin/AdminPayments.vue') },
      { path: 'activations', name: 'admin-activations', component: () => import('@/views/admin/AdminActivations.vue') },
      { path: 'reports', name: 'admin-reports', component: () => import('@/views/admin/AdminReports.vue') },
      { path: 'support', name: 'admin-support', component: () => import('@/views/admin/AdminSupport.vue') },
      { path: 'promo', name: 'admin-promo', component: () => import('@/views/admin/AdminPromo.vue') },
      { path: 'audit', name: 'admin-audit', component: () => import('@/views/admin/AdminAudit.vue') },
      { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/AdminSettings.vue') },
    ],
  },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.restore()
  const needsLogin = to.matched.some((r) => r.meta.auth || r.meta.organizer || r.meta.admin)
  if (needsLogin && !auth.isSignedIn) return { name: 'login', query: { next: to.fullPath } }
  if (to.matched.some((r) => r.meta.admin) && !auth.isAdmin) return { name: 'home' }
  // A signed-in attendee who opens the organizer area is sent to "become an organizer".
  if (to.matched.some((r) => r.meta.organizer) && !auth.isOrganizer) return { name: 'organizer-profile' }
  return true
})
