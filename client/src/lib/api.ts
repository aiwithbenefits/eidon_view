import { queryClient } from "./queryClient";

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown,
): Promise<Response> {
  const res = await fetch(url, {
    method,
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }

  return res;
}

export async function getTimeline(date?: string, page = 1, limit = 12) {
  try {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    if (page) params.append('page', page.toString());
    if (limit) params.append('limit', limit.toString());
    
    const res = await apiRequest('GET', `/api/timeline?${params.toString()}`);
    return await res.json();
  } catch (error) {
    console.error('Error fetching timeline:', error);
    throw error;
  }
}

export async function getScreenshot(id: number) {
  try {
    const res = await apiRequest('GET', `/api/screenshots/${id}`);
    return await res.json();
  } catch (error) {
    console.error('Error fetching screenshot:', error);
    throw error;
  }
}

export async function searchEntries(queryParams: Record<string, string | number>) {
  try {
    const params = new URLSearchParams();
    
    Object.entries(queryParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString());
      }
    });
    
    const res = await apiRequest('GET', `/api/search?${params.toString()}`);
    return await res.json();
  } catch (error) {
    console.error('Error searching entries:', error);
    throw error;
  }
}

export async function getCaptureStatus() {
  try {
    const res = await apiRequest('GET', '/api/capture/status');
    return await res.json();
  } catch (error) {
    console.error('Error fetching capture status:', error);
    throw error;
  }
}

export async function toggleCapture() {
  try {
    const res = await apiRequest('POST', '/api/capture/toggle');
    return await res.json();
  } catch (error) {
    console.error('Error toggling capture:', error);
    throw error;
  }
}
