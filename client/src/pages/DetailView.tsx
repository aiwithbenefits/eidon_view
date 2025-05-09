import { useRoute, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import ScreenshotDetail from "@/components/ScreenshotDetail";
import MetadataCard from "@/components/MetadataCard";
import OCRTextCard from "@/components/OCRTextCard";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function DetailView() {
  const [, setLocation] = useLocation();
  const [match, params] = useRoute("/screenshots/:id");
  
  const id = match ? parseInt(params.id) : null;
  
  // Fetch the screenshot data
  const { data: entry, isLoading, isError } = useQuery({
    queryKey: ['/api/screenshots', id],
    enabled: !!id
  });
  
  // Fetch adjacent screenshots for navigation
  const { data: timelineData } = useQuery({
    queryKey: ['/api/timeline'],
    staleTime: 30000 // 30 seconds
  });
  
  if (!match || !id) {
    return null;
  }
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  if (isError || !entry) {
    return (
      <div className="text-center py-8">
        <h2 className="text-lg font-medium text-red-600">Error loading screenshot</h2>
        <p className="text-eidon-gray-600 mt-2">Failed to load the requested screenshot.</p>
        <Button 
          variant="outline" 
          className="mt-4" 
          onClick={() => setLocation('/')}
        >
          Back to Timeline
        </Button>
      </div>
    );
  }
  
  // Find adjacent entries for navigation
  const entries = timelineData?.entries || [];
  const currentIndex = entries.findIndex(e => e.id === id);
  const prevEntry = currentIndex > 0 ? entries[currentIndex - 1] : null;
  const nextEntry = currentIndex < entries.length - 1 ? entries[currentIndex + 1] : null;
  
  const timestamp = new Date(entry.timestamp);
  const formattedDate = format(timestamp, "MMMM d, yyyy");
  const formattedTime = format(timestamp, "HH:mm");
  
  return (
    <div className="w-full">
      {/* Detail Header with Navigation */}
      <div className="flex justify-between items-center mb-4">
        <Button 
          variant="outline" 
          className="inline-flex items-center" 
          onClick={() => setLocation('/')}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back to Timeline
        </Button>
        
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => prevEntry && setLocation(`/screenshots/${prevEntry.id}`)}
            disabled={!prevEntry}
            aria-label="Previous screenshot"
          >
            <ChevronLeft className="w-5 h-5" />
          </Button>
          
          <span className="text-sm text-eidon-gray-600">
            {formattedDate} • {formattedTime}
          </span>
          
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => nextEntry && setLocation(`/screenshots/${nextEntry.id}`)}
            disabled={!nextEntry}
            aria-label="Next screenshot"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Screenshot and Metadata */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Screenshot Container */}
        <div className="lg:w-3/4 bg-white rounded-lg shadow-sm p-4">
          <ScreenshotDetail 
            imageUrl={entry.imagePath} 
            title={entry.title || "Untitled Screenshot"} 
          />
        </div>

        {/* Metadata and OCR Sidebar */}
        <div className="lg:w-1/4 flex flex-col gap-4">
          <MetadataCard
            title={entry.title}
            appName={entry.appName}
            url={entry.url}
            timestamp={entry.timestamp}
          />
          
          <OCRTextCard text={entry.extractedText || "No text extracted"} />
        </div>
      </div>
    </div>
  );
}
