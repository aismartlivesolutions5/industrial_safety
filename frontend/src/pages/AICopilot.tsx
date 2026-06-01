import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchChatbotSummary, askChatbot } from "@/lib/api";
import { AppLayout } from "@/components/layout/AppLayout";
import type { ChatMessage } from "@/types/api";
import { Bot, Send, Loader2, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const suggestions = [
  "Summarize plant safety",
  "Show live alerts",
  "Why is REACTOR_C1 critical?",
  "Give shift handover summary",
  "Which asset needs immediate attention?",
  "What action should operators take now?",
];

export default function AICopilot() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const summary = useQuery({ queryKey: ["copilot-summary"], queryFn: fetchChatbotSummary });

  const askMutation = useMutation({
    mutationFn: askChatbot,
    onSuccess: (data) => {
      const response = data as any;
      setMessages((prev) => [...prev, { role: "assistant", content: response.answer || response.summary || JSON.stringify(data) }]);
    },
    onError: (err) => {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err.message}` }]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = (text?: string) => {
    const q = text || input.trim();
    if (!q) return;
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setInput("");
    askMutation.mutate(q);
  };

  return (
    <AppLayout title="AI Safety Copilot" subtitle="Ask questions about plant safety and operations">
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 h-[calc(100vh-180px)]">
        {/* Chat Panel */}
        <div className="xl:col-span-3 glass-card rounded-xl flex flex-col overflow-hidden">
          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                  <Bot className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">InsightGuard AI Copilot</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  Ask me about plant safety, asset conditions, risk analysis, or operational recommendations.
                </p>
              </div>
            )}
            <AnimatePresence>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-primary/20 text-foreground border border-primary/30"
                        : "bg-secondary/50 text-foreground border border-border/30"
                    }`}
                  >
                    {msg.role === "assistant" && (
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <Bot className="w-3.5 h-3.5 text-primary" />
                        <span className="text-[10px] text-primary font-semibold uppercase tracking-wider">Copilot</span>
                      </div>
                    )}
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            {askMutation.isPending && (
              <div className="flex justify-start">
                <div className="bg-secondary/50 rounded-xl px-4 py-3 border border-border/30">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                </div>
              </div>
            )}
          </div>

          {/* Suggestions */}
          <div className="px-6 py-3 border-t border-border/30 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => handleSend(s)}
                className="text-xs px-3 py-1.5 rounded-full bg-secondary/50 border border-border/50 text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all"
              >
                <Sparkles className="w-3 h-3 inline mr-1" />
                {s}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-border/30">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Ask about plant safety..."
                className="flex-1 bg-secondary/50 border border-border/50 rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || askMutation.isPending}
                className="px-5 py-3 rounded-xl bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 disabled:opacity-50 transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Summary Sidebar */}
        <div className="glass-card rounded-xl p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Plant Overview</h3>
          </div>
          {summary.isLoading ? (
            <div className="flex-1 flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
          ) : (
            <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap flex-1 overflow-y-auto scrollbar-thin">
              {summary.data?.summary || "No summary available yet."}
            </p>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
