import { GoogleGenAI } from "@google/genai";

// Initialize the client with the API key from environment variables
// Note: In a real production app, ensure this key is not exposed if not intended for public client-side usage.
export const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

// Helper to check if user needs to select a key for paid features (Veo/Pro Image)
export const checkApiKeySelection = async (): Promise<boolean> => {
  if (typeof window !== 'undefined' && (window as any).aistudio) {
    const hasKey = await (window as any).aistudio.hasSelectedApiKey();
    if (!hasKey) {
       await (window as any).aistudio.openSelectKey();
       return true;
    }
    return true;
  }
  return true; // Fallback for standard environments assuming process.env.API_KEY is valid
};

// Global type definition for AI Studio helper
declare global {
  interface Window {
    // aistudio is likely defined by the environment/libraries with specific types (AIStudio),
    // so we remove the conflicting 'any' declaration and access it via type assertion above.
    webkitAudioContext: typeof AudioContext;
  }
}