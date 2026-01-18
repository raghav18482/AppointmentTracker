<!-- 7d3f8292-5ebe-4b4d-8ba5-ffdf53b4afb1 3d66c672-7528-401f-b672-95cec4738d9f -->
# Frontend React UI Implementation Plan

## Project Location

**Frontend Directory**: `/Users/raghavswami/Desktop/Appointment Tracker CRM/`

This will be a completely separate project from the backend, allowing independent development and deployment.

## Architecture Overview

```
Frontend Structure (at /Users/raghavswami/Desktop/Appointment Tracker CRM/):
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ui/             # Shadcn components
│   │   ├── layout/         # Layout components
│   │   ├── queue/          # Queue-specific components
│   │   ├── dashboard/      # Dashboard widgets
│   │   └── forms/          # Form components
│   ├── pages/              # Page components
│   │   ├── auth/           # Login, Register
│   │   ├── dashboard/      # Main dashboard
│   │   ├── queue/          # Queue management
│   │   ├── staff/          # Staff management
│   │   ├── counters/       # Counter management
│   │   └── notifications/  # Notification management
│   ├── contexts/           # React contexts
│   │   ├── AuthContext     # Authentication state
│   │   └── BusinessContext # Business selection
│   ├── services/           # API services
│   │   ├── api.ts          # API client with interceptors
│   │   ├── auth.ts         # Auth API calls
│   │   ├── queue.ts        # Queue API calls
│   │   ├── dashboard.ts    # Dashboard API calls
│   │   └── ...
│   ├── hooks/              # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useQueue.ts
│   │   └── usePolling.ts   # Auto-refresh hook
│   ├── lib/                # Utilities
│   │   ├── utils.ts        # Helper functions
│   │   └── constants.ts    # Constants
│   └── App.tsx             # Main app component
```

## Implementation Steps

### Phase 1: Project Setup & Foundation

**1.1 Initialize React Project**

- Create Vite + React + TypeScript project
- Install dependencies: React Router, Axios, date-fns
- Setup Tailwind CSS configuration
- Configure Shadcn/ui (install and setup)

**1.2 Project Structure**

- Create folder structure (components, pages, contexts, services, hooks)
- Setup path aliases (@/components, @/lib, etc.)
- Configure environment variables (.env for API URL)

**1.3 Core Utilities**

- Create API client (`services/api.ts`) with:
  - Base URL configuration
  - Request/response interceptors
  - Token management (store in localStorage)
  - Business ID header injection
  - Error handling
- Create utility functions (`lib/utils.ts`)
- Create constants file (`lib/constants.ts`)

### Phase 2: Authentication & Layout

**2.1 Authentication Context**

- Create `AuthContext` with:
  - User state management
  - Login/logout functions
  - Token persistence
  - Auto-logout on token expiry
- Create `useAuth` hook

**2.2 Business Context**

- Create `BusinessContext` for:
  - Current business selection
  - Business list management
  - Business switching

**2.3 Layout Components**

- Create `Layout` component with:
  - Header (user info, business selector, logout)
  - Sidebar navigation (role-based menu)
  - Main content area
- Create `ProtectedRoute` wrapper
- Create `BusinessSelector` component

**2.4 Auth Pages**

- Login page (`pages/auth/Login.tsx`)
  - Email/password form
  - Error handling
  - Redirect after login
- Register page (`pages/auth/Register.tsx`)
  - User registration form
  - Success handling

### Phase 3: Dashboard Implementation

**3.1 Dashboard Page**

- Create main dashboard (`pages/dashboard/Dashboard.tsx`)
- Integrate live queue view API
- Display stats cards (total waiting, served today, etc.)

**3.2 Dashboard Components**

- `StatsCard` component (reusable stat display)
- `QueueOverview` component (live queue list)
- `CounterActivity` component (counter status)
- `MissedCustomers` component (missed customers list)
- `FailedNotifications` component (notification errors)

**3.3 Real-time Updates**

- Create `usePolling` hook for auto-refresh
- Implement polling for dashboard (every 5-10 seconds)
- Add manual refresh button
- Show loading states during refresh

### Phase 4: Queue Management

**4.1 Queue Page**

- Create queue management page (`pages/queue/QueueManagement.tsx`)
- Display active queue items
- Filter by counter, queue type
- Sort by position/type

**4.2 Queue Components**

- `QueueItemCard` component:
  - Customer info
  - Position, status, wait time
  - Queue type badge (normal/emergency)
  - Action buttons (notify, serve, miss, cancel)
- `QueueList` component (grid/list view)
- `BookingForm` component (create booking modal)

**4.3 Queue Actions**

- Implement serve next customer
- Implement notify customer
- Implement handle miss
- Implement cancel booking
- Show success/error toasts

**4.4 Booking Creation**

- Create booking form modal
- Normal booking form
- Emergency booking form
- Customer search/creation

### Phase 5: Staff Management (Admin/Manager Only)

**5.1 Staff Page**

- Create staff management page (`pages/staff/StaffManagement.tsx`)
- List all staff members
- Role badges (OWNER, MANAGER, COUNTER)

**5.2 Staff Components**

- `StaffList` component (table/cards)
- `StaffForm` component (create new staff)
- `StaffRoleUpdate` component (update role)
- `DeleteStaff` confirmation dialog

