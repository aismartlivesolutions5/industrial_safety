import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  const BACKEND_URL = Deno.env.get("INDUSTRIAL_BACKEND_URL");
  if (!BACKEND_URL) {
    return new Response(JSON.stringify({ error: "Backend URL not configured" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    const url = new URL(req.url);
    const topN = url.searchParams.get("top_n") || "20";

    if (isNaN(Number(topN))) {
      return new Response(JSON.stringify({ error: "Invalid query parameter" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const response = await fetch(
      `${BACKEND_URL}/alerts/last-24h?top_n=${topN}`,
      { signal: AbortSignal.timeout(5000) }
    );
    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Alerts last 24h error:", error);
    return new Response(JSON.stringify({ error: "Upstream Timeout", details: String(error) }), {
      status: 504,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
