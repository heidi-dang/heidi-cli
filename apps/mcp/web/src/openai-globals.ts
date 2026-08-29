import { useSyncExternalStore } from "react";

export type ChatGptDisplayMode = "inline" | "pip" | "fullscreen";

type OpenAiSetGlobalsEvent = CustomEvent<{
  globals?: {
    displayMode?: ChatGptDisplayMode;
  };
}>;

type OpenAiRuntime = {
  displayMode?: ChatGptDisplayMode;
};

const SET_GLOBALS_EVENT = "openai:set_globals";

function runtime(): OpenAiRuntime | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { openai?: OpenAiRuntime }).openai;
}

function subscribeDisplayMode(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const handler = (event: Event) => {
    const displayMode = (event as OpenAiSetGlobalsEvent).detail?.globals?.displayMode;
    if (displayMode !== undefined) onChange();
  };
  window.addEventListener(SET_GLOBALS_EVENT, handler, { passive: true });
  return () => window.removeEventListener(SET_GLOBALS_EVENT, handler);
}

function displayModeSnapshot(): ChatGptDisplayMode {
  return runtime()?.displayMode ?? "inline";
}

export function useOpenAiDisplayMode(): ChatGptDisplayMode {
  return useSyncExternalStore(subscribeDisplayMode, displayModeSnapshot, () => "inline");
}
