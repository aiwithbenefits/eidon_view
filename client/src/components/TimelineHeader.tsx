import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface TimelineHeaderProps {
  title: string;
  date: string;
  onNavigate: (direction: 'prev' | 'next') => void;
}

export default function TimelineHeader({ title, date, onNavigate }: TimelineHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-5">
      <h2 className="text-xl font-bold bg-gradient-to-r from-blue-700 to-indigo-700 bg-clip-text text-transparent">{title}</h2>
      
      {/* Date Navigation */}
      <div className="flex items-center space-x-2 text-sm">
        <Button 
          variant="ghost" 
          size="icon"
          className="p-1.5 rounded-full hover:bg-blue-100/50 text-blue-700" 
          onClick={() => onNavigate('prev')}
          aria-label="Previous day"
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>
        
        <span className="font-medium bg-blue-500/10 backdrop-blur-sm text-blue-700 px-3 py-1 rounded-full border border-blue-200/30 shadow-sm">{date}</span>
        
        <Button 
          variant="ghost" 
          size="icon"
          className="p-1.5 rounded-full hover:bg-blue-100/50 text-blue-700" 
          onClick={() => onNavigate('next')}
          aria-label="Next day"
        >
          <ChevronRight className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
