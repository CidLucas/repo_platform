-- Migration: Add workflow_graph column to agent_catalog
-- Purpose: Store custom node/edge layout for the drag-and-drop workflow editor
-- Format: {nodes: [{id, type, position: {x,y}}], edges: [{source, target, label, condition}]}
-- NULL means "use default graph" (backward compatible)

ALTER TABLE public.agent_catalog
  ADD COLUMN IF NOT EXISTS workflow_graph JSONB DEFAULT NULL;

COMMENT ON COLUMN public.agent_catalog.workflow_graph IS
  'Custom workflow graph definition. NULL = use default graph. Format: {nodes: [...], edges: [...]}';
