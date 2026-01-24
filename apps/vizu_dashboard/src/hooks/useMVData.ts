/**
 * Hook to fetch data from materialized views.
 * These provide fast, pre-computed aggregations for dashboard charts.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  getMVCustomers,
  getMVProducts,
  getMVMonthlySales,
  getMVDashboardSummary,
  type MVCustomersResponse,
  type MVProductsResponse,
  type MVMonthlySalesResponse,
  type MVDashboardSummary,
} from '../services/analyticsService';

// Hook for customer summary from MV
export function useMVCustomers() {
  const [data, setData] = useState<MVCustomersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getMVCustomers();
      setData(response);
    } catch (err: any) {
      console.error('Error fetching MV customers:', err);
      setError(err.message || 'Failed to load customer data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

// Hook for product summary from MV
export function useMVProducts() {
  const [data, setData] = useState<MVProductsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getMVProducts();
      setData(response);
    } catch (err: any) {
      console.error('Error fetching MV products:', err);
      setError(err.message || 'Failed to load product data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

// Hook for monthly sales trend from MV
export function useMVMonthlySales() {
  const [data, setData] = useState<MVMonthlySalesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getMVMonthlySales();
      setData(response);
    } catch (err: any) {
      console.error('Error fetching MV monthly sales:', err);
      setError(err.message || 'Failed to load monthly sales data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  // Transform data for chart compatibility
  const chartData = data?.monthly_sales.map(m => ({
    name: m.month,
    revenue: m.revenue,
    orders: m.orders,
    customers: m.unique_customers,
    avgOrderValue: m.avg_order_value,
    // Generic 'total' for simple charts
    total: m.revenue,
  })) || [];

  return { data, chartData, loading, error, refetch };
}

// Hook for complete dashboard summary from MVs
export function useMVDashboardSummary() {
  const [data, setData] = useState<MVDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getMVDashboardSummary();
      setData(response);
    } catch (err: any) {
      console.error('Error fetching MV dashboard summary:', err);
      setError(err.message || 'Failed to load dashboard summary');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  // Transform monthly trend for chart compatibility
  const revenueChartData = data?.monthly_trend.map(m => ({
    name: m.month,
    value: m.revenue,
    total: m.revenue,
  })) || [];

  const ordersChartData = data?.monthly_trend.map(m => ({
    name: m.month,
    value: m.orders,
    total: m.orders,
  })) || [];

  const customersChartData = data?.monthly_trend.map(m => ({
    name: m.month,
    value: m.unique_customers,
    total: m.unique_customers,
  })) || [];

  return {
    data,
    revenueChartData,
    ordersChartData,
    customersChartData,
    loading,
    error,
    refetch,
  };
}
