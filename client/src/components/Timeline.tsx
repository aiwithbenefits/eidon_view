import { Fragment } from "react";
import TimelineEntry from "./TimelineEntry";
import { Button } from "@/components/ui/button";
import { ChevronDown } from "lucide-react";
import { ScreenshotEntry } from "@/types";
import { Skeleton } from "@/components/ui/skeleton";

interface TimelineProps {
  entries: ScreenshotEntry[];
  isLoading: boolean;
  isError: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
}

export default function Timeline({ entries, isLoading, isError, hasMore, onLoadMore }: TimelineProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="glass-card overflow-hidden">
            <Skeleton className="w-full h-48" />
            <div className="p-3">
              <Skeleton className="h-5 w-3/4 mb-2" />
              <Skeleton className="h-4 w-1/2 mb-2" />
              <Skeleton className="h-4 w-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }
  
  if (isError) {
    return (
      <div className="text-center py-12 glass-container p-8 mx-auto max-w-md">
        <h2 className="text-lg font-medium text-red-600 dark:text-red-400 mb-2">Error loading timeline</h2>
        <p className="text-blue-700 dark:text-blue-300 mb-4">Failed to load timeline entries.</p>
        <Button 
          variant="outline"
          className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-white/30 dark:border-gray-700/30 text-blue-700 dark:text-blue-300 hover:bg-white/70 dark:hover:bg-gray-700/70"
          onClick={() => window.location.reload()}
        >
          Retry
        </Button>
      </div>
    );
  }
  
  if (entries.length === 0) {
    return (
      <div className="text-center py-12 glass-container p-8 mx-auto max-w-md">
        <h2 className="text-lg font-medium text-blue-800 dark:text-blue-300 mb-2">No entries found</h2>
        <p className="text-blue-700 dark:text-blue-400 mb-4">
          No screenshots match your current criteria.
        </p>
      </div>
    );
  }
  
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {entries.map((entry) => (
          <TimelineEntry key={entry.id} entry={entry} />
        ))}
      </div>
      
      {hasMore && (
        <div className="mt-8 text-center">
          <Button 
            variant="outline"
            className="inline-flex items-center bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-white/30 dark:border-gray-700/30 text-blue-700 dark:text-blue-300 hover:bg-white/70 dark:hover:bg-gray-700/70 px-4 py-2 rounded-full"
            onClick={onLoadMore}
          >
            Load More
            <ChevronDown className="ml-2 -mr-0.5 h-4 w-4" />
          </Button>
        </div>
      )}
    </>
  );
}
