import { evaluar } from '../calculo'
import { fmtNumero } from '../formato'

// Caja de texto que además acepta operaciones (ej. "45*3", "500*0.25") y muestra
// el resultado en vivo (items 2 y 11). El valor que maneja el padre sigue siendo
// el TEXTO crudo; el padre lo evalúa con evaluar() al enviarlo o calcular. El
// "= resultado" solo aparece cuando el texto tiene algún operador, para no
// repetir un número plano. Reemplaza a los <input> numéricos de cantidades y
// precios en los formularios.
function InputCalculo({ value, onChange, placeholder, width = '7rem', style, decimales = 6 }) {
  const tieneOperacion = /[+\-*/()]/.test(String(value))
  const resultado = evaluar(value)
  return (
    <>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ width, ...style }}
      />
      {tieneOperacion && (
        <span style={{ marginLeft: '0.3rem', color: Number.isNaN(resultado) ? '#a00' : '#557', fontSize: '0.85em' }}>
          {Number.isNaN(resultado) ? '= (inválido)' : `= ${fmtNumero(resultado, decimales)}`}
        </span>
      )}
    </>
  )
}

export default InputCalculo
