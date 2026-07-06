// Lightweight device fingerprint for anti-abuse rate limiting on signup.
// Not a tracking/ad fingerprint: cached locally, sent only on registration.

async function sha256(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function canvasSignature(): string {
  try {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return "";
    ctx.textBaseline = "top";
    ctx.font = "14px 'Arial'";
    ctx.fillText("sb-device-check", 2, 2);
    return canvas.toDataURL();
  } catch {
    return "";
  }
}

export async function getDeviceFingerprint(): Promise<string> {
  if (typeof window === "undefined") return "";
  const cached = localStorage.getItem("sb_fp");
  if (cached) return cached;

  const parts = [
    navigator.userAgent,
    navigator.language,
    String(navigator.hardwareConcurrency || ""),
    `${screen.width}x${screen.height}x${screen.colorDepth}`,
    Intl.DateTimeFormat().resolvedOptions().timeZone,
    canvasSignature(),
  ].join("||");

  const fp = await sha256(parts);
  localStorage.setItem("sb_fp", fp);
  return fp;
}
