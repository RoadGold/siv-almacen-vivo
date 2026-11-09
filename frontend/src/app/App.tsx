import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './layout/Layout';
import { RutaPrivada } from './layout/RutaPrivada';
import { Acceso } from '@/features/acceso/Acceso';
import { Inicio } from '@/features/inicio/Inicio';
import { Vender } from '@/features/vender/Vender';
import { Recibir } from '@/features/recibir/Recibir';
import { Explorar } from '@/features/explorar/Explorar';
import { Kardex } from '@/features/kardex/Kardex';
import { Productos } from '@/features/productos/Productos';
import { Proveedores } from '@/features/proveedores/Proveedores';
import { Analizar } from '@/features/analizar/Analizar';
import { Administrar } from '@/features/administracion/Administrar';
import { NoEncontrado } from '@/features/comunes/NoEncontrado';

/** Mapa de rutas de SIV · Almacén Vivo (plan §3). */
export function Rutas() {
  return (
    <Routes>
      <Route path="/login" element={<Acceso />} />

      <Route
        element={
          <RutaPrivada>
            <Layout />
          </RutaPrivada>
        }
      >
        <Route path="/" element={<Inicio />} />
        <Route path="/vender" element={<Vender />} />
        <Route path="/recibir" element={<Recibir />} />
        <Route path="/explorar" element={<Explorar />} />
        <Route path="/kardex" element={<Kardex />} />
        <Route path="/gestionar/productos" element={<Productos />} />
        <Route path="/gestionar/proveedores" element={<Proveedores />} />
        <Route path="/analizar" element={<Analizar />} />
        <Route path="/administrar" element={<Administrar />} />
        <Route path="/index.html" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NoEncontrado />} />
      </Route>
    </Routes>
  );
}
