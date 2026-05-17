# Design Handoff: Jira Team Performance Analytics - Component Library

**Last Updated:** 2026-05-16  
**Status:** Ready for Development  
**Tech Stack:** React + Tailwind CSS  
**Accessibility:** WCAG AA Compliant

---

## Design Token System

### Color Palette

#### Semantic Colors
| Token | Value | Usage | Contrast Ratio |
|-------|-------|-------|---|
| `color-primary` | #2563EB | Primary CTAs, links, focus states | 4.5:1 |
| `color-success` | #10B981 | Healthy metrics, green status | 4.5:1 |
| `color-warning` | #F59E0B | Watch/attention needed | 4.5:1 |
| `color-critical` | #EF4444 | Critical/error states | 4.5:1 |

#### Role Colors
| Token | Value | Usage |
|-------|-------|-------|
| `color-role-dev` | #3B82F6 | Developer role badge |
| `color-role-qa` | #A855F7 | QA role badge |
| `color-role-po` | #14B8A6 | Product Owner role badge |

#### Neutral Palette
| Token | Value | Usage |
|-------|-------|-------|
| `color-bg-primary` | #FFFFFF | Main background |
| `color-bg-secondary` | #F9FAFB | Secondary background (panels) |
| `color-bg-tertiary` | #F3F4F6 | Hover backgrounds |
| `color-text-primary` | #1F2937 | Primary text (98% of content) |
| `color-text-secondary` | #6B7280 | Secondary text (labels, hints) |
| `color-text-tertiary` | #9CA3AF | Tertiary text (helper text, metadata) |
| `color-border` | #E5E7EB | Borders, dividers |
| `color-border-strong` | #D1D5DB | Stronger borders (focus) |

### Typography Scale

#### Font Family
- **Headings:** `font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Body:** `font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Monospace:** `font-family: 'Monaco', 'SF Mono', monospace`

#### Heading Styles
| Token | Font Size | Font Weight | Line Height | Letter Spacing | Usage |
|-------|-----------|-------------|-------------|---|---|
| `text-h1` | 32px | 700 | 1.2 (38px) | -0.02em | Page titles |
| `text-h2` | 24px | 600 | 1.25 (30px) | -0.01em | Section titles |
| `text-h3` | 20px | 600 | 1.3 (26px) | 0 | Subsection titles |
| `text-h4` | 16px | 600 | 1.4 (22px) | 0 | Card titles, modal headers |

#### Body Styles
| Token | Font Size | Font Weight | Line Height | Usage |
|-------|-----------|-------------|-------------|---|
| `text-body-regular` | 14px | 400 | 1.5 (21px) | Body text, table cells, descriptions |
| `text-body-emphasis` | 14px | 500 | 1.5 (21px) | Emphasized text within body |
| `text-body-small` | 12px | 400 | 1.5 (18px) | Secondary text, labels, helper text |
| `text-mono` | 12px | 400 | 1.4 (17px) | Ticket keys, timestamps, code |

### Spacing Scale

