import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.skingraph.app',
  appName: 'SkinGraph',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    // In production, serve the local bundle (offline-capable)
    // For dev, you can set url: 'http://YOUR_LOCAL_IP:5173' to live reload
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
