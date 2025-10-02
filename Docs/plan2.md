# Connections Component Plan

## Overview
This plan outlines the creation of a new Django component called "Connections" that will replace the existing "integrations_section" component. The new component will provide a cleaner, more focused interface for managing the three main integrations: Garmin Connect, Liftosaur, and Health Connect.

## Current Analysis

### Existing integrations_section Structure
- **Framework**: Django Components
- **Layout**: 4-row settings menu (Garmin, Liftosaur, Health Connect, Apple Health)
- **Styling**: Pixel-themed with consistent button styling
- **Functionality**: 
  - Connect/Disconnect buttons per service
  - Sync buttons when connected
  - Modals for connection setup
  - AJAX form submissions
  - Liftosaur has dual connection modes (one-time file upload vs continuous token-based sync)

### Models Available
- `UserProfile` with connection fields:
  - Garmin: `garmin_auth` (foreign key to Garmin_Auth model)
  - Liftosaur: `liftosaur_user_id`, `liftosaur_session_token`
  - Health Connect: `hc_username`, `hc_password`, `hc_token`, `hc_token_expiry`
- `ConnectedService` model for tracking service connections
- `Garmin_Auth` model for Garmin authentication

### Existing Views & URLs
- Garmin: `garminconnect:connect_garmin`, `garminconnect:disconnect_garmin`
- Liftosaur: `fitness:connect_liftosaur`, `fitness:disconnect_liftosaur`, `liftosaur:import_data`, `liftosaur:save_token`
- Health Connect: `healthconnect:connect`, `healthconnect:disconnect`
- Sync: `fitness:sync_data_view`

## New Connections Component Design

### Architecture
```
Flexingg/core/components/connections/
├── template.html          # Main component template
├── connections.py         # Django component class
├── style.css             # Component-specific styles
└── script.js             # Component JavaScript (optional)
```

### Layout (3-Row Design)
1. **Garmin Connect Row**
   - Service name and status indicator
   - Connect button (when disconnected)
   - Sync + Disconnect + Info buttons (when connected)

2. **Liftosaur Row**
   - Service name and status indicator
   - Connect button with dropdown (when disconnected):
     - "One Time" → File upload modal
     - "Continuous" → Advanced sync modal (session token)
   - Sync + Disconnect + Info buttons (when connected)

3. **Health Connect Row**
   - Service name and status indicator
   - Connect button (when disconnected)
   - Sync + Disconnect + Info buttons (when connected)

### Component Features

#### Template Structure
```html
<div class="pixel-border bg-[#2a2a2a] mt-3 p-4 space-y-4">
    <!-- Garmin Connect Row -->
    <div class="flex items-center justify-between">
        <span class="font-pixel text-sm text-white">Garmin Connect</span>
        <!-- Connection state buttons -->
    </div>
    
    <!-- Liftosaur Row -->
    <div class="flex items-center justify-between">
        <span class="font-pixel text-sm text-white">Liftosaur</span>
        <!-- Connection state buttons with dropdown -->
    </div>
    
    <!-- Health Connect Row -->
    <div class="flex items-center justify-between">
        <span class="font-pixel text-sm text-white">Health Connect</span>
        <!-- Connection state buttons -->
    </div>
</div>

<!-- Modals for each connection type -->
<!-- Garmin Modal -->
<!-- Liftosaur One-Time Modal -->
<!-- Liftosaur Continuous Modal -->
<!-- Health Connect Modal -->
```

#### Connection States
- **Disconnected State**: Show appropriate connect button
- **Connected State**: Show sync + disconnect + info buttons
- **Connection Status**: Visual indicator (color-coded dot or text)

#### Modal System
1. **Garmin Connect Modal**
   - Email/password form
   - Links to existing `garminconnect:connect_garmin` view

2. **Liftosaur Modals**
   - **One-Time Modal**: File upload form
     - Links to existing `liftosaur:import_data` view
   - **Continuous Modal**: Session token input
     - Links to existing `liftosaur:save_token` view

3. **Health Connect Modal**
   - Username/password form
   - Links to existing `healthconnect:connect` view

#### JavaScript Features
- Modal toggle functionality
- AJAX form submissions (no page refresh)
- Connection status updates
- Error handling and user feedback

## Implementation Steps

### 1. Component Creation
- Create `connections/` directory in `Flexingg/core/components/`
- Create `template.html` with 3-row layout
- Create `connections.py` Django component class
- Create `style.css` with pixel-themed styling
- Create `script.js` for interactive functionality

### 2. Component Registration
- Update `Flexingg/core/components/__init__.py` to import and register the new component

### 3. Template Integration
- Replace `integrations_section` usage with `connections` in relevant templates (only in core/templates/settings.html for now)
- Ensure all context variables are properly passed

### 4. Testing
- Test each connection flow
- Verify modal functionality
- Confirm AJAX submissions work correctly
- Test connection state management

## Context Variables Required

The component will need access to:
- `garmin_connected` (boolean)
- `liftosaur_connected` (boolean) 
- `has_liftosaur_token` (boolean)
- `hc_connected` (boolean)
- Current user profile for connection status

## Styling Approach

- Maintain pixel-themed design consistency
- Use existing CSS classes where possible
- Ensure responsive design
- Keep visual parity with current integrations_section

## Clarified Requirements

1. **Info Button Functionality**: The "info" button should show usage instructions for each service.

2. **Connection Status Indicators**: Connection status should be indicated using color-coded dots (green for connected, red for disconnected).

3. **Liftosaur Sync Options**: The "one time" vs "continuous" choice should be implemented as a dropdown on the connect button.

4. **Error Handling**: Connection failures should be handled using toast notifications.

5. **Sync Button Behavior**: Sync buttons should only show for services that support manual sync (none currently support this).

6. **Component Context**: This component should be a direct replacement for integrations_section in core/templates/settings.html only.

## Success Criteria

- [ ] Component renders correctly in all connection states
- [ ] All three services can be connected/disconnected successfully
- [ ] Liftosaur one-time and continuous modes both work
- [ ] Modals function properly with existing backend views
- [ ] AJAX submissions prevent page refreshes
- [ ] Styling matches existing design system
- [ ] Component integrates seamlessly with existing codebase