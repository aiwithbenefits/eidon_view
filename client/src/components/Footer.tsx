export default function Footer() {
  return (
    <footer className="bg-white border-t border-eidon-gray-200 py-3">
      <div className="container mx-auto px-4">
        <div className="flex flex-col sm:flex-row justify-between items-center">
          <p className="text-sm text-eidon-gray-500">Eidon - Your Personal Digital History Recorder</p>
          <div className="flex items-center space-x-4 mt-2 sm:mt-0">
            <button className="text-sm text-eidon-gray-500 hover:text-eidon-gray-700">About</button>
            <span className="text-xs bg-eidon-gray-200 text-eidon-gray-600 px-2 py-0.5 rounded-full">v1.0.0</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
