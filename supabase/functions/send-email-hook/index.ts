// No-op email hook for Supabase Auth
// Replaces the built-in email provider to bypass the 2/h rate limit.
// Called by Supabase Auth every time a send_email hook is triggered.
// Returns success immediately without actually sending any email.

Deno.serve(async (req: Request) => {
  const body = await req.json()
  console.log(`[send-email-hook] Received: ${JSON.stringify(body)}`)

  return new Response(
    JSON.stringify({
      status: "ok",
      message: "noop - email sending disabled via hook"
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" }
    }
  )
})
