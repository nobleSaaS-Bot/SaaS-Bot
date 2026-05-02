export function getSubdomain(): string | null {
  const hostname = window.location.hostname;
  const parts = hostname.split(".");
  if (parts.length >= 3) {
    return parts[0];
  }
  return null;
}

export function buildStoreUrl(subdomain: string, baseDomain = "yoursaasplatform.com"): string {
  return `https://${subdomain}.${baseDomain}`;
}

export function isStoreDomain(): boolean {
  const subdomain = getSubdomain();
  const knownSubdomains = ["www", "app", "dashboard", "api"];
  return !!subdomain && !knownSubdomains.includes(subdomain);
}
