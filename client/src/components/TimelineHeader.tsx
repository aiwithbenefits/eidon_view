import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface TimelineHeaderProps {
  title: string;
  date: string;
  onNavigate: (direction: 'prev' | 'next') => void;
}

export default function TimelineHeader({ title, date, onNavigate }: TimelineHeaderProps) {
  return (
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-xl font-semibold text-eidon-gray-800">{title}</h2>
      
      {/* Date Navigation */}
      <div className="flex items-center space-x-2 text-sm">
        <Button 
          variant="ghost" 
          size="icon"
          className="p-1.5 rounded-md hover:bg-eidon-gray-200 text-eidon-gray-700" 
          onClick={() => onNavigate('prev')}
          aria-label="Previous day"
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>
        
        <span className="font-medium">{date}</span>
        
        <Button 
          variant="ghost" 
          size="icon"
          className="p-1.5 rounded-md hover:bg-eidon-gray-200 text-eidon-gray-700" 
          onClick={() => onNavigate('next')}
          aria-label="Next day"
        >
          <ChevronRight className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
