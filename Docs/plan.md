# Social Leaderboard Responsive Layout Fix Plan

## Updated Requirements Based on User Feedback

### 1. Mobile Podium Name Display - **TOOLTIP APPROACH**
- **Truncation**: Show first 10 characters, then "..." 
- **Interaction**: Tap avatar → show tooltip with full name
- **UX**: Tooltip appears on tap, disappears when finger lifted
- **Accessibility**: Ensure touch targets are adequate size

### 2. Navigation Issue - **WIDE ASPECT RATIO PROBLEM**
- **Affected Devices**: PC Chrome, iPad Safari (wider aspect ratios)
- **Working**: Phones, vertical desktop windows
- **Root Cause**: Likely media query breakpoint or CSS specificity issue at wider widths

## Finalized Solution Architecture

### Phase 1: Mobile Tooltip Implementation
```css
/* Mobile podium styles */
@media (max-width: 767px) {
  .podium-name {
    max-width: 60px; /* ~10 characters */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .podium-avatar {
    position: relative; /* For tooltip positioning */
  }
  
  .name-tooltip {
    display: none;
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #2a2a2a;
    padding: 8px 12px;
    border: 2px solid #00f5d4;
    z-index: 1000;
    white-space: nowrap;
    animation: fadeInTooltip 0.2s ease-out;
  }
}
```

### Phase 2: Navigation Breakpoint Investigation
- Check if 768px breakpoint is appropriate for wide aspect ratios
- Consider adding intermediate breakpoint for tablet landscape
- Verify CSS specificity isn't being overridden

### Phase 3: Implementation Steps
1. **Add mobile CSS styles** for name truncation and tooltip
2. **Add JavaScript** for tap tooltip functionality
3. **Investigate and fix** navigation media query issues
4. **Test on target devices** (Chrome PC, iPad Safari)

## Technical Implementation Details

### CSS Updates
- Mobile-first responsive approach
- Tooltip animation for smooth UX
- Maintain pixel-art aesthetic with themed borders

### JavaScript Requirements
- Touch event listeners for mobile
- Click event listeners for desktop
- Proper cleanup to prevent memory leaks

### Testing Scenarios
- **Mobile phones**: Portrait and landscape
- **iPad**: Landscape orientation (wide aspect ratio)
- **Desktop**: Various window sizes and aspect ratios
- **Touch interaction**: Verify tooltip works with touch

## Files to Modify

1. `Flexingg/social/templates/social/main.html` - Add mobile styles and JS
2. Potentially adjust `base.html` media queries if navigation breakpoint needs changes

## Success Criteria

- [ ] Mobile names truncate at 10 characters with "..."
- [ ] Tooltip shows full name on avatar tap
- [ ] Desktop sidebar visible on wide screens (≥768px effective width)
- [ ] Mobile bottom nav properly hidden on desktop
- [ ] All animations smooth and pixel-art themed
- [ ] Touch interactions work perfectly on mobile devices

Ready for implementation! Would you like me to proceed with Code mode to implement this solution?