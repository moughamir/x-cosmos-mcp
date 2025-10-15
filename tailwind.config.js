/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./views/admin/templates/**/*.html",
    "./views/admin/src/**/*.{ts,js}",
    "./views/admin/src/**/*.ts"
  ],
  safelist: [
    // Common utility classes used in components
    'container',
    'mx-auto',
    'px-3',
    'py-2',
    'mb-4',
    'text-xl',
    'text-2xl',
    'font-bold',
    'bg-blue-500',
    'bg-blue-700',
    'bg-slate-900',
    'bg-slate-800',
    'bg-slate-700',
    'bg-slate-50',
    'text-white',
    'border-b',
    'rounded',
    'hover:bg-blue-700',
    'transition-colors',
    'flex',
    'justify-between',
    'items-center',
    'gap-4',
    'p-4',
    'min-w-full',
    'bg-white',
    'py-1',
    'text-sm',
    'px-1',
    // Add more as needed
  ],
  theme: {
    extend: {
      colors: {
        'slate': {
          50: '#f8fafc',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        }
      }
    },
  },
  plugins: [],
}
