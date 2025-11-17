import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ChartsPage from './pages/ChartsPage';
import SettingsPage from './pages/SettingsPage';
import FornecedoresPage from './pages/FornecedoresPage';
import ProdutosPage from './pages/ProdutosPage';
import PedidosPage from './pages/PedidosPage';
import PedidosListPage from './pages/PedidosListPage';
import ProdutosListPage from './pages/ProdutosListPage'; // New import
import FornecedoresListPage from './pages/FornecedoresListPage'; // New import

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/charts" element={<ChartsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/fornecedores" element={<FornecedoresPage />} />
      <Route path="/fornecedores/lista" element={<FornecedoresListPage />} /> {/* New route */}
      <Route path="/produtos" element={<ProdutosPage />} />
      <Route path="/produtos/lista" element={<ProdutosListPage />} /> {/* New route */}
      <Route path="/pedidos" element={<PedidosPage />} />
      <Route path="/pedidos/lista" element={<PedidosListPage />} />
    </Routes>
  );
}

export default App;