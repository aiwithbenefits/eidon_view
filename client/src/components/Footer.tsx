export default function Footer() {
  return (
    <footer className="bg-white/40 backdrop-blur-sm border-t border-white/20 py-3">
      <div className="container mx-auto px-4">
        <div className="flex flex-col sm:flex-row justify-between items-center">
          <p className="text-sm text-blue-700">Eidon - Your Personal Digital History Recorder</p>
          <div className="flex items-center space-x-4 mt-2 sm:mt-0">
            <button className="text-sm text-blue-600 hover:text-blue-800 transition-colors">About</button>
            <span className="text-xs bg-blue-500/10 backdrop-blur-sm text-blue-700 px-2.5 py-0.5 rounded-full border border-blue-200/30 shadow-sm">v1.0.0</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
