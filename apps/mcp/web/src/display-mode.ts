export type DisplayMode = "inline" | "fullscreen" | "pip";

export type DisplayModeBridge = {
  requestDisplayMode?: (input: { mode: DisplayMode }) => Promise<{ mode?: DisplayMode } | void>;
};

export type DisplayModeRequestOptions = {
  userActivated?: boolean;
};

function currentUserActivation(): boolean {
  if (typeof navigator === "undefined") return true;
  const activation = (navigator as Navigator & { userActivation?: { isActive?: boolean } }).userActivation;
  return activation?.isActive !== false;
}

export async function requestHostDisplayMode(
  bridge: DisplayModeBridge | undefined,
  mode: DisplayMode,
  options?: DisplayModeRequestOptions,
): Promise<DisplayMode | null> {
  if (!bridge?.requestDisplayMode) return null;
  const userActivated = options?.userActivated ?? currentUserActivation();
  if (!userActivated) return null;
  const result = await bridge.requestDisplayMode({ mode });
  return result && typeof result === "object" && typeof result.mode === "string"
    ? result.mode
    : mode;
}
