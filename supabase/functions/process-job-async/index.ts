import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function getServiceClient() {
  return createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { job_id } = await req.json();

    if (!job_id) {
      return json({ error: "job_id is required" }, 400);
    }

    const supabase = getServiceClient();

    // Call the RPC to process the entire sync job at once
    // This processes ALL rows in one execution (no batching, no cron delay)
    const { data, error } = await supabase.rpc("sincronizar_dados_cliente", {
      p_job_id: job_id,
    });

    if (error) {
      console.error("[process-job-async] RPC error:", error);
      return json(
        { error: "Failed to process sync job", details: error.message },
        500
      );
    }

    console.log(`[process-job-async] Job ${job_id} processed:`, data);

    return json({
      success: true,
      job_id,
      result: data,
    });
  } catch (err) {
    console.error("[process-job-async] Handler error:", err);
    return json(
      {
        error: "Internal error",
        details: err instanceof Error ? err.message : String(err),
      },
      500
    );
  }
});
