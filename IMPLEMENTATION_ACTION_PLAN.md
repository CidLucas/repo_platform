# Frontend-Backend Integration - Action Plan
## Step-by-Step Implementation Guide

Based on the Figma design analysis, here's the prioritized implementation plan.

---

## 🎯 Priority 1: Backend API Enhancements (Week 1)

### Task 1.1: Add Missing Chart Endpoints for Time Series

#### File: `services/analytics_api/src/analytics_api/schemas/metrics.py`

Add new response fields:

```python
# After line 78 (FornecedoresOverviewResponse)
class FornecedoresOverviewResponse(BaseModel):
    # ... existing fields ...

    # ADD THESE NEW FIELDS:
    chart_receita_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Receita mensal dos fornecedores ao longo do tempo"
    )
    chart_ticketmedio_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Ticket médio dos fornecedores ao longo do tempo"
    )
    chart_quantidade_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Volume (kg/ton) comercializado ao longo do tempo"
    )

# Similarly for ClientesOverviewResponse (after line 89)
class ClientesOverviewResponse(BaseModel):
    # ... existing fields ...

    # ADD THESE NEW FIELDS:
    chart_receita_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Receita comprada por clientes ao longo do tempo"
    )
    chart_ticketmedio_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Ticket médio dos clientes ao longo do tempo"
    )
    chart_quantidade_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Volume comprado ao longo do tempo"
    )

# Similarly for ProdutosOverviewResponse (after line 100)
class ProdutosOverviewResponse(BaseModel):
    # ... existing fields ...

    # ADD THESE NEW FIELDS:
    chart_produtos_no_tempo: list[ChartDataPoint] = Field(
        default=[],
        description="Quantidade de produtos vendidos ao longo do tempo"
    )
    chart_produtos_por_regiao: list[ChartDataPoint] = Field(
        default=[],
        description="Produtos mais vendidos por região"
    )
```

#### File: `services/analytics_api/src/analytics_api/api/endpoints/rankings.py`

Update the endpoint implementations:

```python
# In get_fornecedores_overview_endpoint (around line 30)
@router.get("/fornecedores", ...)
def get_fornecedores_overview_endpoint(...):
    """Retorna KPIs, rankings e gráficos para a página de Fornecedores."""

    suppliers = repo.get_gold_suppliers_metrics(client_id, period) or []
    products = repo.get_gold_products_metrics(client_id) or []

    # Existing rankings...
    ranking_por_receita = [...]

    # NEW: Add time series charts
    # Get monthly aggregated data
    monthly_data = repo.get_suppliers_monthly_metrics(client_id, period)

    chart_receita_no_tempo = [
        ChartDataPoint(
            name=row['month'],
            receita=row['total_receita'],
            **row
        )
        for row in monthly_data
    ]

    chart_ticketmedio_no_tempo = [
        ChartDataPoint(
            name=row['month'],
            ticket_medio=row['avg_ticket'],
            **row
        )
        for row in monthly_data
    ]

    chart_quantidade_no_tempo = [
        ChartDataPoint(
            name=row['month'],
            quantidade=row['total_quantidade'],
            **row
        )
        for row in monthly_data
    ]

    return FornecedoresOverviewResponse(
        # ... existing fields ...
        chart_receita_no_tempo=chart_receita_no_tempo,
        chart_ticketmedio_no_tempo=chart_ticketmedio_no_tempo,
        chart_quantidade_no_tempo=chart_quantidade_no_tempo,
    )
```

#### File: `services/analytics_api/src/analytics_api/data_access/postgres_repository.py`

Add new repository methods:

