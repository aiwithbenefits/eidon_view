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
    <Card className="bg-white rounded-lg shadow-sm">
      <CardContent className="pt-4">
        <h3 className="text-sm font-semibold text-eidon-gray-700 mb-3">Metadata</h3>
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-eidon-gray-500">Title</dt>
            <dd className="text-eidon-gray-800 font-medium">{title || "-"}</dd>
          </div>
          <div>
            <dt className="text-eidon-gray-500">Application</dt>
            <dd className="text-eidon-gray-800">{appName || "-"}</dd>
          </div>
          <div>
            <dt className="text-eidon-gray-500">URL</dt>
            <dd className="text-eidon-gray-800 truncate">
              {url ? (
                <a 
                  href={url.startsWith('http') ? url : `https://${url}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline truncate inline-block max-w-full"
                >
                  {url}
                </a>
              ) : (
                "-"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-eidon-gray-500">Date & Time</dt>
            <dd className="text-eidon-gray-800">{formattedDate}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
