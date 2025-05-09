import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { SearchIcon } from "lucide-react";
import { useDebounce } from "@/hooks/use-mobile";

interface SearchBarProps {
  onSearch: (query: string) => void;
  initialValue?: string;
}

export default function SearchBar({ onSearch, initialValue = "" }: SearchBarProps) {
  const [searchValue, setSearchValue] = useState(initialValue);
  const debouncedValue = useDebounce(searchValue, 500);
  
  // Handle debounced search
  useEffect(() => {
    onSearch(debouncedValue);
  }, [debouncedValue, onSearch]);
  
  return (
    <div className="w-full sm:w-3/4 md:w-1/2 relative">
      <Input
        type="text"
        placeholder="Search your digital history... (Try: 'meeting notes date:today')"
        value={searchValue}
        onChange={(e) => setSearchValue(e.target.value)}
        className="w-full px-4 py-2 glass-input text-blue-900 dark:text-blue-100 placeholder:text-blue-400/70 dark:placeholder:text-blue-300/70"
      />
      <div className="absolute right-3 top-2.5 text-blue-600/80 dark:text-blue-400/80">
        <SearchIcon className="w-5 h-5" />
      </div>
    </div>
  );
}
