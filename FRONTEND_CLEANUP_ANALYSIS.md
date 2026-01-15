# Frontend Cleanup Analysis - vizu_dashboard

**Date**: January 14, 2026
**Analyzed Directory**: `apps/vizu_dashboard/src`
**Total Files**: 70 TypeScript/TSX files

---

## 🔴 UNUSED FILES (Can be deleted)

### Pages (4 files)
1. ❌ **`pages/ChatPage.tsx`** - Not imported in routes
   - Has full implementation but never used
   - AdminChatPage exists as replacement in admin folder

2. ❌ **`pages/PedidosListPage.tsx`** - Not imported in routes
   - Duplicate functionality - PedidosPage already exists and is used
   - Uses old mock data approach

3. ❌ **`pages/ChartsPage.tsx`** - Placeholder with no real content
   - Only shows "Página de Gráficos" heading
   - Routed but empty implementation
   - Route: `/dashboard/charts`

### Components (3 files)
4. ❌ **`components/GraphPlaceholder.tsx`** - Never imported
   - Only shows "Gráfico Placeholder" text
   - GraphComponent is used instead

5. ❌ **`components/MapPlaceholder.tsx`** - Never imported
   - Only shows "Mapa Placeholder" text
   - MapComponent is used instead

6. ❌ **`components/FloatingMenu.tsx`** - Never imported
   - Old implementation, MenuDrawer is used

---

## 🟡 DUPLICATE FUNCTIONALITY (Need consolidation)

### Pages with Similar Purposes
1. **PedidosPage.tsx** (used) vs **PedidosListPage.tsx** (unused)
   - PedidosPage is actively used with new indicators
   - PedidosListPage has table view but outdated
   - **Action**: Delete PedidosListPage

---

## 🟢 ACTIVE FILES (Keep)

### Core Pages (10 files)
✅ HomePage.tsx - Main dashboard
✅ ClientesPage.tsx - Customer overview with indicators
✅ ClientesListPage.tsx - Customer list table
✅ FornecedoresPage.tsx - Supplier overview with indicators
✅ FornecedoresListPage.tsx - Supplier list table
✅ ProdutosListPage.tsx - Product list with indicators
✅ PedidosPage.tsx - Orders overview with indicators
✅ SettingsPage.tsx - User settings
✅ LoginPage.tsx - Authentication
✅ LandingFinalPage.tsx - Marketing landing

### Admin Page.tsx - Products overview with indicators
✅ ProdutosListPage.tsx - Product list table
✅ admin/AdminHomePage.tsx
✅ admin/AdminFontesPage.tsx
✅ admin/AdminFontesDetalhesPage.tsx
✅ admin/AdminPlanosPage.tsx
✅ admin/AdminChatPage.tsx
✅ admin/AdminAjudaPage.tsx
✅ admin/AdminPrivacidadePage.tsx

### Active Components (15 files)
✅ DashboardCard.tsx - Main card component with KPI accordion
✅ ListCard.tsx - List display component
✅ MapComponent.tsx - Real map implementation
✅ GraphComponent.tsx - Real graph implementation
✅ GraphCarousel.tsx - Multiple graphs display
✅ AccordionComponent.tsx - KPI accordion
✅ ModalContentLayout.tsx - Modal structure
✅ MiniCard.tsx - Small card in lists
✅ Header.tsx - Navigation header
✅ MenuDrawer.tsx - Side menu
✅ ChatPanel.tsx - Chat interface
✅ StatCard.tsx - Statistics card (used in HomePage)
✅ SignupModal.tsx - Registration modal
✅ ClienteDetailsModal.tsx - Customer details
✅ FornecedorDetailsModal.tsx - Supplier details
✅ PedidoDetailsModal.tsx - Order details
✅ ProdutoDetailsModal.tsx - Product details

### Layouts (1 file)
✅ layouts/MainLayout.tsx

---

