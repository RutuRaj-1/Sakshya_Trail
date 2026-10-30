/**
 * SakshyaTrail Firebase Client SDK Initialization
 * SIH Problem Statement: 26265
 * 
 * Configured via Vite environment variables (VITE_FIREBASE_*) with
 * resilient fallbacks to official SIH 26265 project credentials.
 */
import { initializeApp, getApps, getApp, type FirebaseApp } from "firebase/app";
import { getAnalytics, isSupported, type Analytics } from "firebase/analytics";
import { getFirestore, type Firestore } from "firebase/firestore";
import { getStorage, type FirebaseStorage } from "firebase/storage";
import { getAuth, type Auth } from "firebase/auth";

export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyAqqvkCHZutYjILCXT6Q-SzvGn88holAps",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "sih-26265-fdr.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "sih-26265-fdr",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "sih-26265-fdr.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "2017740195",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:2017740195:web:ed1355f7fd21cd3ad80616",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "G-YYNCY2BVT9",
};

// Initialize or retrieve existing Firebase App instance
export const app: FirebaseApp = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();
export const firebaseApp: FirebaseApp = app;

// Firebase Analytics (supported conditionally in browser environments)
export const analyticsPromise: Promise<Analytics | null> =
  typeof window !== "undefined"
    ? isSupported()
        .then((supported) => (supported ? getAnalytics(app) : null))
        .catch(() => null)
    : Promise.resolve(null);

// Modular service instances (ready for Firestore, Cloud Storage, or Auth if needed)
export const firestore: Firestore = getFirestore(app);
export const storage: FirebaseStorage = getStorage(app);
export const auth: Auth = getAuth(app);

export default app;
