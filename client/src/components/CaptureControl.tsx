import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { queryClient } from "@/lib/queryClient";
import { apiRequest } from "@/lib/api";
import { CaptureStatus } from "@/types";

export default function CaptureControl() {
  // Fetch the current capture status
  const { data, isLoading, isError } = useQuery<CaptureStatus>({
    queryKey: ['/api/capture/status'],
    refetchInterval: 30000 // Refresh every 30 seconds
  });
  
  // Toggle capture mutation
  const toggleCapture = useMutation({
    mutationFn: async () => {
      const res = await apiRequest('POST', '/api/capture/toggle', {});
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/capture/status'] });
    }
  });
  
  const handleToggle = () => {
    toggleCapture.mutate();
  };
  
  // Default to active if loading
  const isActive = isLoading ? true : (data?.active ?? true);
  
  if (isError) {
    return (
      <Button 
        variant="outline" 
        className="text-red-600 dark:text-red-400 border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/50"
        disabled
      >
        Error
      </Button>
    );
  }
  
  if (isActive) {
    return (
      <Button 
        className="flex items-center px-3 py-1.5 rounded-full focus:outline-none focus:ring-2 focus:ring-green-500/30 transition-all duration-200 bg-green-500/20 dark:bg-green-500/30 backdrop-blur-md text-green-700 dark:text-green-400 hover:bg-green-500/30 dark:hover:bg-green-500/40 border border-green-200/30 dark:border-green-500/30 shadow-sm" 
        onClick={handleToggle}
        disabled={isLoading || toggleCapture.isPending}
      >
        <span className="flex h-2 w-2 relative mr-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-600 dark:bg-green-500"></span>
        </span>
        Active
      </Button>
    );
  } else {
    return (
      <Button 
        className="flex items-center px-3 py-1.5 rounded-full focus:outline-none focus:ring-2 focus:ring-red-500/30 transition-all duration-200 bg-red-500/20 dark:bg-red-500/30 backdrop-blur-md text-red-700 dark:text-red-400 hover:bg-red-500/30 dark:hover:bg-red-500/40 border border-red-200/30 dark:border-red-500/30 shadow-sm" 
        onClick={handleToggle}
        disabled={isLoading || toggleCapture.isPending}
      >
        <span className="relative inline-flex rounded-full h-2 w-2 bg-red-600 dark:bg-red-500 mr-2"></span>
        Paused
      </Button>
    );
  }
}
