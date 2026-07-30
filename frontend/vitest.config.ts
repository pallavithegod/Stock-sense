import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    exclude: ['dist/**', 'node_modules/**', 'tests/e2e/**'],
    include: ['tests/unit/**/*.{spec,test}.{ts,tsx}'],
    setupFiles: './tests/setup.ts',
  },
})
