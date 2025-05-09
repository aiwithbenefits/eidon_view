import { ReactNode } from "react";
import SearchBar from "./SearchBar";
import ActiveFilters from "./ActiveFilters";
import CaptureControl from "./CaptureControl";
import Footer from "./Footer";
import { useSearch } from "@/hooks/useSearch";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

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
    <div className="flex flex-col min-h-screen font-sans text-foreground">
      {/* Top Bar */}
      <header className="sticky top-0 z-10 bg-white/70 dark:bg-gray-900/70 backdrop-blur-lg border-b border-white/20 dark:border-gray-700/20 shadow-sm">
        <div className="container mx-auto px-4 py-3">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center">
              {/* App Logo/Title */}
              <Logo />
              <span className="ml-2 text-xs bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 text-blue-800 dark:text-blue-300 px-2.5 py-0.5 rounded-full shadow-sm">
                Personal Digital History
              </span>
            </div>

            {/* Search Bar */}
            <SearchBar 
              onSearch={setSearchQuery} 
              initialValue={searchQuery} 
            />

            {/* Capture Controls and Theme Toggle */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-blue-800 dark:text-blue-300">Capture:</span>
                <CaptureControl />
              </div>
              <ThemeToggle />
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
