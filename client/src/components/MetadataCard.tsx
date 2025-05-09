import { format } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";

interface MetadataCardProps {
  title: string | null;
  appName: string | null;
  url: string | null;
  timestamp: number;
}

export default function MetadataCard({ title, appName, url, timestamp }: MetadataCardProps) {
  const formattedDate = format(new Date(timestamp), "MMMM d, yyyy - HH:mm:ss");
  
  return (
    <Card className="glass-card">
      <CardContent className="pt-4">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-3">Metadata</h3>
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-blue-600 dark:text-blue-400 text-xs">Title</dt>
            <dd className="text-blue-900 dark:text-blue-200 font-medium">{title || "-"}</dd>
          </div>
          <div>
            <dt className="text-blue-600 dark:text-blue-400 text-xs">Application</dt>
            <dd className="text-blue-900 dark:text-blue-200">{appName || "-"}</dd>
          </div>
          <div>
            <dt className="text-blue-600 dark:text-blue-400 text-xs">URL</dt>
            <dd className="text-blue-900 dark:text-blue-200 truncate">
              {url ? (
                <a 
                  href={url.startsWith('http') ? url : `https://${url}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline truncate inline-block max-w-full transition-colors"
                >
                  {url}
                </a>
              ) : (
                "-"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-blue-600 dark:text-blue-400 text-xs">Date & Time</dt>
            <dd className="text-blue-900 dark:text-blue-200">{formattedDate}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