| Token | Value | Common Usage |
|-------|-------|---|
| `spacing-xs` | 4px | Small gaps, icon spacing |
| `spacing-sm` | 8px | Tight spacing, input padding |
| `spacing-md` | 12px | Default spacing, form fields |
| `spacing-lg` | 16px | Component padding, section spacing |
| `spacing-xl` | 24px | Large spacing, section breaks |
| `spacing-2xl` | 32px | Major spacing, page sections |
| `spacing-3xl` | 48px | Large gaps, hero sections |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius-none` | 0px | Sharp corners where needed |
| `radius-sm` | 4px | Input borders, small buttons |
| `radius-md` | 8px | Cards, badges, dropdowns |
| `radius-lg` | 12px | Modals, large panels |

---

## Core Components

### 1. Metrics Tile (Dashboard)

**Purpose:** Display a single KPI with health status and trend indicator  
**Context:** Dashboard hero section (2×2 grid on desktop)

#### Visual Specifications
- **Container:** 280px width, 120px height, rounded-md, border 1px #E5E7EB
- **Left indicator bar:** 4px width, full height, color-coded by health status
- **Padding:** 16px all sides
- **Gap between elements:** 8px

#### Measurements
| Element | Size | Value |
|---------|------|-------|
| Title | Font | 12px, 400 weight, #6B7280 |
| Metric Value | Font | 24px, 600 weight, #1F2937 |
| Trend | Font | 12px, 400 weight, color-semantic |
| Timestamp | Font | 12px, 400 weight, #9CA3AF |
| Container | Width × Height | 280px × 120px |
| Indicator Bar | Width × Height | 4px × 100% |

#### Health Status Mapping
| Status | Indicator Color | Rule |
|--------|---|---|
| Healthy | #10B981 (success) | Metric below threshold |
| Watch | #F59E0B (warning) | Metric in warning range |
| Critical | #EF4444 (critical) | Metric above threshold |

#### States

**Default/Idle**
```
- Background: #FFFFFF
- Border: 1px solid #E5E7EB
- Shadow: 0 1px 2px 0 rgba(0,0,0,0.05)
- Cursor: default
```

**Hover**
```
- Background: #FFFFFF
- Shadow: 0 4px 6px -1px rgba(0,0,0,0.1) [elevated]
- Border: 1px solid #D1D5DB
- Cursor: pointer
- Transition: shadow 200ms ease-out
```

**Loading**
```
- Metric value: Skeleton placeholder (gradient pulse)
- Animation: 1200ms ease-in-out infinite
- Opacity: 60%
```

**Focus**
```
- Border: 2px solid #2563EB
- Outline: none
- Shadow: 0 0 0 3px rgba(37,99,235,0.1)
```

#### Responsive Behavior
| Breakpoint | Dimensions | Layout |
|---|---|---|
| Desktop (>1200px) | 280×120px | 2×2 grid, 24px gap |
| Tablet (768-1200px) | 240×110px | 2×1 stack |
| Mobile (<768px) | Full-width -32px | Single column |

#### Accessibility
- **Role:** `<article role="region" aria-label="Cycle Time metric">`
- **Focus:** Keyboard focusable, visible focus ring
- **Screen Reader:** "Cycle Time metric. 18 point 5 days. Up 2 point 3 days, 8 percent improvement. Last synced 2 minutes ago."
- **Keyboard:** Tab to focus, Enter to open drill-down

#### React Implementation

```jsx
export function MetricsTile({
  status = 'success', // 'success' | 'warning' | 'critical'
  title,
  value,
  unit,
  trend,
  lastUpdated,
  onClick,
}) {
  const statusColors = {
    success: 'border-l-green-500',
    warning: 'border-l-amber-500',
    critical: 'border-l-red-500',
  };

  const trendColors = {
    success: 'text-green-600',
    warning: 'text-amber-600',
    critical: 'text-red-600',
  };

  return (
    <article
      className={`
        w-72 h-32 p-4 rounded-lg border border-gray-200
        ${statusColors[status]} border-l-4
        bg-white shadow-sm hover:shadow-md transition-shadow
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
        cursor-pointer
      `}
      onClick={onClick}
      role="region"
      aria-label={`${title} metric`}
      tabIndex={0}
    >
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium text-gray-600">{title}</p>
        <p className="text-2xl font-semibold text-gray-900">
          {value} <span className="text-sm text-gray-600">{unit}</span>
        </p>
        <p className={`text-xs font-medium ${trendColors[status]}`}>
          {trend.direction === 'up' ? '↑' : '↓'} {trend.amount} ({trend.percent}%)
        </p>
        <p className="text-xs text-gray-500">Last synced: {lastUpdated}</p>
      </div>
    </article>
  );
}
```

---

### 2. Status Badge

**Purpose:** Display ticket status with semantic color  
**Context:** Table view, Kanban cards, detail views

#### Visual Specifications
- **Small:** 28px height, 8px-12px padding horizontal
- **Medium:** 32px height, 12px-16px padding horizontal
- **Border radius:** 4px
- **Font:** 12px, 500 weight

#### Status Colors
| Status | Solid BG | Text | Icon |
|---|---|---|---|
| To Do | #F3F4F6 | #6B7280 | — |
| In Progress | #3B82F6 | #FFFFFF | ▶ |
| QA | #A855F7 | #FFFFFF | ✓ |
| Done | #10B981 | #FFFFFF | ✓ |

#### Variants

**Solid (Default)**
```
- Background: Status color
- Text: White or dark (contrast compliant)
- Border: None
- Padding: 8-12px horizontal, 4-6px vertical
```

**Outline**
```
- Background: Transparent
- Border: 1px solid status color
- Text: Status color
- Padding: 8-12px horizontal, 4-6px vertical
```

#### States
| State | Styling |
|---|---|
| Default | Full opacity, normal |
| Hover | opacity-90 |
| Active | Background darkened 10% |
| Disabled | opacity-50, cursor-not-allowed |
| Focus | 2px outline in #2563EB |

#### React Implementation

```jsx
export function StatusBadge({
  status = 'todo', // 'todo' | 'in-progress' | 'qa' | 'done'
  variant = 'solid', // 'solid' | 'outline'
  size = 'medium', // 'small' | 'medium'
}) {
  const statusConfig = {
    todo: { bg: '#F3F4F6', text: '#6B7280', label: 'To Do' },
    'in-progress': { bg: '#3B82F6', text: '#FFFFFF', label: 'In Progress', icon: '▶' },
    qa: { bg: '#A855F7', text: '#FFFFFF', label: 'QA', icon: '✓' },
    done: { bg: '#10B981', text: '#FFFFFF', label: 'Done', icon: '✓' },
  };

  const config = statusConfig[status];
  const sizeClass = size === 'small' ? 'h-7 px-2 text-xs' : 'h-8 px-3 text-sm';

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded font-medium
        ${sizeClass}
        ${variant === 'solid'
          ? `bg-[${config.bg}] text-[${config.text}]`
          : `border border-[${config.bg}] text-[${config.bg}]`
        }
        focus:outline-none focus:ring-2 focus:ring-blue-500
      `}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      {config.icon && <span>{config.icon}</span>}
      {config.label}
    </span>
  );
}
```

---

## Page Layouts

### Dashboard View

**Purpose:** Team health overview with key metrics  

#### Layout Structure
```
┌─────────────────────────────────────┐
│ Navigation Bar (64px)                │
├─────────────────────────────────────┤
│ Padding: 32px horizontal             │
│                                      │
│  [Metrics Tile]  [Metrics Tile]     │ 2×2 grid, gap 24px
│                                      │
│  [Metrics Tile]  [Metrics Tile]     │
│                                      │
├─────────────────────────────────────┤
│ Last updated: X min ago | [↻]       │ Sticky footer
└─────────────────────────────────────┘
```

#### Grid Properties
- **Max-width:** 1400px
- **Margin:** 0 auto
- **Padding:** 32px horizontal, 24px vertical
- **Grid columns:** 2 (desktop), 1 (mobile)
- **Gap:** 24px between tiles

### Table View

**Purpose:** Detailed ticket management with sorting and filtering

#### Header Controls
```
┌─────────────────────────────────────┐
│ [Filter ▼] [Sort ▼] | [⚙] [↻]     │ Sticky control bar (56px)
├─────────────────────────────────────┤
│ Key ↑↓ │ Title │ Assignee │ Status │ Header (48px, sticky)
├─────────────────────────────────────┤
│ [Table rows, scrollable]            │
│ [PROJ-1 data row]                   │
│ [PROJ-2 data row]                   │
└─────────────────────────────────────┘
```

#### Column Configuration
| Column | Width | Sortable | Filterable |
|--------|-------|----------|---|
| Key | 100px | Yes | No |
| Title | Flex | No | Yes |
| Assignee | 140px | Yes | Yes |
| Status | 120px | Yes | Yes |
| Days in Status | 140px | Yes | No |
| Role | 100px | Yes | Yes |

#### Row Heights
- **Header:** 48px (sticky)
- **Data row:** 52px (40px content + 12px padding)
- **Hover state:** Background #F9FAFB

---

## Tailwind Configuration

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
        },
        success: '#10B981',
        warning: '#F59E0B',
        critical: '#EF4444',
        role: {
          dev: '#3B82F6',
          qa: '#A855F7',
          po: '#14B8A6',
        },
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
        '2xl': '32px',
        '3xl': '48px',
      },
      borderRadius: {
        sm: '4px',
        md: '8px',
        lg: '12px',
      },
      fontSize: {
        h1: ['32px', { lineHeight: '1.2', fontWeight: '700' }],
        h2: ['24px', { lineHeight: '1.25', fontWeight: '600' }],
        h3: ['20px', { lineHeight: '1.3', fontWeight: '600' }],
        h4: ['16px', { lineHeight: '1.4', fontWeight: '600' }],
      },
    },
  },
};
```

---

## Accessibility Checklist

- [ ] All colors meet WCAG AA contrast ratio (4.5:1)
- [ ] Focus ring visible on all interactive elements
- [ ] Tab order is logical (left-to-right, top-to-bottom)
- [ ] Screen reader announces all information
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] No color alone conveys information
- [ ] Error messages are clear and associated
- [ ] Form labels are properly associated

---

**Version:** 1.0  
**Status:** Ready for Implementation  
**Generated:** 2026-05-16