```python
# Add these methods to PostgresRepository class

def get_suppliers_monthly_metrics(
    self,
    client_id: str,
    period: str = "all"
) -> list[dict]:
    """Get monthly time series data for suppliers."""

    query = """
    SELECT
        TO_CHAR(DATE_TRUNC('month', order_date), 'YYYY-MM') as month,
        SUM(total_value) as total_receita,
        AVG(total_value) as avg_ticket,
        SUM(total_quantity) as total_quantidade,
        COUNT(DISTINCT order_id) as num_pedidos
    FROM gold_orders
    WHERE client_id = :client_id
        AND (:period = 'all' OR order_date >= CURRENT_DATE - CAST(:period_days AS INTERVAL))
    GROUP BY DATE_TRUNC('month', order_date)
    ORDER BY month
    """

    period_days_map = {
        "week": "7 days",
        "month": "30 days",
        "quarter": "90 days",
        "year": "365 days",
        "all": "10000 days"  # Large number for all time
    }

    with self.engine.connect() as conn:
        result = conn.execute(
            text(query),
            {"client_id": client_id, "period": period, "period_days": period_days_map.get(period, "10000 days")}
        )
        return [dict(row) for row in result]

def get_customers_monthly_metrics(
    self,
    client_id: str,
    period: str = "all"
) -> list[dict]:
    """Get monthly time series data for customers."""
    # Similar implementation to get_suppliers_monthly_metrics
    # but grouping by receiver (customer)
    pass

def get_products_monthly_metrics(
    self,
    client_id: str,
    period: str = "all"
) -> list[dict]:
    """Get monthly time series data for products."""
    # Similar implementation grouping by product
    pass
```

---

## 🎯 Priority 2: Frontend Components (Week 2)

### Task 2.1: Create Period Selector Component

#### File: `apps/vizu_dashboard/src/components/PeriodSelector.tsx` (NEW)

```typescript
import { Select } from '@chakra-ui/react';
import React from 'react';

export type PeriodType = 'week' | 'month' | 'quarter' | 'year' | 'all';

interface PeriodSelectorProps {
  value: PeriodType;
  onChange: (period: PeriodType) => void;
  bg?: string;
}

export const PeriodSelector: React.FC<PeriodSelectorProps> = ({
  value,
  onChange,
  bg = 'white'
}) => {
  return (
    <Select
      value={value}
      onChange={(e) => onChange(e.target.value as PeriodType)}
      bg={bg}
      border="1px solid"
      borderColor="gray.200"
      borderRadius="full"
      px={6}
      py={5}
      fontSize="18px"
      fontWeight="500"
      maxW="200px"
      _hover={{ borderColor: 'gray.300' }}
    >
      <option value="week">Última semana</option>
      <option value="month">Último mês</option>
      <option value="quarter">Último trimestre</option>
      <option value="year">Último ano</option>
      <option value="all">Todo período</option>
    </Select>
  );
};
```

### Task 2.2: Create Big Number Card Component

#### File: `apps/vizu_dashboard/src/components/BigNumberCard.tsx` (NEW)

```typescript
import { Box, Text, VStack, HStack, Icon } from '@chakra-ui/react';
import { InfoOutlineIcon } from '@chakra-ui/icons';
import React from 'react';

interface BigNumberCardProps {
  label: string;
  value: number | string;
  percentChange?: number;
  showInfo?: boolean;
  bg?: string;
}

export const BigNumberCard: React.FC<BigNumberCardProps> = ({
  label,
  value,
  percentChange,
  showInfo = true,
  bg = 'white'
}) => {
  const isPositive = percentChange && percentChange > 0;

  return (
    <Box
      bg={bg}
      borderRadius="22px"
      p={6}
      minH="200px"
    >
      <VStack align="flex-start" spacing={2}>
        <HStack>
          <Text
            fontSize="16px"
            fontWeight="400"
            textTransform="uppercase"
            letterSpacing="wider"
            color="gray.700"
          >
            {label}
          </Text>
          {showInfo && (
            <Icon as={InfoOutlineIcon} w={4} h={4} color="gray.500" />
          )}
        </HStack>

        <Text
          fontSize="84px"
          fontWeight="600"
          lineHeight="1"
          color="black"
        >
          {value}
        </Text>

        {percentChange !== undefined && (
          <Text
            fontSize="44px"
            fontWeight="600"
            color={isPositive ? 'green.500' : 'red.500'}
          >
            {isPositive ? '+' : ''}{percentChange.toFixed(2)}%
          </Text>
        )}
      </VStack>
    </Box>
  );
};
```

### Task 2.3: Create Chart Carousel Component

#### File: `apps/vizu_dashboard/src/components/ChartCarousel.tsx` (NEW)

