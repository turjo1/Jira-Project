# Design System Handoff - Jira Team Performance Analytics

## 📦 What's Included

This design handoff package contains everything needed to implement the Jira Team Performance Analytics UI using React and Tailwind CSS.

### Files in This Package

| File | Purpose | Use When |
|------|---------|----------|
| **DESIGN-SYSTEM-Guide.md** | Complete design system overview | Starting implementation or needing design principles |
| **DESIGN-HANDOFF-Components.md** | Detailed component specifications | Building a specific component |
| **tailwind.config.js** | Pre-configured Tailwind theme | Setting up the project |
| **PRD-Team-Performance-Analytics.md** | Product requirements | Needing context on what to build |

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install -D tailwindcss postcss autoprefixer
npm install inter
```

### 2. Copy Tailwind Config
Copy `tailwind.config.js` to your project root. Includes:
- Color tokens (primary, success, warning, critical, roles)
- Typography scale (H1-H4, body text, monospace)
- Spacing scale (xs, sm, md, lg, xl, 2xl, 3xl)
- Border radius and shadows

### 3. Import Design Font
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 4. Start Building Components
Open `DESIGN-HANDOFF-Components.md` for detailed specifications.

---

## 🎨 Design Tokens Quick Reference

### Colors
```
Primary:    #2563EB (CTAs, links, focus)
Success:    #10B981 (Healthy, good)
Warning:    #F59E0B (Watch, attention)
Critical:   #EF4444 (Errors, critical)

Dev:        #3B82F6 (Developer)
QA:         #A855F7 (Quality Assurance)
PO:         #14B8A6 (Product Owner)
```

### Spacing (4px base)
```
xs: 4px  |  md: 12px  |  xl: 24px   |  3xl: 48px
sm: 8px  |  lg: 16px  |  2xl: 32px
```

### Typography
```
H1: 32px/700  |  Body: 14px/400  |  Mono: 12px/400
H2: 24px/600  |  Body-sm: 12px/400
H3: 20px/600  |  H4: 16px/600
```

---

## 📋 Core Components

### 1. Metrics Tile (Dashboard)
Display KPI with health status. See `DESIGN-HANDOFF-Components.md` Section 1.

```jsx
<MetricsTile
  status="success"
  title="Cycle Time"
  value={18.5}
  unit="days"
  trend={{ direction: 'up', amount: 2.3, percent: 8 }}
  lastUpdated="2 min ago"
  onClick={handleDrill Down}
/>
```

**Key specs:** 280×120px, color-coded border, responsive

### 2. Status Badge
Display ticket status. See `DESIGN-HANDOFF-Components.md` Section 2.

```jsx
<StatusBadge status="qa" variant="solid" size="medium" />
```

**Key specs:** Solid/outline variants, small/medium sizes, status colors

### 3. Data Table
Sortable, filterable tickets. See `DESIGN-HANDOFF-Components.md` Section 3.

**Key specs:** 6+ columns, sortable headers, sticky, responsive

### 4. Developer Detail Modal
Performance drill-down. See `DESIGN-HANDOFF-Components.md` Section 4.

**Key specs:** 600px width, metrics + ticket history, modal dialog pattern

---

## 📐 Layout Patterns

### Dashboard
2×2 metric grid, responsive to 1 column on mobile

### Table View
Sticky header, sortable columns, configurable visibility

### Kanban Board
4 fixed columns (To Do, In Progress, QA, Done), horizontal scroll on mobile

---

## ♿ Accessibility Checklist

- [ ] Colors meet WCAG AA (4.5:1 contrast)
- [ ] Focus ring visible on all interactive elements
- [ ] Tab order is logical
- [ ] All buttons have accessible labels
- [ ] Form inputs have associated labels
- [ ] Modal has role="dialog"
- [ ] Live regions for dynamic updates
- [ ] No color alone conveys information

---

## 📱 Responsive Breakpoints

| Size | Width | Layout |
|------|-------|--------|
| Mobile | <640px | Single column |
| Tablet | 640-1024px | 2-column |
| Desktop | >1024px | Full layout |

---

## 💡 Implementation Tips

### 1. Use Tailwind for All Styles
```jsx
// Good
className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"

