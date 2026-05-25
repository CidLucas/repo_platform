-- Add ui_prefs JSONB column to clientes_blu for frontend user preferences
ALTER TABLE public.clientes_blu
  ADD COLUMN IF NOT EXISTS ui_prefs jsonb DEFAULT '{}'::jsonb;

-- RPC to merge a single key into ui_prefs without clobbering other keys
CREATE OR REPLACE FUNCTION public.set_ui_pref(p_key text, p_value jsonb)
RETURNS void
LANGUAGE sql
SECURITY INVOKER
AS $$
  UPDATE public.clientes_blu
  SET ui_prefs = jsonb_set(COALESCE(ui_prefs, '{}'), ARRAY[p_key], p_value, true)
  WHERE external_user_id = (auth.jwt() ->> 'sub');
$$;

GRANT EXECUTE ON FUNCTION public.set_ui_pref(text, jsonb) TO authenticated;
