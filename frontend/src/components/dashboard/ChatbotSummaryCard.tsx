import { Bot, Loader2 } from "lucide-react";

interface Props {
  data?: { summary: string };
  isLoading: boolean;
}

export function ChatbotSummaryCard({ data, isLoading }: Props) {
  return (
    <div className="glass-card rounded-xl p-6 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg bg-primary/20 flex items-center justify-center">
          <Bot className="w-4 h-4 text-primary" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">AI Safety Summary</h3>
      </div>
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {data?.summary || "No summary available. Click AI Copilot for detailed analysis."}
          </p>
        </div>
      )}
    </div>
  );
}