## 📦 SERVICES (All active - keep)
✅ services/analyticsService.ts - Analytics API integration
✅ services/connectorService.ts - Connector management
✅ services/connectorStatusService.ts - Connector status checks
✅ services/chatService.ts - Chat functionality

---

## 🔧 UTILS (All active - keep)
✅ utils/regionCoordinates.ts - Geographic data
✅ utils/* (any other utility files)

---

## 📊 CLEANUP SUMMARY

### Files to DELETE (7 files):
```bash
# Pages
rm apps/vizu_dashboard/src/pages/ChatPage.tsx
rm apps/vizu_dashboard/src/pages/PedidosListPage.tsx
rm apps/vizu_dashboar6 files):
```bash
# Pages
rm apps/vizu_dashboard/src/pages/ChatPage.tsx
rm apps/vizu_dashboard/src/pages/PedidosListPage.tsx
rm apps/vizu_dashboard/src/pages/ChartoatingMenu.tsx
```

### Routes to UPDATE:
```typescript
// File: apps/vizu_dashboard/src/routes/dashboardRoutes.tsx

// REMOVE these routes:
- /dashboard/charts (line ~27) - Remove ChartsPage route
- /dashboard/produtos (line ~45) - Already have /dashboard/produtos/lista
```

---
is route:
- /dashboard/charts (line ~27) - Remove ChartsPage route
### Step 1: Remove Unused Files (Safe)
```bash
cd /Users/lucascruz/Documents/GitHub/vizu-mono

# Remove unused page files
rm apps/vizu_dashboard/src/pages/ChatPage.tsx
rm apps/vizu_dashboard/src/pages/PedidosListPage.tsx
rm apps/vizu_dashboard/src/pages/ChartsPage.tsx

# Remove placeholder components
rm apps/vizu_dashboard/src/components/GraphPlaceholder.tsx
rm apps/vizu_dashboard/src/components/MapPlaceholder.tsx
rm apps/vizu_dashboard/src/components/FloatingMenu.tsx
```

### Step 2: Consolidate ProdutosPage
- Move any unique features from ProdutosPage.tsx to ProdutosListPage.tsx
- Then delete ProdutosPage.tsx

### Step 3: Clean Up Routes
Remove or redirect these routes in `dashboardRoutes.tsx`:
- `/dashboard/charts` → Remove (no content)
- `/dashboard
// Remove:
import ChartsPage from "../pages/ChartsPage";
import ProdutosPage from "../pages/ProdutosPage"; // If consolidating
```
this route in `dashboardRoutes.tsx`:
- `/dashboard/charts` → Remove (no content)

### Step 3: Update dashboardRoutes.tsx imports
After deletion, remove unused import:
```typescript
// Remove:
import ChartsPage from "../pages/ChartsPage";
### After Cleanup:
- Total files: ~63
- All files actively used
- Clearer codebase structure
- Easier mainten6 (8.5%)
- Placeholder/duplicate code: Multiple instances

### After Cleanup:
- Total files: ~64

1. **ProdutosPage.tsx** - Check if there are any unique features before deleting
2. **ChartsPage** - Verify no one is linking to `/dashboard/charts` directly
3. **Test after deletion** - Run the app and verify all routes work

---

## ✅ SAFE TO DELETE (Confirmed)
ChartsPage** - Verify no one is linking to `/dashboard/charts` directly
2. GraphPlaceholder.tsx - Never imported
2. MapPlaceholder.tsx - Never imported
3. FloatingMenu.tsx - Never imported
4. PedidosListPage.tsx - Not in routes
5. ChatPage.tsx - Not in routes (AdminChatPage is used)

---

## 🔍 NEXT STEPS

1. Review this analysis
2. Backup current code (git commit)
3. Execute Step 1 cleanup (remove unused files)
4. Test application
5. Execute Steps 2-4 (consolidation & route cleanup)
6. Final testing

**Estimated cleanup time**: 15-30 minutes
**Risk level**: Low (mostly removing unused code)
**Benefit**: Cleaner codebase, less confusion, easier maintenance
