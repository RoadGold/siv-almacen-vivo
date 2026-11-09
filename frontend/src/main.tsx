import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { Rutas } from './app/App';
import { ProveedoresApp } from './app/proveedores';
import './design-system/base.css';

/*
 * Se usa `HashRouter` porque el backend sirve `frontend/dist` con
 * `StaticFiles(html=True)`, que no aplica el «fallback» de las aplicaciones de
 * una sola página: sin hash, una recarga en `/vender` devolvería un 404.
 * Si el backend añade una ruta comodín que devuelva `index.html`, puede
 * cambiarse por `BrowserRouter` sin tocar el resto de la aplicación.
 */
const contenedor = document.getElementById('raiz');
if (!contenedor) {
  throw new Error('No se encontró el contenedor raíz «raiz» en index.html.');
}

createRoot(contenedor).render(
  <StrictMode>
    <HashRouter>
      <ProveedoresApp>
        <Rutas />
      </ProveedoresApp>
    </HashRouter>
  </StrictMode>,
);
