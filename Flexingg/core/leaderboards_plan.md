# Leaderboards Feature Plan

## Overview
A dedicated "Leaderboards" page to display user rankings for key metrics: steps, calories burned, CardioCoins, GymGems. 
- Configurable for different metrics via URL and UI switches.
- Time periods: all-time (default), weekly, monthly.
- Scopes: global (default), friends, group-specific.
- Display: Top 3 on podium (reuse existing component), paginated list for 4th+ (10 per page).
- URLs: `/leaderboards/{metric}/{period}/?scope={scope}&group_id={id}` (e.g., `/leaderboards/steps/all/?scope=friends`).
- Default entry: `/leaderboards/cardiocoins/all/` (wealth rankings).
- Tie-breaking: Primary metric descending, then username ascending.
- Access: Replace "Gym" sidebar link with "Leaderboards" pointing to default URL.
- UI: Clean switches (tabs for metrics, dropdowns for period/scope/group select).

## Data Sources & Aggregation
- **Steps**: Sum `DailySteps.total_steps` for the user, filtered by period.
- **Calories**: Sum `GarminActivity.calories` for the user, filtered by period.
- **CardioCoins/GymGems**: Direct `UserProfile.cardio_coins` or `.gym_gems` (current balance; no period filter for balances, but can filter users active in period if needed).
- Queries use Django ORM:
  - Annotate UserProfile with aggregated values.
  - Filter by date ranges (e.g., `start_time_utc >= cutoff` for activities/steps).
  - For scopes:
    - Global: All UserProfile.
    - Friends: Users where Friendship accepted between current user and target.
    - Group: UserProfile in Group.members for specified group_id.
- Pagination: Django's Paginator on ranked queryset.

## UI Structure
- Page template: `core/templates/leaderboards.html` extends base.html.
- Top: Tabs for metrics (Steps | Calories | CardioCoins | GymGems).
- Controls: Dropdown for Period (All | Week | Month), Scope (Global | Friends | Group), Group select (if scope=group, load user's groups).
- Leaderboard section: Existing component for podium (pass top 3 users with rank/metric/name).
- List: Table or cards for next 10, with pagination links.
- Pixel-art styling consistent with app.

Mermaid diagram for page flow:
```mermaid
graph TD
    A[Enter /leaderboards/{metric}/{period}/] --> B{Logged in?}
    B -->|No| C[Redirect to sign-in]
    B -->|Yes| D[Load users queryset for metric/period/scope]
    D --> E[Annotate with rank and value]
    E --> F[Paginate results]
    F --> G[Render podium top 3]
    G --> H[Render list page 1 (4-13)]
    H --> I[UI controls update URL/query params]
    I --> J[Switch metric/period/scope refreshes page]
```

## Implementation Steps
- [ ] Update core/urls.py: Add leaderboard patterns under app_name='fitness'.
- [ ] Create core/views.py additions: LeaderboardView (class-based, handles GET, queries, context).
- [ ] Extend core/components/leaderboard/: Update component to accept users list, metric label; add list template variant.
- [ ] Create core/templates/leaderboards.html: Main page with tabs, controls, podium, list, pagination.
- [ ] Update sidebar: Modify core/components/sidebar_bottom_nav/template.html to replace Gym link with Leaderboards.
- [ ] Queries: Implement aggregation in view (e.g., UserProfile.objects.annotate(steps=Sum('daily_steps__total_steps', filter=Q(daily_steps__calendar_date__gte=cutoff)))).
- [ ] Handle scopes: In view, filter queryset based on request.GET['scope'].
- [ ] Pagination: Use Paginator on sliced queryset (skip top 3).
- [ ] Testing: Ensure queries efficient (add indexes if needed, but defer to code mode).
- [ ] Edge cases: No data, ties, private profiles (show only public metrics).

## Potential Extensions
- Real-time updates via WebSockets (future).
- Personal rank highlight.
- Filters for active users only.

This plan ensures copyable code: View logic per metric via if/elif, component reusable.