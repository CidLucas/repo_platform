import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Input,
  HStack,
  VStack,
  IconButton,
  Text,
  Flex,
  Tooltip,
  useToast,
  useColorModeValue,
  Card,
  CardBody,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  Portal,
} from '@chakra-ui/react';
import {
  TriangleDownIcon,
  TriangleUpIcon,
  DownloadIcon,
  CopyIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@chakra-ui/icons';
import { useState, useMemo } from 'react';
import { FaGoogle } from 'react-icons/fa';

// Types matching backend StructuredDataResponse
export type ColumnType = 'string' | 'number' | 'date' | 'datetime' | 'boolean' | 'currency';

export interface Column {
  key: string;
  label: string;
  type: ColumnType;
  sortable?: boolean;
  filterable?: boolean;
  width?: number;
}

export interface StructuredData {
  columns: Column[];
  rows: Record<string, unknown>[];
  total_rows: number;
  title?: string;
  summary?: string;
  export_id?: string;
  has_more?: boolean;
}

interface SimpleDataTableProps {
  data: StructuredData;
  onExportToSheets?: () => void;
  maxHeight?: string;
}

// Card view for mobile
interface DataCardProps {
  row: Record<string, unknown>;
  columns: Column[];
  formatValue: (value: unknown, type: ColumnType) => string;
}

const DataCard = ({ row, columns, formatValue }: DataCardProps) => {
  const cardBg = useColorModeValue('white', 'gray.700');
  const labelColor = useColorModeValue('gray.500', 'gray.400');

  return (
    <Card bg={cardBg} size="sm" variant="outline">
      <CardBody py={3} px={4}>
        <VStack align="stretch" spacing={2}>
          {columns.map((col) => (
            <Flex key={col.key} justify="space-between" align="center">
              <Text fontSize="xs" color={labelColor} fontWeight="500">
                {col.label}
              </Text>
              <Text fontSize="sm" fontWeight="400" textAlign="right" maxW="60%">
                {formatValue(row[col.key], col.type)}
              </Text>
            </Flex>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};

// Filter icon component (three descending horizontal lines)
const FilterIcon = ({ isActive }: { isActive: boolean }) => {
  const activeColor = useColorModeValue('blue.500', 'blue.300');
  const inactiveColor = useColorModeValue('gray.400', 'gray.500');
  const color = isActive ? activeColor : inactiveColor;

  return (
    <Box as="svg" viewBox="0 0 16 16" w="14px" h="14px" fill={color}>
      <rect x="1" y="3" width="14" height="2" rx="0.5" />
      <rect x="3" y="7" width="10" height="2" rx="0.5" />
      <rect x="5" y="11" width="6" height="2" rx="0.5" />
    </Box>
  );
};

export const SimpleDataTable = ({
  data,
  onExportToSheets,
  maxHeight = '400px',
}: SimpleDataTableProps) => {
  const toast = useToast();

  // Theme colors
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const headerBg = useColorModeValue('gray.50', 'gray.700');
  const hoverBg = useColorModeValue('gray.50', 'gray.600');
  const tableBg = useColorModeValue('white', 'gray.800');

  // Sorting state
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Filtering state
  const [filters, setFilters] = useState<Record<string, string>>({});

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // Filter rows
  const filteredRows = useMemo(() => {
    return data.rows.filter((row) => {
      return Object.entries(filters).every(([key, value]) => {
        if (!value) return true;
        const cellValue = String(row[key] ?? '').toLowerCase();
        return cellValue.includes(value.toLowerCase());
      });
    });
  }, [data.rows, filters]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows;

    return [...filteredRows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle nulls
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortDirection === 'asc' ? 1 : -1;
      if (bVal == null) return sortDirection === 'asc' ? -1 : 1;

      // Compare based on type
      const column = data.columns.find((c) => c.key === sortColumn);
      if (column?.type === 'number' || column?.type === 'currency') {
        return sortDirection === 'asc'
          ? Number(aVal) - Number(bVal)
          : Number(bVal) - Number(aVal);
      }

      return sortDirection === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
  }, [filteredRows, sortColumn, sortDirection, data.columns]);

  // Paginate rows
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, currentPage, pageSize]);

  const totalPages = Math.ceil(sortedRows.length / pageSize);

  // Handlers
  const handleSort = (columnKey: string) => {
    const column = data.columns.find((c) => c.key === columnKey);
    if (column?.sortable === false) return;

    if (sortColumn === columnKey) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  const handleFilterChange = (columnKey: string, value: string) => {
    setFilters((prev) => ({ ...prev, [columnKey]: value }));
    setCurrentPage(1);
  };

  const formatCellValue = (value: unknown, type: ColumnType): string => {
    if (value == null) return '-';

    switch (type) {
      case 'currency':
        return new Intl.NumberFormat('pt-BR', {
          style: 'currency',
          currency: 'BRL',
        }).format(Number(value));
      case 'number':
        return new Intl.NumberFormat('pt-BR').format(Number(value));
      case 'date':
        return new Date(String(value)).toLocaleDateString('pt-BR');
      case 'datetime':
        return new Date(String(value)).toLocaleString('pt-BR');
      case 'boolean':
        return value ? 'Sim' : 'Não';
      default:
        return String(value);
    }
  };

  // Export functions
  const copyToClipboard = async () => {
    const headers = data.columns.map((c) => c.label).join('\t');
    const rows = sortedRows
      .map((row) => data.columns.map((c) => row[c.key] ?? '').join('\t'))
      .join('\n');

    await navigator.clipboard.writeText(`${headers}\n${rows}`);
    toast({
      title: 'Copiado!',
      description: 'Dados copiados para a área de transferência',
      status: 'success',
      duration: 2000,
    });
  };

  const downloadCSV = () => {
    const headers = data.columns.map((c) => c.label).join(',');
    const rows = sortedRows
      .map((row) =>
        data.columns
          .map((c) => {
            const val = row[c.key] ?? '';
            // Escape commas and quotes in CSV
            return `"${String(val).replace(/"/g, '""')}"`;
          })
          .join(',')
      )
      .join('\n');

    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${data.title?.replace(/[^a-z0-9]/gi, '_') || 'dados'}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    toast({
      title: 'Download iniciado',
      status: 'success',
      duration: 2000,
    });
  };

  // Check if any filter is active
  const hasActiveFilters = Object.values(filters).some((v) => v.length > 0);

  return (
    <Box
      borderRadius="lg"
      border="1px solid"
      borderColor={borderColor}
      overflow="hidden"
      bg={tableBg}
      w="100%"
    >
      {/* Desktop Table View */}
      <Box display={{ base: 'none', md: 'block' }} overflowX="auto" maxH={maxHeight} overflowY="auto">
        <Table size="sm" variant="simple">
          <Thead position="sticky" top={0} bg={tableBg} zIndex={1}>
            {/* Header row with filter icons */}
            <Tr>
              {data.columns.map((col) => (
                <Th
                  key={col.key}
                  cursor={col.sortable !== false ? 'pointer' : 'default'}
                  _hover={col.sortable !== false ? { bg: hoverBg } : undefined}
                  whiteSpace="nowrap"
                  userSelect="none"
                  py={2}
                >
                  <HStack spacing={2} justify="space-between">
                    <HStack
                      spacing={1}
                      onClick={() => handleSort(col.key)}
                      flex={1}
                    >
                      <Text>{col.label}</Text>
                      {sortColumn === col.key &&
                        (sortDirection === 'asc' ? (
                          <TriangleUpIcon boxSize={3} />
                        ) : (
                          <TriangleDownIcon boxSize={3} />
                        ))}
                    </HStack>
                    {col.filterable !== false && (
                      <Popover placement="bottom-end" isLazy>
                        <PopoverTrigger>
                          <Box
                            as="button"
                            p={1}
                            borderRadius="sm"
                            _hover={{ bg: hoverBg }}
                            onClick={(e: React.MouseEvent) => e.stopPropagation()}
                          >
                            <FilterIcon isActive={!!filters[col.key]} />
                          </Box>
                        </PopoverTrigger>
                        <Portal>
                          <PopoverContent w="200px">
                            <PopoverBody p={2}>
                              <Input
                                size="sm"
                                placeholder={`Filtrar ${col.label}...`}
                                value={filters[col.key] || ''}
                                onChange={(e) => handleFilterChange(col.key, e.target.value)}
                                autoFocus
                              />
                            </PopoverBody>
                          </PopoverContent>
                        </Portal>
                      </Popover>
                    )}
                  </HStack>
                </Th>
              ))}
            </Tr>
          </Thead>
          <Tbody>
            {paginatedRows.map((row, idx) => (
              <Tr key={idx} _hover={{ bg: hoverBg }}>
                {data.columns.map((col) => (
                  <Td key={col.key} whiteSpace="nowrap">
                    {formatCellValue(row[col.key], col.type)}
                  </Td>
                ))}
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {/* Mobile Card View */}
      <Box display={{ base: 'block', md: 'none' }} maxH={maxHeight} overflowY="auto" p={2}>
        <VStack spacing={2} align="stretch">
          {paginatedRows.map((row, idx) => (
            <DataCard key={idx} row={row} columns={data.columns} formatValue={formatCellValue} />
          ))}
        </VStack>
      </Box>

      {/* Footer with pagination and export icons */}
      <Flex
        justify="space-between"
        align="center"
        p={2}
        borderTop="1px solid"
        borderColor={borderColor}
        bg={headerBg}
        flexWrap="wrap"
        gap={2}
      >
        {/* Row count and active filters info */}
        <HStack spacing={2}>
          <Text fontSize="xs" color="gray.500">
            {sortedRows.length > pageSize ? (
              <>
                {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, sortedRows.length)}{' '}
                de {sortedRows.length}
              </>
            ) : (
              <>{sortedRows.length} {sortedRows.length === 1 ? 'registro' : 'registros'}</>
            )}
            {hasActiveFilters && ` (filtrado de ${data.rows.length})`}
          </Text>
        </HStack>

        {/* Center: Pagination (only if needed) */}
        {sortedRows.length > pageSize && (
          <HStack spacing={1}>
            <IconButton
              aria-label="Página anterior"
              icon={<ChevronLeftIcon />}
              size="xs"
              variant="ghost"
              isDisabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => p - 1)}
            />
            <Text fontSize="xs" color="gray.500" minW="50px" textAlign="center">
              {currentPage} / {totalPages}
            </Text>
            <IconButton
              aria-label="Próxima página"
              icon={<ChevronRightIcon />}
              size="xs"
              variant="ghost"
              isDisabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => p + 1)}
            />
          </HStack>
        )}

        {/* Right: Export icons */}
        <HStack spacing={1}>
          <Tooltip label="Copiar para área de transferência" placement="top">
            <IconButton
              aria-label="Copiar"
              icon={<CopyIcon />}
              size="xs"
              variant="ghost"
              onClick={copyToClipboard}
            />
          </Tooltip>
          <Tooltip label="Baixar CSV" placement="top">
            <IconButton
              aria-label="Download CSV"
              icon={<DownloadIcon />}
              size="xs"
              variant="ghost"
              onClick={downloadCSV}
            />
          </Tooltip>
          {onExportToSheets && (
            <Tooltip label="Exportar para Google Sheets" placement="top">
              <IconButton
                aria-label="Google Sheets"
                icon={<FaGoogle />}
                size="xs"
                variant="ghost"
                onClick={onExportToSheets}
              />
            </Tooltip>
          )}
        </HStack>
      </Flex>
    </Box>
  );
};

export default SimpleDataTable;
