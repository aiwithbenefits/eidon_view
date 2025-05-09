import { ReactNode } from "react";
import SearchBar from "./SearchBar";
import ActiveFilters from "./ActiveFilters";
import CaptureControl from "./CaptureControl";
import Footer from "./Footer";
import { useSearch } from "@/hooks/useSearch";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { 
    searchQuery, 
    activeFilters, 
    setSearchQuery, 
    removeFilter 
  } = useSearch();
  
  return (
    <div className="flex flex-col min-h-screen bg-eidon-gray-100 font-sans text-eidon-gray-900">
      {/* Top Bar */}
      <header className="sticky top-0 z-10 bg-white border-b border-eidon-gray-200 shadow-sm">
        <div className="container mx-auto px-4 py-2">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center">
              {/* App Logo/Title */}
              <h1 className="text-xl font-semibold text-blue-700">Eidon</h1>
              <span className="ml-2 text-xs bg-eidon-gray-200 text-eidon-gray-600 px-2 py-0.5 rounded-full">Personal Digital History</span>
            </div>

            {/* Search Bar */}
            <SearchBar 
              onSearch={setSearchQuery} 
              initialValue={searchQuery} 
            />

            {/* Capture Controls */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-eidon-gray-600">Capture:</span>
              <CaptureControl />
            </div>
          </div>
          
          {/* Active Filters */}
          <ActiveFilters 
            filters={activeFilters} 
            onRemove={removeFilter} 
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 flex-grow">
        {children}
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