```typescript
import { Box, IconButton, HStack, Text } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';
import React, { useState } from 'react';
import { DashboardCard } from './DashboardCard';

export interface ChartItem {
  id: string;
  title: string;
  data: any;
  type?: 'line' | 'bar' | 'area';
}

interface ChartCarouselProps {
  charts: ChartItem[];
  bgColor?: string;
}

export const ChartCarousel: React.FC<ChartCarouselProps> = ({
  charts,
  bgColor = '#c9edff'
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev === 0 ? charts.length - 1 : prev - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev === charts.length - 1 ? 0 : prev + 1));
  };

  const currentChart = charts[currentIndex];

  return (
    <Box position="relative">
      <DashboardCard
        title={currentChart.title}
        size="large"
        bgColor={bgColor}
        graphData={currentChart.data}
      />

      {charts.length > 1 && (
        <HStack
          position="absolute"
          top={4}
          right={4}
          spacing={2}
          bg="white"
          borderRadius="full"
          p={1}
        >
          <IconButton
            aria-label="Previous chart"
            icon={<ChevronLeftIcon />}
            size="sm"
            variant="ghost"
            onClick={handlePrevious}
          />
          <Text fontSize="sm" fontWeight="500">
            {currentIndex + 1} / {charts.length}
          </Text>
          <IconButton
            aria-label="Next chart"
            icon={<ChevronRightIcon />}
            size="sm"
            variant="ghost"
            onClick={handleNext}
          />
        </HStack>
      )}
    </Box>
  );
};
```

### Task 2.4: Create Tier Badge Component

#### File: `apps/vizu_dashboard/src/components/TierBadge.tsx` (NEW)

```typescript
import { Badge } from '@chakra-ui/react';
import React from 'react';

interface TierBadgeProps {
  tier: string; // 'A', 'B', 'C', 'D'
  size?: 'sm' | 'md' | 'lg';
}

const tierColors: Record<string, { bg: string; color: string }> = {
  'A': { bg: 'green.100', color: 'green.800' },
  'B': { bg: 'blue.100', color: 'blue.800' },
  'C': { bg: 'orange.100', color: 'orange.800' },
  'D': { bg: 'red.100', color: 'red.800' },
};

export const TierBadge: React.FC<TierBadgeProps> = ({
  tier,
  size = 'md'
}) => {
  const colors = tierColors[tier] || tierColors['D'];

  const sizeMap = {
    sm: { fontSize: '12px', px: 2, py: 1 },
    md: { fontSize: '14px', px: 3, py: 1.5 },
    lg: { fontSize: '16px', px: 4, py: 2 },
  };

  return (
    <Badge
      bg={colors.bg}
      color={colors.color}
      borderRadius="full"
      fontWeight="600"
      textTransform="uppercase"
      {...sizeMap[size]}
    >
      Tier {tier}
    </Badge>
  );
};
```

---

## 🎯 Priority 3: Update Existing Pages (Week 3)

### Task 3.1: Enhance Fornecedores Page

#### File: `apps/vizu_dashboard/src/pages/FornecedoresPage.tsx`

Key changes needed:

```typescript
// Add imports
import { BigNumberCard } from '../components/BigNumberCard';
import { PeriodSelector, PeriodType } from '../components/PeriodSelector';
import { ChartCarousel, ChartItem } from '../components/ChartCarousel';
import { TierBadge } from '../components/TierBadge';

function FornecedoresPage() {
  // Add period state
  const [period, setPeriod] = useState<PeriodType>('month');

  // Update API call to include period
  const { data, isLoading, error, refetch } = useQuery(
    ['fornecedores', period],
    () => getFornecedores(period),
    { staleTime: 5 * 60 * 1000 }
  );

  // Prepare charts for carousel
  const charts: ChartItem[] = [
    {
      id: 'receita',
      title: 'Receita no Tempo',
      data: data?.chart_receita_no_tempo || [],
      type: 'line'
    },
    {
      id: 'ticket',
      title: 'Ticket Médio no Tempo',
      data: data?.chart_ticketmedio_no_tempo || [],
      type: 'line'
    },
    {
      id: 'quantidade',
      title: 'Volume Comercializado',
      data: data?.chart_quantidade_no_tempo || [],
      type: 'bar'
    },
  ];

  return (
    <MainLayout>
      <Flex direction="column" gap={6}>
        {/* Header with Period Selector */}
        <Flex justify="space-between" align="center">
          <Heading size="xl">Fornecedores</Heading>
          <PeriodSelector value={period} onChange={setPeriod} />
        </Flex>

        {/* Big Number Card */}
        <BigNumberCard
          label="Total Fornecedores"
          value={data?.scorecard_total_fornecedores || 0}
          percentChange={data?.scorecard_crescimento_percentual}
          bg="#92daff"
        />

        {/* Chart Carousel */}
        <ChartCarousel charts={charts} bgColor="#c9edff" />

        {/* Regional Map */}
        <DashboardCard
          title="Fornecedores por Região"
          size="large"
          mapData={{
            center: [-14.2350, -51.9253],
            zoom: 4,
            markers: data?.chart_fornecedores_por_regiao?.map(item => ({
              position: getRegionCoordinates(item.name),
              label: item.name,
              value: item.receita || 0,
            })) || [],
          }}
        />

        {/* Top Suppliers List */}
        <ListCard
          title="Top Fornecedores por Receita"
          items={data?.ranking_por_receita?.slice(0, 5).map(item => ({
            id: item.nome,
            label: item.nome,
            value: `R$ ${item.receita_total.toLocaleString('pt-BR')}`,
            badge: <TierBadge tier={item.cluster_tier} />,
            onClick: () => handleSupplierClick(item.nome),
          })) || []}
        />
      </Flex>
    </MainLayout>
  );
}
```

