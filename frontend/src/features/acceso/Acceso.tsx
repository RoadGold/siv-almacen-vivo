import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { Button, Field, Input, InterruptorTema, Notice } from '@/design-system';
import { useAutenticacion } from '@/shared/auth/ProveedorAutenticacion';
import { ErrorApi } from '@/shared/api/client';
import { errorDeLongitud, reglaDe } from '@/shared/contrato/reglas';

/**
 * Pantalla de acceso al sistema.
 * Guarda el token y los datos del usuario y devuelve al inicio.
 */
export function Acceso() {
  const { iniciarSesion, usuario } = useAutenticacion();
  const navegar = useNavigate();
  const ubicacion = useLocation();

  const [nombreUsuario, setNombreUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const destino = (ubicacion.state as { desde?: string } | null)?.desde ?? '/';

  if (usuario) {
    return <Navigate to={destino} replace />;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);

    // Las mismas reglas que aplica el backend (ver `LoginRequest`).
    const usuario = nombreUsuario.trim();
    const errorUsuario = errorDeLongitud(usuario, reglaDe('acceso', 'usuario'), 'El usuario');
    if (errorUsuario) {
      setError(errorUsuario);
      return;
    }
    const errorClave = errorDeLongitud(clave, reglaDe('acceso', 'password'), 'La contraseña');
    if (errorClave) {
      setError(errorClave);
      return;
    }

    setEnviando(true);
    try {
      await iniciarSesion(usuario, clave);
      navegar(destino, { replace: true });
    } catch (excepcion) {
      if (excepcion instanceof ErrorApi && excepcion.estado === 401) {
        setError('Usuario o contraseña incorrectos. Intente nuevamente.');
      } else if (excepcion instanceof ErrorApi) {
        setError(excepcion.mensaje);
      } else {
        setError('No se pudo completar el acceso. Intente nuevamente.');
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-4 flex justify-end">
          <InterruptorTema />
        </div>
        <div className="mb-6 text-center">
          <span
            aria-hidden="true"
            className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-[8px] bg-brand text-lg font-bold text-white"
          >
            SV
          </span>
          <h1 className="text-xl font-bold uppercase tracking-[0.16em] text-ink">
            SIV · Almacén Vivo
          </h1>
          <p className="mt-1 text-sm text-muted">Sistema local de inventario y ventas</p>
        </div>

        <form
          onSubmit={enviar}
          className="rounded-tarjeta border border-linea bg-surface px-6 py-6 shadow-panel"
          noValidate
        >
          <h2 className="mb-4 text-base font-semibold text-ink">Acceso al sistema</h2>

          {error ? (
            <div className="mb-4">
              <Notice tono="error" titulo="No se pudo iniciar la sesión">
                {error}
              </Notice>
            </div>
          ) : null}

          <div className="flex flex-col gap-4">
            <Field htmlFor="usuario" etiqueta="Usuario" ejemplo="vendedor1" obligatorio>
              <Input
                id="usuario"
                name="usuario"
                autoComplete="username"
                autoFocus
                required
                value={nombreUsuario}
                onChange={(evento) => setNombreUsuario(evento.target.value)}
              />
            </Field>

            <Field htmlFor="clave" etiqueta="Contraseña" ejemplo="••••••••" obligatorio>
              <Input
                id="clave"
                name="clave"
                type="password"
                autoComplete="current-password"
                required
                value={clave}
                onChange={(evento) => setClave(evento.target.value)}
              />
            </Field>

            <Button
              type="submit"
              variante="primario"
              tamano="lg"
              anchoCompleto
              cargando={enviando}
              textoCargando="Comprobando…"
            >
              Entrar al sistema
            </Button>
          </div>
        </form>

        <p className="mt-4 text-center text-xs text-muted">
          El sistema funciona sin conexión a internet. Debe estar encendido el servidor local.
        </p>
      </div>
    </div>
  );
}
