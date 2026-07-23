import { fmtNumero } from '../formato'
import { evaluar } from '../calculo'

// Carga de una cantidad de producto terminado en PAQUETES + BOTELLAS sueltas
// (mejora 6.13), con la suma en botellas mostrada al lado, no editable.
//
// Por que la suma no es estado propio: el total en botellas es lo unico que
// viaja al backend, y ademas alimenta el precio sugerido, la ganancia por
// linea y el prorrateo del taxi en Ventas (6.12). Si se guardara como un
// tercer estado habria que sincronizarlo en cada cambio, y el dia que se
// desincronice los calculos se rompen sin ningun error visible. Por eso se
// deriva SIEMPRE con totalBotellas() en el render.
//
// En productos sueltos (botellasPorPaquete <= 1) el paquete ES la botella:
// se muestra un solo campo y ninguna suma, porque "5 paquetes + 1 botella =
// 6" no significa nada util cuando el paquete trae una sola.
export function totalBotellas(paquetes, botellas, botellasPorPaquete) {
  // Los campos aceptan operaciones (ej. "45*3", item 11): se evalúan en vez de
  // parseFloat. NaN (vacío o expresión inválida) cuenta como 0.
  const num = (t) => { const v = evaluar(t); return Number.isNaN(v) ? 0 : v }
  const b = num(botellas)
  // Producto suelto: el campo de paquetes esta oculto, asi que un valor que
  // haya quedado ahi (de otro producto elegido antes) no debe sumar en
  // silencio: el usuario no puede verlo ni corregirlo.
  if (!botellasPorPaquete || botellasPorPaquete <= 1) return b
  return num(paquetes) * botellasPorPaquete + b
}

function CantidadPaquetes({
  botellasPorPaquete,
  paquetes,
  botellas,
  onCambiarPaquetes,
  onCambiarBotellas,
  etiquetaBotellas = 'Botellas sueltas',
}) {
  const suelto = !botellasPorPaquete || botellasPorPaquete <= 1
  const total = totalBotellas(paquetes, botellas, botellasPorPaquete)

  if (suelto) {
    return (
      <input type="text" placeholder="Cantidad (botellas)"
        value={botellas} onChange={(e) => onCambiarBotellas(e.target.value)} />
    )
  }

  return (
    <>
      <input type="text" placeholder="Paquetes"
        value={paquetes} onChange={(e) => onCambiarPaquetes(e.target.value)}
        style={{ width: '6rem' }} />
      <input type="text" placeholder={etiquetaBotellas}
        value={botellas} onChange={(e) => onCambiarBotellas(e.target.value)}
        style={{ width: '7rem' }} />
      <span style={{ marginLeft: '0.4rem', color: '#557' }}>
        = <strong>{fmtNumero(total)}</strong> botellas
        <span style={{ fontSize: '0.85em' }}> (paquete de {botellasPorPaquete})</span>
      </span>
    </>
  )
}

export default CantidadPaquetes
