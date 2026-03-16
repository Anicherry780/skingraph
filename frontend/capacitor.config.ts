import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.skingraph.app',
  appName: 'SkinGraph',
  webDir: 'dist',
  server: {
    // Load directly from the live production site — always up-to-date,
    // has all env vars baked in by Cloudflare, no local rebuild needed.
    url: 'https://skin.anirudhdev.com',
    cleartext: false,
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      backgroundColor: '#f9fafb',
      showSpinner: false,
    },
  },
};

export default config;
