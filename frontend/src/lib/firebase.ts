/**
 * Firebase Client Configuration
 * Initialized with official SIH 26265 credentials
 */
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";

export const firebaseConfig = {
  apiKey: "AIzaSyAqqvkCHZutYjILCXT6Q-SzvGn88holAps",
  authDomain: "sih-26265-fdr.firebaseapp.com",
  projectId: "sih-26265-fdr",
  storageBucket: "sih-26265-fdr.firebasestorage.app",
  messagingSenderId: "2017740195",
  appId: "1:2017740195:web:ed1355f7fd21cd3ad80616",
  measurementId: "G-YYNCY2BVT9",
};

// Initialize Firebase singleton
export const firebaseApp = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();

// Conditionally initialize analytics in browser environments
export const analyticsPromise = isSupported().then((supported) =>
  supported ? getAnalytics(firebaseApp) : null
);
