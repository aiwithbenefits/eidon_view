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
    <Card className="bg-white rounded-lg shadow-sm">
      <CardContent className="pt-4 pb-2">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-semibold text-eidon-gray-700">Extracted Text</h3>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs"
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
        <div className="h-96 overflow-y-auto text-sm font-mono text-eidon-gray-800 whitespace-pre-wrap bg-eidon-gray-100 p-3 rounded">
          {text || "No text extracted"}
        </div>
      </CardContent>
    </Card>
  );
}