### Task 3.2: Update analyticsService.ts

#### File: `apps/vizu_dashboard/src/services/analyticsService.ts`

Update the service to support period parameter:

```typescript
// Update existing interfaces
export interface FornecedoresOverviewResponse {
  scorecard_total_fornecedores: number;
  scorecard_crescimento_percentual: number;

  // Add new chart fields
  chart_receita_no_tempo: ChartDataPoint[];
  chart_ticketmedio_no_tempo: ChartDataPoint[];
  chart_quantidade_no_tempo: ChartDataPoint[];

  // Existing fields...
  chart_fornecedores_no_tempo: ChartDataPoint[];
  chart_fornecedores_por_regiao: ChartDataPoint[];
  ranking_por_receita: RankingItem[];
  // ... rest
}

// Update function signatures to include period
export async function getFornecedores(
  period: string = 'month'
): Promise<FornecedoresOverviewResponse> {
  const response = await api.get(`/fornecedores?period=${period}`);
  return response.data;
}

export async function getClientes(
  period: string = 'month'
): Promise<ClientesOverviewResponse> {
  const response = await api.get(`/clientes?period=${period}`);
  return response.data;
}

export async function getProdutosOverview(
  period: string = 'month'
): Promise<ProdutosOverviewResponse> {
  const response = await api.get(`/produtos?period=${period}`);
  return response.data;
}
```

---

## 🎯 Priority 4: Detail Views Enhancement (Week 4)

### Task 4.1: Update Fornecedor Details Modal

#### File: `apps/vizu_dashboard/src/components/FornecedorDetailsModal.tsx`

Add scorecards section:

```typescript
import { TierBadge } from './TierBadge';
import { SimpleGrid, Stat, StatLabel, StatNumber } from '@chakra-ui/react';

function FornecedorDetailsModal({ fornecedor, isOpen, onClose }) {
  // ... existing code ...

  // Calculate top product
  const topProduct = fornecedor?.ranking_por_receita?.[0];
  const topRegion = fornecedor?.dados_cadastrais?.emitter_estado;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl">
      <ModalContent>
        <ModalHeader>
          <HStack>
            <Text>{fornecedor?.dados_cadastrais?.emitter_nome}</Text>
            <TierBadge tier={fornecedor?.cluster_tier || 'D'} />
          </HStack>
        </ModalHeader>

        <ModalBody>
          {/* Existing accordion section */}
          <AccordionComponent items={[...]} />

          {/* NEW: Scorecards Section */}
          <SimpleGrid columns={3} spacing={6} mt={6}>
            {/* Scorecard 1: Top Product */}
            <Stat bg="gray.50" p={4} borderRadius="md">
              <StatLabel fontSize="sm" textTransform="uppercase">
                Produto Mais Vendido
              </StatLabel>
              <StatNumber fontSize="lg">
                {topProduct?.nome || 'N/A'}
              </StatNumber>
              <Text fontSize="sm" color="gray.600">
                R$ {topProduct?.receita_total?.toLocaleString('pt-BR') || '0'}
              </Text>
            </Stat>

            {/* Scorecard 2: Top Client (requires backend update) */}
            <Stat bg="gray.50" p={4} borderRadius="md">
              <StatLabel fontSize="sm" textTransform="uppercase">
                Top Cliente
              </StatLabel>
              <StatNumber fontSize="lg">
                {/* TODO: Get from backend */}
                Instituto Reciclar
              </StatNumber>
            </Stat>

            {/* Scorecard 3: Top Region */}
            <Stat bg="gray.50" p={4} borderRadius="md">
              <StatLabel fontSize="sm" textTransform="uppercase">
                Região Principal
              </StatLabel>
              <StatNumber fontSize="lg">
                {topRegion || 'N/A'}
              </StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Charts Section (Time series - requires backend update) */}
          {/* TODO: Add chart carousel for supplier-specific time series */}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
```

