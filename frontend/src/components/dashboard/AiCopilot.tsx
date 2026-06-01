import { useState, useRef, useEffect } from "react";
import { useChat } from "@/hooks/useApi";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Loader2, ChevronDown, ChevronUp, Bot, User } from "lucide-react";
import type { ChatMessage, ChatResponse } from "@/types/api";

function SensorStrip({ snapshot }: { snapshot: Record<string, unknown> }) {
  const keys = ["pressure_bar_g", "temp_c", "water_level_pct", "lel_pct", "voc_ppm", "vibration_rms_mm_s", "active_alarm_count"];
  const labels: Record<string, string> = { pressure_bar_g: "Press.", temp_c: "Temp", water_level_pct: "Water", lel_pct: "LEL", voc_ppm: "VOC", vibration_rms_mm_s: "Vib.", active_alarm_count: "Alarms" };
  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      {keys.map((k) => {
        const v = snapshot[k];
        if (v === undefined || v === null) return null;
        return (
          <span key={k} className="bg-nominal/10 text-nominal rounded px-1.5 py-0.5 text-[9px] font-mono">
            {labels[k]}: {typeof v === "number" ? v.toFixed(1) : String(v)}
          </span>
        );
      })}
    </div>
  );
}

function AssistantCard({ data, sensorSnapshot }: { data: ChatResponse["answer"]; sensorSnapshot?: Record<string, unknown> | null }) {
  return (
    <div className="space-y-2 mt-2">
      {sensorSnapshot && <SensorStrip snapshot={sensorSnapshot} />}
      <p className="text-sm text-foreground">{data.summary}</p>
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-muted/50 rounded-lg p-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Risk Level</p>
          <p className={`text-xs font-semibold ${
            data.risk_level?.toLowerCase() === "emergency" ? "text-emergency" :
            data.risk_level?.toLowerCase() === "critical" ? "text-critical" : "text-nominal"
          }`}>{data.risk_level}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Anomaly</p>
          <p className="text-xs font-semibold text-foreground">{data.anomaly_status}</p>
        </div>
      </div>
      {data.top_drivers && data.top_drivers.length > 0 && (
        <div className="bg-muted/50 rounded-lg p-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Top Drivers</p>
          {data.top_drivers.map((d, i) => (
            <p key={i} className="text-xs font-mono text-foreground">{typeof d === "string" ? d : JSON.stringify(d)}</p>
          ))}
        </div>
      )}
      {data.recommended_actions && data.recommended_actions.length > 0 && (
        <div className="bg-muted/50 rounded-lg p-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Recommended Actions</p>
          {data.recommended_actions.map((a, i) => (
            <p key={i} className="text-xs text-foreground">• {typeof a === "string" ? a : JSON.stringify(a)}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export function AiCopilot() {
  const [isOpen, setIsOpen] = useState(true);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { mutate, isPending } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isPending) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    mutate(
      { question: input.trim() },
      {
        onSuccess: (data) => {
          const assistantMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: data.answer.summary,
            data: data.answer,
            sensorSnapshot: data.sensor_snapshot,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
        },
        onError: () => {
          const errorMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: "Error 504: Upstream Connection Timeout. Please retry.",
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMsg]);
        },
      }
    );
  };

  return (
    <div className="glass-card flex flex-col h-full overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-5 py-4 border-b border-border/50 hover:bg-foreground/[0.02] transition-colors lg:cursor-default"
      >
        <div className="flex items-center gap-2">
          <Bot size={16} strokeWidth={1.5} className="text-nominal" />
          <h2 className="text-sm font-semibold uppercase tracking-wider">AI Copilot</h2>
        </div>
        <span className="lg:hidden">
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
            className="flex flex-col flex-1 min-h-0 overflow-hidden lg:!h-auto lg:flex-1"
          >
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px] max-h-[400px] lg:max-h-[500px]">
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <p className="text-xs font-mono text-muted-foreground text-center">
                    SYSTEM NOMINAL<br />Ask about plant safety, risk analysis, or predictions.
                  </p>
                </div>
              )}
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-6 h-6 rounded bg-nominal/10 flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot size={12} className="text-nominal" />
                    </div>
                  )}
                  <div className={`max-w-[85%] rounded-lg px-3 py-2 ${
                    msg.role === "user"
                      ? "bg-nominal/10 text-foreground"
                      : "bg-muted/50 text-foreground"
                  }`}>
                    {msg.role === "assistant" && msg.data ? (
                      <AssistantCard data={msg.data} sensorSnapshot={msg.sensorSnapshot} />
                    ) : (
                      <p className="text-sm">{msg.content}</p>
                    )}
                    <p className="text-[10px] font-mono text-muted-foreground mt-1">
                      {msg.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                  {msg.role === "user" && (
                    <div className="w-6 h-6 rounded bg-secondary flex items-center justify-center flex-shrink-0 mt-1">
                      <User size={12} className="text-muted-foreground" />
                    </div>
                  )}
                </motion.div>
              ))}
              {isPending && (
                <div className="flex gap-2">
                  <div className="w-6 h-6 rounded bg-nominal/10 flex items-center justify-center flex-shrink-0">
                    <Bot size={12} className="text-nominal" />
                  </div>
                  <div className="bg-muted/50 rounded-lg px-3 py-2">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-pulse" />
                      <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-pulse" style={{ animationDelay: "0.15s" }} />
                      <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-pulse" style={{ animationDelay: "0.3s" }} />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-border/50">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                  placeholder="Ask about safety risks..."
                  className="flex-1 bg-muted/50 rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-nominal/30"
                />
                <motion.button
                  whileTap={{ scale: 0.97 }}
                  onClick={handleSend}
                  disabled={!input.trim() || isPending}
                  className="p-2 rounded-lg bg-nominal/10 text-nominal hover:bg-nominal/20 transition-colors disabled:opacity-30"
                >
                  <Send size={16} strokeWidth={1.5} />
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
