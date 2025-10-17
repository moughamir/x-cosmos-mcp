const getApiUrl = () => {
  const url = process.env.NEXT_PUBLIC_API_URL;
  // On the server, we can use the internal docker URL if NEXT_PUBLIC_API_URL is not set
  if (typeof window === 'undefined' && !url) {
    return process.env.BACKEND_API_URL || 'http://localhost:8000';
  }
  if (!url) {
    // On the client, we fall back to the relative path
    return '';
  }
  return url;
};

export async function fetchApi(path: string, options?: RequestInit): Promise<Response> {
  const apiUrl = getApiUrl();
  const fullUrl = path.startsWith('http') ? path : `${apiUrl}${path}`;

  let lastError: Error | null = null;

  // Retry logic to handle development server race conditions.
  for (let i = 0; i < 3; i++) {
    try {
      const response = await fetch(fullUrl, options);
      // Don't retry on client-side errors (4xx) or successful responses
      if (response.ok || (response.status >= 400 && response.status < 500)) {
        return response;
      }
      // Retry on server-side errors (5xx)
      lastError = new Error(`Server error: ${response.status}`);
    } catch (e) {
      lastError = e as Error;
    }

    // Only retry on the server-side during the build/SSR phase
    if (typeof window === 'undefined') {
      await new Promise(res => setTimeout(res, 1500)); // Wait 1.5s before retrying
    } else {
      break; // Don't retry on the client-side
    }
  }
  throw lastError || new Error('API fetch failed after multiple retries.');
}