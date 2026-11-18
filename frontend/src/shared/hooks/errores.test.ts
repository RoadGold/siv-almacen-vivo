/**
 * El error por campo: el backend dice qué falló y el cliente lo muestra
 * bajo el control correspondiente.
 */

import { describe, expect, it } from 'vitest';
import { ErrorApi } from '../api/client';
import { erroresPorCampo, mensajeDeCampo, mensajeDeError } from './errores';

/** Error de validación tal como lo manda el backend. */
function errorDeValidacion(campos: { loc: (string | number)[]; msg: string }[]): ErrorApi {
  return new ErrorApi(
    'validacion',
    'Los datos enviados no son válidos.',
    { campos },
    422,
  );
}

describe('errores por campo', () => {
  it('devuelve el mensaje de cada campo que falló', () => {
    const error = errorDeValidacion([
      { loc: ['body', 'ruc'], msg: 'El RUC debe tener 11 dígitos.' },
      { loc: ['body', 'email'], msg: 'El correo no es válido.' },
    ]);

    expect(erroresPorCampo(error)).toEqual({
      ruc: 'El RUC debe tener 11 dígitos.',
      email: 'El correo no es válido.',
    });
  });

  it('usa el último tramo de la ruta, para las líneas del carrito', () => {
    const error = errorDeValidacion([
      { loc: ['body', 'lineas', 0, 'cantidad'], msg: 'La cantidad debe ser mayor que cero.' },
    ]);

    expect(erroresPorCampo(error)).toEqual({
      cantidad: 'La cantidad debe ser mayor que cero.',
    });
  });

  it('devuelve el mensaje de un campo concreto', () => {
    const error = errorDeValidacion([
      { loc: ['body', 'codigo'], msg: 'El código no puede pasar de 40 caracteres.' },
    ]);

    expect(mensajeDeCampo(error, 'codigo')).toBe('El código no puede pasar de 40 caracteres.');
    expect(mensajeDeCampo(error, 'nombre')).toBeUndefined();
  });

  it('no se rompe con errores que no traen detalle', () => {
    expect(erroresPorCampo(new Error('algo falló'))).toEqual({});
    expect(erroresPorCampo(new ErrorApi('error', 'mensaje', {}, 500))).toEqual({});
    expect(mensajeDeCampo(new ErrorApi('error', 'mensaje', {}, 500), 'campo')).toBeUndefined();
  });

  it('ignora los campos sin nombre', () => {
    const error = errorDeValidacion([{ loc: [], msg: 'sin campo' }]);
    expect(erroresPorCampo(error)).toEqual({});
  });

  it('mantiene el primer mensaje cuando un campo falla dos veces', () => {
    const error = errorDeValidacion([
      { loc: ['body', 'nombre'], msg: 'primer aviso' },
      { loc: ['body', 'nombre'], msg: 'segundo aviso' },
    ]);

    expect(erroresPorCampo(error).nombre).toBe('primer aviso');
  });

  it('el mensaje general sigue disponible', () => {
    const error = errorDeValidacion([{ loc: ['body', 'ruc'], msg: 'El RUC debe tener 11 dígitos.' }]);
    expect(mensajeDeError(error)).toBe('Los datos enviados no son válidos.');
  });
});
