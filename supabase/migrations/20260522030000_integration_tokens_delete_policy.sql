-- Allow authenticated users to delete their own integration tokens
-- (needed for disconnect flow in AdminScreen)
CREATE POLICY "own client delete" ON integration_tokens
  FOR DELETE
  USING (client_id = get_my_client_id());
