import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CopyIcon, CheckIcon } from "lucide-react";

interface OCRTextCardProps {
  text: string;
}

export default function OCRTextCard({ text }: OCRTextCardProps) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  
  return (
    <Card className="glass-card">
      <CardContent className="pt-4 pb-2">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300">Extracted Text</h3>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs text-blue-700 dark:text-blue-400 hover:bg-blue-100/50 dark:hover:bg-blue-800/50"
            onClick={handleCopy}
            disabled={copied}
          >
            {copied ? (
              <>
                <CheckIcon className="h-3.5 w-3.5 mr-1" />
                Copied
              </>
            ) : (
              <>
                <CopyIcon className="h-3.5 w-3.5 mr-1" />
                Copy
              </>
            )}
          </Button>
        </div>
        <div className="h-96 overflow-y-auto text-sm font-mono text-blue-800 dark:text-blue-300 whitespace-pre-wrap bg-white/30 dark:bg-gray-800/30 backdrop-blur-sm border border-white/40 dark:border-gray-700/40 p-3 rounded-lg shadow-inner">
          {text || "No text extracted"}
        </div>
      </CardContent>
    </Card>
  );
}
