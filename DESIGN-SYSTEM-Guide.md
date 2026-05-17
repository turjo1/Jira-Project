# Design System: Jira Team Performance Analytics

## Overview

This design system defines the visual language and component library for the Jira Team Performance Analytics tool—a real-time dashboard for engineering managers and product owners to track team velocity, identify bottlenecks, and measure developer performance.

**Tech Stack:** React + Tailwind CSS  
**Accessibility:** WCAG 2.1 AA compliant  
**Status:** Ready for Implementation  
**Last Updated:** 2026-05-16

---

## Quick Start for Developers

### 1. Setup Tailwind CSS
```bash
npm install -D tailwindcss postcss autoprefixer
npm install inter
```

### 2. Use Tailwind Config
Copy `tailwind.config.js` to your project root. All color tokens, spacing, and typography are pre-configured.

### 3. Import Fonts
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 4. Build Components
Reference `DESIGN-HANDOFF-Components.md` for detailed component specifications, measurements, and code examples.

---

## Design Principles

### 1. **Clarity Over Decoration**
Every visual element serves a purpose. Metrics should be immediately readable. No unnecessary gradients, animations, or effects that distract from data.

### 2. **Semantic Color**
- Green (#10B981) = healthy, good performance
- Amber (#F59E0B) = warning, needs attention
- Red (#EF4444) = critical, action required
- Users should understand status at a glance without reading labels

### 3. **Consistent Spacing**
Use the 4px-based spacing scale (4px, 8px, 12px, 16px, 24px, 32px, 48px) consistently. Never use arbitrary values.

### 4. **Accessible by Default**
- Sufficient contrast (4.5:1 for normal text)
- Keyboard navigation on all interactive elements
- Screen reader announcements for dynamic content
- Focus indicators always visible

### 5. **Performance First**
- Skeleton loaders for data fetching (no spinners)
- Lazy loading for large tables
- CSS optimized with Tailwind tree-shaking
- Minimal, functional animations

---

## Color System

### Semantic Colors

| Color | Hex | Usage | WCAG AA |
|-------|-----|-------|---------|
| **Primary** | #2563EB | CTAs, links, focus states | 4.5:1 ✓ |
| **Success** | #10B981 | Healthy metrics, positive status | 4.5:1 ✓ |
| **Warning** | #F59E0B | Caution, needs attention | 4.5:1 ✓ |
| **Critical** | #EF4444 | Errors, critical issues | 4.5:1 ✓ |

### Role Colors

| Role | Hex | Usage |
|------|-----|-------|
| **Developer** | #3B82F6 | Dev team members |
| **QA** | #A855F7 | Quality assurance team |
| **Product Owner** | #14B8A6 | Product management |

### Neutral Palette

| Element | Hex | Usage |
|---------|-----|-------|
| Background | #FFFFFF | Main app background |
| Secondary BG | #F9FAFB | Panels, cards, sections |
| Tertiary BG | #F3F4F6 | Hover states, disabled |
| Text Primary | #1F2937 | Main content (98% of text) |
| Text Secondary | #6B7280 | Labels, hints, metadata |
| Text Tertiary | #9CA3AF | Helper text, timestamps |
| Border | #E5E7EB | Dividers, input borders |

---

## Typography System

### Font Stack
- **Primary:** Inter (Google Fonts) — clean, modern, excellent readability
- **Monospace:** Monaco or SF Mono for ticket keys and code

### Heading Scale

```
H1 (32px, 700) — Page titles
├─ H2 (24px, 600) — Section titles
├─ H3 (20px, 600) — Subsection titles
└─ H4 (16px, 600) — Card/modal titles
```

### Body Text

```
Body Regular (14px, 400) — Main content
├─ Body Emphasis (14px, 500) — Highlighted text
└─ Body Small (12px, 400) — Labels, helpers, metadata
```

### Monospace
```
Mono (12px, 400) — Ticket keys, timestamps
```

---

## Spacing Scale

**Base Unit:** 4px

```
xs:   4px  (icon spacing, tight gaps)
sm:   8px  (input padding, form fields)
md:  12px  (component padding, gaps)
lg:  16px  (section padding, larger gaps)
xl:  24px  (major spacing, section breaks)
2xl: 32px  (large sections, hero spacing)
3xl: 48px  (hero sections, major breaks)
```

---

## Core Components

### 1. Metrics Tile (Dashboard)
**Purpose:** Display a single KPI with health status  
**Specs:** See `DESIGN-HANDOFF-Components.md` section 1

- 280px × 120px container
- Color-coded left border (4px) for health status
- Hover to drill-down into detail view
- Responsive: Stacks on tablet/mobile

### 2. Status Badge
**Purpose:** Display ticket status with semantic color  
**Specs:** See `DESIGN-HANDOFF-Components.md` section 2

- Solid or outline variants
- Small (28px) or medium (32px) sizes
- Icons for in-progress (▶) and done (✓)
- Keyboard and screen-reader accessible

### 3. Data Table
**Purpose:** Sortable, filterable ticket list  
**Specs:** See `DESIGN-HANDOFF-Components.md` section 3

- Sticky header (56px), 6+ configurable columns
- Sortable: Click header to toggle ASC/DESC
- Configurable: Settings icon to show/hide columns
- Responsive: Column hiding on mobile

### 4. Developer Detail Modal
**Purpose:** Individual performance drill-down  
**Specs:** See `DESIGN-HANDOFF-Components.md` section 4

- 600px width, modal dialog pattern
- Metrics row + last 30 tickets table
- Esc key or backdrop click to close
- Focus trap during open

### Additional Components to Implement
- Button (primary, secondary, ghost)
- Input & Search fields
- Navigation (top bar, user menu)
- Forms & Validation
- Dropdowns & Filters

---

## Layout Patterns

### Dashboard (Home View)
```
┌─────────────────────────────────┐
│ Navigation (64px)               │
├─────────────────────────────────┤
│ Padding: 32px horizontal        │
│                                 │
│  [Metric] [Metric]             │ 2×2 grid
│                                 │ gap: 24px
│  [Metric] [Metric]             │
│                                 │
├─────────────────────────────────┤
│ Last updated | [Refresh]        │ Sticky footer
└─────────────────────────────────┘
```

**Responsive:**
- Desktop (>1200px): 2×2 grid, 280×120px tiles
- Tablet (768-1200px): 2 rows, single column
- Mobile (<768px): Full width, single column

### Table View
```
┌─────────────────────────────────┐
│ [Controls] | [⚙] [↻]           │ Sticky control bar (56px)
├─────────────────────────────────┤
│ Key ↑↓ | Title | Assignee | ... │ Sticky header (48px)
├─────────────────────────────────┤
│ [Scrollable table rows]         │
└─────────────────────────────────┘
```

### Kanban Board
```
┌─────────────────────────────────┐
│ To Do | In Progress | QA | Done │ 4 fixed columns
├─────────────────────────────────┤
│ [Developer cards with tickets]  │
└─────────────────────────────────┘
```

---

## Responsive Breakpoints

| Breakpoint | Width | Behavior |
|---|---|---|
| Mobile | < 640px | Single column, full width (-32px margin) |
| Tablet | 640px - 1024px | 2-column where possible, reduced spacing |
| Desktop | > 1024px | Full layout, all features visible |

---

## Interactive States

### Buttons
- **Default:** bg-blue-600, text-white, shadow-sm
- **Hover:** bg-blue-700, shadow-md, cursor-pointer
- **Active:** bg-blue-800, pressed effect
- **Disabled:** opacity-50, cursor-not-allowed
- **Focus:** ring-2 ring-blue-500

### Form Inputs
- **Default:** bg-white, border-gray-200, text-gray-900
- **Focus:** border-blue-600, ring-2 ring-blue-200
- **Error:** border-red-500, ring-red-200
- **Disabled:** bg-gray-100, opacity-50

### Cards & Rows
- **Default:** bg-white, border-gray-200, shadow-sm
- **Hover:** shadow-md, bg-gray-50, cursor-pointer
- **Selected:** bg-blue-50, border-blue-500
- **Focus:** ring-2 ring-blue-500

---

## Animation & Motion

### Timing Guidelines

| Duration | Use Case |
|---|---|
| 100ms | Quick interactions (hover, click feedback) |
| 200ms | Card hover, shadow transitions |
| 300ms | Page transitions, modal open/close |

### Examples

**Button Hover**
```css
transition: background-color 100ms ease, box-shadow 200ms ease;
```

**Modal Open/Close**
```css
animation: fadeIn 300ms ease-out;
/* from: opacity-0, scale-95; to: opacity-100, scale-100 */
```

**Loading Skeleton**
```css
animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
/* oscillates between opacity-100 and opacity-50 */
```

**Principle:** Animations enhance, not distract. Always provide static alternatives.

---

## Accessibility (WCAG 2.1 AA)

### Color Contrast
- ✓ Normal text (14px): 4.5:1 minimum
- ✓ Large text (18px+): 3:1 minimum
- ✓ UI components: 3:1 minimum
- ✓ Status never conveyed by color alone (use icons)

### Keyboard Navigation
- All interactive elements focusable via Tab
- Logical tab order (left-to-right, top-to-bottom)
- Focus ring visible (2px solid #2563EB, 2px offset)
- Esc key closes modals
- Enter/Space activates buttons

### Screen Reader Support
- All buttons have accessible labels (text or aria-label)
- Form fields have associated labels
- Tables have header rows (role="columnheader")
- Modals announce role="dialog", aria-modal="true"
- Live regions (aria-live="polite") for dynamic updates

### Motion & Animation
- Respects prefers-reduced-motion media query
- No auto-play animations
- Animations are optional enhancements, not essential

### Testing Checklist
- [ ] Run axe DevTools for contrast and ARIA issues
- [ ] Test with keyboard only (Tab, Enter, Esc)
- [ ] Test with screen reader (VoiceOver, NVDA, JAWS)
- [ ] Verify focus always visible
- [ ] Check form error messages announced
- [ ] Test responsive layouts at all breakpoints

---

## Development Guide

### File Structure
```
src/
├── components/
│   ├── dashboard/
│   │   ├── MetricsTile.jsx
│   │   ├── Dashboard.jsx
│   ├── table/
│   │   ├── TicketsTable.jsx
│   │   ├── TableView.jsx
│   ├── kanban/
│   │   ├── KanbanBoard.jsx
│   ├── common/
│   │   ├── StatusBadge.jsx
│   │   ├── Button.jsx
│   │   ├── Modal.jsx
│   ├── layout/
│   │   ├── Navigation.jsx
├── hooks/
│   ├── useSort.js
│   ├── useFilter.js
├── styles/
│   ├── globals.css
│   ├── tailwind.css
```

### Naming Conventions
- **Components:** PascalCase (`MetricsTile.jsx`)
- **Utilities:** camelCase (`useSort.js`)
- **CSS classes:** kebab-case (`metric-tile`, `status-badge`)
- **Hooks:** `use[Feature]` (`useSort`, `useFilter`)

### Code Standards
1. **Use Tailwind for all styles** — No separate CSS files
2. **Component props should be typed** — PropTypes or TypeScript
3. **Keep components small** — Max 300 lines
4. **Test accessibility** — Use axe DevTools in development
5. **Follow React best practices** — Hooks, dependencies, etc.

### Example Component

```jsx
import React from 'react';
import PropTypes from 'prop-types';

function MetricsTile({
  status = 'success',
  title,
  value,
  unit,
  trend,
  onClick,
}) {
  const statusClasses = {
    success: 'border-l-green-500',
    warning: 'border-l-amber-500',
    critical: 'border-l-red-500',
  };

  return (
    <article
      className={`
        w-72 h-32 p-4 rounded-lg border border-gray-200
        ${statusClasses[status]} border-l-4
        bg-white shadow-sm hover:shadow-md transition-shadow
        cursor-pointer focus-visible:outline-none
        focus-visible:ring-2 focus-visible:ring-blue-500
      `}
      onClick={onClick}
      role="region"
      aria-label={`${title} metric`}
      tabIndex={0}
    >
      <p className="text-xs font-medium text-gray-600">{title}</p>
      <p className="text-2xl font-semibold text-gray-900 mt-2">
        {value} <span className="text-sm text-gray-600">{unit}</span>
      </p>
      {trend && (
        <p className="text-xs font-medium text-green-600 mt-1">
          {trend.direction === 'up' ? '↑' : '↓'} {trend.amount} ({trend.percent}%)
        </p>
      )}
    </article>
  );
}

MetricsTile.propTypes = {
  status: PropTypes.oneOf(['success', 'warning', 'critical']),
  title: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired,
  unit: PropTypes.string.isRequired,
  trend: PropTypes.shape({
    direction: PropTypes.oneOf(['up', 'down']),
    amount: PropTypes.number,
    percent: PropTypes.number,
  }),
  onClick: PropTypes.func,
};

export default MetricsTile;
```

---

## Common Patterns

### Responsive Container
```jsx
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  {/* Scales with breakpoints */}
</div>
```

### Grid Layout
```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  {/* Children scale based on breakpoint */}
</div>
```

### Loading State
```jsx
{isLoading ? (
  <div className="h-32 bg-gray-200 rounded animate-pulse" />
) : (
  <MetricsTile {...props} />
)}
```

### Focus Management in Modal
```jsx
const modalRef = useRef(null);

useEffect(() => {
  if (isOpen) {
    modalRef.current?.focus();
  }
}, [isOpen]);
```

---

## Performance Tips

1. **Lazy load large tables** — Use virtualization for 100+ rows
2. **Memoize expensive components** — React.memo() for list items
3. **Use skeleton loaders** — Never use spinners
4. **Optimize images** — WebP with fallbacks
5. **Monitor bundle size** — Tailwind tree-shaking removes unused classes
6. **Defer non-critical CSS** — Load fonts async

---

## Testing

### Unit Tests
```jsx
describe('MetricsTile', () => {
  it('renders metric title and value', () => {
    const { getByText } = render(
      <MetricsTile title="Cycle Time" value={18.5} unit="days" />
    );
    expect(getByText('Cycle Time')).toBeInTheDocument();
  });

  it('has accessible label', () => {
    const { container } = render(
      <MetricsTile title="Cycle Time" value={18.5} unit="days" />
    );
    expect(container.querySelector('[aria-label]')).toHaveAttribute(
      'aria-label',
      'Cycle Time metric'
    );
  });
});
```

### Accessibility Tests
- Use axe DevTools for automated checks
- Test Tab/Shift+Tab keyboard navigation
- Test with screen reader (VoiceOver, NVDA)
- Verify focus indicators on all interactive elements

---

## Resources

- **Tailwind CSS:** https://tailwindcss.com/docs
- **Inter Font:** https://fonts.google.com/specimen/Inter
- **WCAG 2.1:** https://www.w3.org/WAI/WCAG21/quickref/
- **React Accessibility:** https://developer.mozilla.org/en-US/docs/Learn/Accessibility
- **Component Specs:** `DESIGN-HANDOFF-Components.md` (this directory)
- **Tailwind Config:** `tailwind.config.js` (this directory)

---

**Version:** 1.0  
**Status:** Ready for Implementation  
**Last Updated:** 2026-05-16
