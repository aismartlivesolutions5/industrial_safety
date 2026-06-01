const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
};

Deno.serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    console.log("Request method:", req.method);
    console.log("Request URL:", req.url);

    // Get base URL from environment
    const baseUrl = Deno.env.get("EXTERNAL_API_URL");
    if (!baseUrl) {
      console.error("Missing EXTERNAL_API_URL environment variable");
      return new Response(
        JSON.stringify({ error: "Missing EXTERNAL_API_URL configuration" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
    console.log("Base URL configured:", baseUrl);

    // Parse request body with error handling
    let requestData;
    try {
      const bodyText = await req.text();
      console.log("Raw request body:", bodyText);
      
      if (!bodyText) {
        console.error("Empty request body");
        return new Response(
          JSON.stringify({ error: "Request body cannot be empty" }),
          { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      
      requestData = JSON.parse(bodyText);
    } catch (parseError) {
      console.error("JSON parse error:", parseError);
      return new Response(
        JSON.stringify({ error: "Invalid JSON in request body", details: String(parseError) }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { path, method = "GET", payload } = requestData;

    if (!path) {
      console.error("Missing path in request body");
      return new Response(
        JSON.stringify({ error: "Missing required field: path" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Build upstream URL
    const upstreamUrl = `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    console.log("Target path:", path);
    console.log("Upstream URL:", upstreamUrl);
    console.log("HTTP method:", method);

    // Log payload if present
    if (method !== "GET" && method !== "HEAD" && payload) {
      console.log("Request payload:", JSON.stringify(payload));
    }

    // Keep proxy lightweight to avoid platform timeouts; forward upstream status/body
    try {
      console.log("Fetching from upstream...");
      const upstreamResponse = await fetch(upstreamUrl, {
        method,
        headers: { "Content-Type": "application/json" },
        body: (method !== "GET" && method !== "HEAD" && payload) ? JSON.stringify(payload) : undefined,
        signal: AbortSignal.timeout(20000),
      });

      console.log("Upstream response status:", upstreamResponse.status);
      const responseText = await upstreamResponse.text();

      return new Response(responseText, {
        status: upstreamResponse.status,
        headers: {
          ...corsHeaders,
          "Content-Type": upstreamResponse.headers.get("Content-Type") || "application/json",
        },
      });
    } catch (fetchError) {
      console.error("Fetch error:", fetchError);
      return new Response(
        JSON.stringify({ error: "Upstream API unavailable", details: String(fetchError) }),
        { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
  } catch (error) {
    console.error("Unhandled proxy error:", error);
    console.error("Error type:", error?.constructor?.name);
    console.error("Error message:", String(error));
    
    return new Response(
      JSON.stringify({ 
        error: "Proxy function error", 
        details: String(error),
        errorType: error?.constructor?.name 
      }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
