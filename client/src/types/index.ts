export interface ScreenshotEntry {
  id: number;
  timestamp: number;
  title: string | null;
  appName: string | null;
  windowTitle: string | null;
  url: string | null;
  extractedText: string | null;
  imagePath: string;
}

export interface TimelineResponse {
  entries: ScreenshotEntry[];
  hasMore: boolean;
  currentDate: string;
}

export interface SearchFilters {
  query?: string;
  date?: string;
  time?: string;
  title?: string;
  url?: string;
  page?: number;
  limit?: number;
}

export interface ActiveFilter {
  key: keyof SearchFilters;
  value: string;
  display: string;
}

export interface CaptureStatus {
  active: boolean;
}
