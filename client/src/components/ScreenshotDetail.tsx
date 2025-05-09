import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ZoomInIcon, ZoomOutIcon, DownloadIcon } from "lucide-react";

interface ScreenshotDetailProps {
  imageUrl: string;
  title: string;
}

export default function ScreenshotDetail({ imageUrl, title }: ScreenshotDetailProps) {
  const [zoom, setZoom] = useState(1);
  
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.25, 3));
  };
  
  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.25, 0.5));
  };
  
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `eidon-screenshot-${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  return (
    <div className="flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300">{title}</h3>
        <div className="flex items-center space-x-2">
          <Button 
            variant="outline" 
            size="icon" 
            className="h-8 w-8 bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-white/30 dark:border-gray-700/30 text-blue-700 dark:text-blue-400 hover:bg-white/70 dark:hover:bg-gray-700/70" 
            onClick={handleZoomOut}
            disabled={zoom <= 0.5}
            aria-label="Zoom out"
          >
            <ZoomOutIcon className="h-4 w-4" />
          </Button>
          <span className="text-xs text-blue-700 dark:text-blue-400 bg-blue-100/50 dark:bg-blue-900/50 px-2 py-0.5 rounded-md">{Math.round(zoom * 100)}%</span>
          <Button 
            variant="outline" 
            size="icon" 
            className="h-8 w-8 bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-white/30 dark:border-gray-700/30 text-blue-700 dark:text-blue-400 hover:bg-white/70 dark:hover:bg-gray-700/70" 
            onClick={handleZoomIn}
            disabled={zoom >= 3}
            aria-label="Zoom in"
          >
            <ZoomInIcon className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="icon" 
            className="h-8 w-8 bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-white/30 dark:border-gray-700/30 text-blue-700 dark:text-blue-400 hover:bg-white/70 dark:hover:bg-gray-700/70" 
            onClick={handleDownload}
            aria-label="Download screenshot"
          >
            <DownloadIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      <div className="overflow-auto bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm border border-white/40 dark:border-gray-700/40 rounded-lg shadow-inner flex items-center justify-center" style={{ minHeight: '400px' }}>
        <div style={{ transform: `scale(${zoom})`, transformOrigin: 'center', transition: 'transform 0.2s ease-out' }}>
          <img 
            src={imageUrl} 
            alt={title} 
            className="max-w-full h-auto object-contain rounded-lg shadow-md"
          />
        </div>
      </div>
    </div>
  );
}