// Avoid
style={{ backgroundColor: '#2563EB' }}
```

### 2. Always Include Focus States
```jsx
className="... focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
```

### 3. Use Skeleton Loaders for Loading
```jsx
{isLoading ? (
  <div className="h-32 bg-gray-200 rounded animate-pulse" />
) : (
  <MetricsTile {...props} />
)}
```

### 4. Lazy Load Large Tables
Use virtualization for 100+ rows

### 5. Test Accessibility Early
Run axe DevTools in development

---

## 🔍 Common Patterns

### Container with Responsive Padding
```jsx
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  {/* Content */}
</div>
```

### Grid Layout
```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  <MetricsTile {...props} />
</div>
```

### Modal Focus Management
```jsx
const modalRef = useRef(null);

useEffect(() => {
  if (isOpen) {
    modalRef.current?.focus();
  }
}, [isOpen]);
```

---

## 📚 Documentation Map

```
DESIGN-HANDOFF-README.md (you are here)
├─ For component details
│  └─ DESIGN-HANDOFF-Components.md (sections 1-4)
├─ For design principles
│  └─ DESIGN-SYSTEM-Guide.md
├─ For project context
│  └─ PRD-Team-Performance-Analytics.md
└─ For Tailwind tokens
   └─ tailwind.config.js
```

---

## 🎯 Implementation Order

1. **Setup** — Install Tailwind, copy config, set up navigation
2. **Core Components** — MetricsTile, StatusBadge, buttons
3. **Dashboard** — Metric grid, real-time sync
4. **Table View** — Columns, sorting, filtering
5. **Kanban View** — Board layout, developer cards
6. **Details & Testing** — Modal, accessibility, responsive

---

## 🧪 Testing Checklist

### Functionality
- [ ] All views load without errors
- [ ] Data updates every 5 minutes
- [ ] Sorting/filtering work
- [ ] Modal opens/closes

### Responsive
- [ ] Desktop: all features visible
- [ ] Tablet: layout adjusts, spacing reduces
- [ ] Mobile: single column, horizontal scroll for tables

### Accessibility
- [ ] axe DevTools: 0 violations
- [ ] Tab navigation works
- [ ] Focus ring visible
- [ ] Screen reader compatible

---

## 🚨 Common Pitfalls

❌ Don't use arbitrary Tailwind values (`w-[337px]`)  
✓ Use scale tokens (`w-80`, `h-40`)

❌ Don't skip focus states  
✓ Include `focus-visible:ring-2 focus-visible:ring-blue-500`

❌ Don't use spinners for loading  
✓ Use skeleton loaders with `animate-pulse`

❌ Don't hardcode colors  
✓ Use Tailwind color classes (`text-primary-600`)

---

## ✅ Handoff Contents

- [x] Component specifications with measurements
- [x] Design token system (colors, typography, spacing)
- [x] React component code examples
- [x] Tailwind CSS configuration (ready to copy)
- [x] Accessibility guidelines (WCAG AA)
- [x] Responsive design patterns
- [x] Interactive state specifications
- [x] Layout patterns for all views
- [x] Implementation guide

---

**Status:** ✅ Ready for Implementation  
**Last Updated:** 2026-05-16  
**Tech Stack:** React + Tailwind CSS  
**Accessibility:** WCAG 2.1 AA

---

### Next Steps

1. Read `DESIGN-SYSTEM-Guide.md` for design principles
2. Install Tailwind and copy `tailwind.config.js`
3. Reference `DESIGN-HANDOFF-Components.md` while building
4. Test with axe DevTools early and often
5. Check `PRD-Team-Performance-Analytics.md` for feature context

Happy building! 🚀
