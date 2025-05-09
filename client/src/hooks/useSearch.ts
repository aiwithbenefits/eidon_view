import { useState, useCallback, useMemo } from "react";
import { SearchFilters, ActiveFilter } from "@/types";
import { parseSearchQuery, filtersToActiveFilters } from "@/lib/filters";

export function useSearch() {
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(12);
  
  // Parse the search query to extract filters
  const searchFilters = useMemo(() => {
    const filters = parseSearchQuery(searchQuery);
    filters.page = page;
    filters.limit = limit;
    return filters;
  }, [searchQuery, page, limit]);
  
  // Convert filters to active filters for display
  const activeFilters = useMemo(() => {
    return filtersToActiveFilters(searchFilters);
  }, [searchFilters]);
  
  // Add a new filter
  const addFilter = useCallback((key: keyof SearchFilters, value: string) => {
    setSearchQuery(prev => {
      // Remove any existing filter with the same key
      const regex = new RegExp(`${key}:[^\\s]+`, 'g');
      const cleaned = prev.replace(regex, '').trim();
      
      // Add new filter
      return `${cleaned} ${key}:${value}`.trim();
    });
    setPage(1); // Reset to first page when adding a filter
  }, []);
  
  // Remove a filter
  const removeFilter = useCallback((filter: ActiveFilter) => {
    setSearchQuery(prev => {
      const regex = new RegExp(`${filter.key}:${filter.value.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')}\\s*`, 'g');
      return prev.replace(regex, '').trim();
    });
    setPage(1); // Reset to first page when removing a filter
  }, []);
  
  // Remove all filters
  const removeAllFilters = useCallback(() => {
    setSearchQuery("");
    setPage(1);
  }, []);
  
  return {
    searchQuery,
    searchFilters,
    activeFilters,
    setSearchQuery,
    setPage,
    setLimit,
    addFilter,
    removeFilter,
    removeAllFilters
  };
}
