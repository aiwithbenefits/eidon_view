import { SearchFilters, ActiveFilter } from "@/types";

// Extract filter parameters from a search query string
export function parseSearchQuery(query: string): SearchFilters {
  const filters: SearchFilters = { query: "" };
  
  // Regular expressions for filter extraction
  const datePattern = /date:([^\s]+)/i;
  const timePattern = /time:([^\s]+)/i;
  const titlePattern = /title:([^\s]+|"[^"]+"|'[^']+')/i;
  const urlPattern = /url:([^\s]+|"[^"]+"|'[^']+')/i;
  
  // Extract date
  const dateMatch = query.match(datePattern);
  if (dateMatch) {
    filters.date = dateMatch[1].replace(/["']/g, '');
    query = query.replace(dateMatch[0], '');
  }
  
  // Extract time
  const timeMatch = query.match(timePattern);
  if (timeMatch) {
    filters.time = timeMatch[1].replace(/["']/g, '');
    query = query.replace(timeMatch[0], '');
  }
  
  // Extract title
  const titleMatch = query.match(titlePattern);
  if (titleMatch) {
    filters.title = titleMatch[1].replace(/^["'](.*)["']$/, '$1');
    query = query.replace(titleMatch[0], '');
  }
  
  // Extract URL
  const urlMatch = query.match(urlPattern);
  if (urlMatch) {
    filters.url = urlMatch[1].replace(/^["'](.*)["']$/, '$1');
    query = query.replace(urlMatch[0], '');
  }
  
  // The remaining text is the main query
  filters.query = query.trim();
  
  return filters;
}

// Convert filters to a list of active filters for display
export function filtersToActiveFilters(filters: SearchFilters): ActiveFilter[] {
  const activeFilters: ActiveFilter[] = [];
  
  if (filters.date) {
    activeFilters.push({
      key: 'date',
      value: filters.date,
      display: `date: ${filters.date}`
    });
  }
  
  if (filters.time) {
    activeFilters.push({
      key: 'time',
      value: filters.time,
      display: `time: ${filters.time}`
    });
  }
  
  if (filters.title) {
    activeFilters.push({
      key: 'title',
      value: filters.title,
      display: `title: ${filters.title}`
    });
  }
  
  if (filters.url) {
    activeFilters.push({
      key: 'url',
      value: filters.url,
      display: `url: ${filters.url}`
    });
  }
  
  return activeFilters;
}

// Combine filters into a search URL string
export function filtersToSearchParams(filters: SearchFilters): string {
  const params = new URLSearchParams();
  
  if (filters.query) params.append('query', filters.query);
  if (filters.date) params.append('date', filters.date);
  if (filters.time) params.append('time', filters.time);
  if (filters.title) params.append('title', filters.title);
  if (filters.url) params.append('url', filters.url);
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  
  return params.toString();
}
