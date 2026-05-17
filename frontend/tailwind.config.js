import { createRequire } from 'node:module';

// Re-use the workspace design-token config so colors/spacing/typography stay
// in sync with DESIGN-SYSTEM-Guide.md. Only `content` is local to this app.
const require = createRequire(import.meta.url);
const shared = require('../tailwind.config.js');

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: shared.theme,
  plugins: shared.plugins ?? [],
};
