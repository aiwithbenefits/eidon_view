import { useLocation } from "wouter";
import { format } from "date-fns";
import { ScreenshotEntry } from "@/types";
import { 
  Card, 
  CardContent 
} from "@/components/ui/card";
import { MonitorIcon, LinkIcon } from "lucide-react";

interface TimelineEntryProps {
  entry: ScreenshotEntry;
}

export default function TimelineEntry({ entry }: TimelineEntryProps) {
  const [, navigate] = useLocation();
  
  const handleClick = () => {
    navigate(`/screenshots/${entry.id}`);
  };
  
  const formattedTime = format(new Date(entry.timestamp), "HH:mm");
  
  return (
    <Card 
      className="glass-card hover:shadow-md transition-all duration-200 overflow-hidden cursor-pointer hover:bg-white/80" 
      onClick={handleClick}
    >
      <div className="relative">
        <img 
          src={entry.imagePath} 
          alt={entry.title || "Screenshot"} 
          className="w-full h-48 object-cover" 
        />
        <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded-md">
          <time>{formattedTime}</time>
        </div>
      </div>
      <CardContent className="p-3">
        <div className="flex items-center mb-2">
          <span className="text-sm font-medium text-blue-900 line-clamp-1">
            {entry.title || entry.windowTitle || "Untitled Screenshot"}
          </span>
        </div>
        <div className="flex items-center text-xs text-blue-700 mb-2">
          <MonitorIcon className="w-4 h-4 mr-1" />
          <span className="mr-2">{entry.appName || "Unknown Application"}</span>
          
          {entry.url && (
            <>
              <LinkIcon className="w-4 h-4 mr-1" />
              <span className="truncate">{entry.url}</span>
            </>
          )}
        </div>
        {entry.extractedText && (
          <p className="text-xs text-blue-600/70 line-clamp-2">
            {entry.extractedText}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
