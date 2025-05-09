import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Set document title
document.title = "Eidon - Your Personal Digital History Recorder";

createRoot(document.getElementById("root")!).render(<App />);
