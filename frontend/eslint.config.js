import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // signal-flow.js is vendored verbatim from redhawkliger/signal-flow; re-synced by copying, never edited here.
  globalIgnores(['dist', 'src/lib/signal-flow/signal-flow.js']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [js.configs.recommended, reactHooks.configs.flat.recommended, reactRefresh.configs.vite],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
  {
    files: ['**/*.test.{js,jsx}', 'src/test-setup.js'],
    languageOptions: { globals: { ...globals.browser, ...globals.node, ...globals.vitest } },
  },
])