**5.3 Staff Operations**

- Create new staff (user + association)
- Update staff role
- Remove staff member
- Permission checks (OWNER/MANAGER only)

### Phase 6: Counter Management (Admin/Manager Only)

**6.1 Counter Page**

- Create counter management page (`pages/counters/CounterManagement.tsx`)
- List all counters
- Active/inactive status

**6.2 Counter Components**

- `CounterList` component
- `CounterForm` component (create/edit)
- `CounterStatusToggle` component

**6.3 Counter Operations**

- Create counter
- Update counter (name, status)
- Delete counter (with validation)
- Permission checks

### Phase 7: Notification Management

**7.1 Notification Page**

- Create notification management page (`pages/notifications/NotificationManagement.tsx`)
- List failed notifications
- Retry functionality

**7.2 Notification Components**

- `NotificationList` component
- `RetryNotification` button
- `NotificationStatus` badge

### Phase 8: UI Polish & Responsiveness

**8.1 Responsive Design**

- Mobile breakpoints for all pages
- Responsive tables (convert to cards on mobile)
- Mobile-friendly forms
- Touch-friendly buttons

**8.2 Loading & Error States**

- Loading skeletons
- Error boundaries
- Empty states
- Toast notifications (success/error)

**8.3 Accessibility**

- Keyboard navigation
- ARIA labels
- Focus management
- Screen reader support

**8.4 Theme & Styling**

- Consistent color scheme
- Dark mode support (optional)
- Smooth animations
- Professional typography

## Key Files to Create

### Core Files

- `src/services/api.ts` - API client with interceptors
- `src/contexts/AuthContext.tsx` - Authentication state
- `src/contexts/BusinessContext.tsx` - Business selection
- `src/hooks/useAuth.ts` - Auth hook
- `src/hooks/usePolling.ts` - Auto-refresh hook
- `src/lib/utils.ts` - Utility functions

### API Service Files

- `src/services/auth.ts` - Auth API calls
- `src/services/business.ts` - Business API calls
- `src/services/queue.ts` - Queue API calls
- `src/services/dashboard.ts` - Dashboard API calls
- `src/services/staff.ts` - Staff API calls
- `src/services/counters.ts` - Counter API calls
- `src/services/notifications.ts` - Notification API calls

### Main Pages

- `src/pages/auth/Login.tsx`
- `src/pages/auth/Register.tsx`
- `src/pages/dashboard/Dashboard.tsx`
- `src/pages/queue/QueueManagement.tsx`
- `src/pages/staff/StaffManagement.tsx`
- `src/pages/counters/CounterManagement.tsx`
- `src/pages/notifications/NotificationManagement.tsx`

### Layout Components

- `src/components/layout/Layout.tsx`
- `src/components/layout/Header.tsx`
- `src/components/layout/Sidebar.tsx`
- `src/components/layout/BusinessSelector.tsx`
- `src/components/layout/ProtectedRoute.tsx`

## Technology Stack

- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/ui
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **State Management**: React Context API
- **Date Handling**: date-fns
- **Icons**: Lucide React (Shadcn default)

## API Integration Points

All APIs will be integrated:

- `/api/v1/auth/*` - Authentication
- `/api/v1/business/*` - Business management
- `/api/v1/queue/*` - Queue operations
- `/api/v1/dashboard/*` - Dashboard data
- `/api/v1/staff/*` - Staff management
- `/api/v1/counters/*` - Counter management
- `/api/v1/notifications/*` - Notification management

## Role-Based Access Control

- **OWNER/MANAGER**: Full access (staff, counters, dashboard)
- **COUNTER**: Queue operations only (serve, notify, miss, cancel)

## Real-time Updates Strategy

- Polling every 5-10 seconds for dashboard
- Manual refresh buttons on all pages
- Optimistic UI updates where possible
- Loading states during API calls

### To-dos

- [ ] Initialize React + Vite + TypeScript project, install dependencies (Tailwind, Shadcn/ui, React Router, Axios), setup project structure
- [ ] Create API client service with interceptors, token management, business ID header injection, and error handling
- [ ] Implement AuthContext and useAuth hook for authentication state management, token persistence, and auto-logout
- [ ] Create BusinessContext for business selection and switching functionality
- [ ] Build Layout, Header, Sidebar, BusinessSelector, and ProtectedRoute components with role-based navigation
- [ ] Create Login and Register pages with forms, validation, and error handling
- [ ] Build dashboard page with live queue view, stats cards, counter activity, and missed customers widgets
- [ ] Create usePolling hook for auto-refresh functionality on dashboard and queue pages
- [ ] Implement queue management page with QueueItemCard, QueueList, booking forms, and queue action buttons (serve, notify, miss, cancel)
- [ ] Build staff management page with staff list, create staff form, role update, and delete functionality (OWNER/MANAGER only)
- [ ] Create counter management page with counter list, create/edit forms, and delete functionality (OWNER/MANAGER only)
- [ ] Build notification management page with failed notifications list and retry functionality
- [ ] Implement responsive design for mobile devices, convert tables to cards on mobile, optimize touch interactions
- [ ] Add loading skeletons, error boundaries, empty states, toast notifications, and final UI polish