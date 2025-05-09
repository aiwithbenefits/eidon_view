import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import SearchBar from "@/components/SearchBar";
import ActiveFilters from "@/components/ActiveFilters";
import Timeline from "@/components/Timeline";
import TimelineHeader from "@/components/TimelineHeader";
import { SearchFilters } from "@/types";
import { format } from "date-fns";
import { useSearch } from "@/hooks/useSearch";

export default function Home() {
  const [currentDate, setCurrentDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [page, setPage] = useState(1);
  
  const { 
    searchQuery, 
    searchFilters, 
    setSearchQuery, 
    addFilter, 
    removeFilter, 
    removeAllFilters 
  } = useSearch();
  
  // Create query key based on filters
  const queryKey = searchFilters.query 
    ? ['/api/search', searchFilters] 
    : ['/api/timeline', { date: currentDate, page }];
  
  // Fetch timeline data
  const { data, isLoading, isError } = useQuery({
    queryKey,
    refetchOnWindowFocus: false
  });
  
  const handleDateChange = (direction: 'prev' | 'next') => {
    const date = new Date(currentDate);
    if (direction === 'prev') {
      date.setDate(date.getDate() - 1);
    } else {
      date.setDate(date.getDate() + 1);
    }
    setCurrentDate(format(date, 'yyyy-MM-dd'));
    setPage(1);
  };
  
  const loadMore = () => {
    setPage(prev => prev + 1);
  };
  
  const timelineEntries = data?.entries || [];
  const hasMore = data?.hasMore || false;
  const dateLabel = data?.currentDate 
    ? format(new Date(data.currentDate), "MMMM d, yyyy") 
    : format(new Date(), "MMMM d, yyyy");
  
  const isToday = format(new Date(), 'yyyy-MM-dd') === currentDate;
  const dateNavigationLabel = isToday ? `Today, ${dateLabel}` : dateLabel;
  
  return (
    <div className="w-full">
      <TimelineHeader 
        title="Timeline" 
        date={dateNavigationLabel} 
        onNavigate={handleDateChange} 
      />
      
      <Timeline 
        entries={timelineEntries} 
        isLoading={isLoading} 
        isError={isError} 
        hasMore={hasMore} 
        onLoadMore={loadMore} 
      />
    </div>
  );
}