---

## 🎯 Priority 5: Testing & Polish (Week 5)

### Task 5.1: Integration Testing

Create test file:

#### File: `apps/vizu_dashboard/src/tests/fornecedores-integration.test.ts` (NEW)

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FornecedoresPage from '../pages/FornecedoresPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('Fornecedores Integration', () => {
  it('should load and display fornecedores data', async () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <FornecedoresPage />
      </QueryClientProvider>
    );

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/Total Fornecedores/i)).toBeInTheDocument();
    });

    // Check big number is displayed
    expect(screen.getByText(/800/i)).toBeInTheDocument();

    // Check chart is displayed
    expect(screen.getByText(/Receita no Tempo/i)).toBeInTheDocument();
  });

  it('should update data when period changes', async () => {
    // ... test implementation
  });
});
```

### Task 5.2: Performance Optimization

Add React Query configuration:

#### File: `apps/vizu_dashboard/src/main.tsx`

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider>
        <AuthProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AuthProvider>
      </ChakraProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

---

## 📊 Progress Tracking

### Week 1: Backend API ✅ (5 days)
- [ ] Day 1-2: Add time series methods to postgres_repository.py
- [ ] Day 3: Update schema models in metrics.py
- [ ] Day 4: Update endpoint implementations in rankings.py
- [ ] Day 5: Test with Postman/curl, update API docs

### Week 2: Frontend Components ✅ (5 days)
- [ ] Day 1: Create PeriodSelector component
- [ ] Day 2: Create BigNumberCard component
- [ ] Day 3: Create ChartCarousel component
- [ ] Day 4: Create TierBadge component
- [ ] Day 5: Update component exports and documentation

### Week 3: Page Integration ✅ (5 days)
- [ ] Day 1-2: Update FornecedoresPage with new components
- [ ] Day 2-3: Update ClientesPage with new components
- [ ] Day 4-5: Update ProdutosPage with new components

### Week 4: Detail Views ✅ (5 days)
- [ ] Day 1-2: Enhance FornecedorDetailsModal
- [ ] Day 3: Enhance ClienteDetailsModal
- [ ] Day 4: Enhance ProdutoDetailsModal
- [ ] Day 5: Add time series charts to detail views

### Week 5: Testing & Polish ✅ (5 days)
- [ ] Day 1-2: Write integration tests
- [ ] Day 3: Performance optimization
- [ ] Day 4: Accessibility audit
- [ ] Day 5: Final QA and documentation

---

## 🚦 Quick Start Commands

### Start Backend Development
```bash
cd services/analytics_api
python -m pytest tests/  # Run tests
uvicorn analytics_api.main:app --reload --port 8001
```

### Start Frontend Development
```bash
cd apps/vizu_dashboard
npm install
npm run dev
```

### Test Integration
```bash
# Terminal 1: Start backend
docker compose up analytics_api

# Terminal 2: Start frontend
cd apps/vizu_dashboard && npm run dev

# Terminal 3: Run tests
cd apps/vizu_dashboard && npm test
```

---

## 📝 Notes

- All new components should follow Chakra UI patterns
- Use TypeScript for type safety
- Follow existing code style (ESLint config)
- Add JSDoc comments for complex functions
- Test with real data from BigQuery

---

This action plan provides a clear, step-by-step path to fully integrate the Figma design with your existing codebase.
