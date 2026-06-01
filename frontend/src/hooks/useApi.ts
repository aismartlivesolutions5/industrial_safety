import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PredictRequest, ChatRequest } from "@/types/api";

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: api.getOverview,
    refetchInterval: 300000, // 5 minutes
    retry: 1,
    staleTime: 120000,
  });
}

export function useRecentAlerts(windowMinutes = 60, topN = 20) {
  return useQuery({
    queryKey: ["alerts-recent", windowMinutes, topN],
    queryFn: () => api.getRecentAlerts(windowMinutes, topN),
    refetchInterval: 300000,
    retry: 1,
    staleTime: 120000,
  });
}

export function useLast24hAlerts(topN = 20) {
  return useQuery({
    queryKey: ["alerts-last-24h", topN],
    queryFn: () => api.getLast24hAlerts(topN),
    refetchInterval: 300000,
    retry: 1,
    staleTime: 120000,
  });
}

export function usePredict() {
  return useMutation({
    mutationFn: (request: PredictRequest) => api.predict(request),
  });
}

export function useChat() {
  return useMutation({
    mutationFn: (request: ChatRequest) => api.chat(request),
  });
}
