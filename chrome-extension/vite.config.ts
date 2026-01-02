import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        background: resolve(__dirname, 'src/background/index.ts'),
        content: resolve(__dirname, 'src/content/inject.ts'),
        dashboard: resolve(__dirname, 'src/dashboard/App.tsx'),
      },
      output: {
        entryFileNames: (chunkInfo) => {
          return `${chunkInfo.name}/${chunkInfo.name}.js`;
        },
      },
    },
  },
});

