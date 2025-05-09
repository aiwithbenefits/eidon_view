import { XIcon } from "lucide-react";
import { ActiveFilter } from "@/types";

interface ActiveFiltersProps {
  filters: ActiveFilter[];
  onRemove: (filter: ActiveFilter) => void;
}

export default function ActiveFilters({ filters, onRemove }: ActiveFiltersProps) {
  if (filters.length === 0) {
    return null;
  }
  
  return (
    <div className="flex flex-wrap gap-2 mt-2 pb-2 text-sm">
      {filters.map((filter, index) => (
        <div 
          key={`${filter.key}-${index}`}
          className="inline-flex items-center bg-blue-500/10 text-blue-700 px-2 py-1 rounded-md"
        >
          <span>{filter.display}</span>
          <button 
            className="ml-1 focus:outline-none" 
            onClick={() => onRemove(filter)}
            aria-label={`Remove ${filter.key} filter`}
          >
            <XIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
