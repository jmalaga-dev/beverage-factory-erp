import { Component } from 'react'

// Error boundary (mejora 6.15): atrapa un error de render de la pantalla
// activa y muestra un cartel en su lugar, en vez de dejar que React
// desmonte TODO el arbol (que borraba hasta el menu y dejaba la app muda,
// sin forma de navegar a otra pantalla).
//
// Tiene que ser una clase: React no expone los hooks de error boundary a los
// componentes de funcion. Es el unico componente de clase del proyecto.
//
// La `clave` cambia con la ruta: al navegar a otra pantalla se resetea el
// estado de error, para que una pantalla rota no deje el cartel pegado sobre
// las demas.
class LimiteError extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidUpdate(prevProps) {
    if (prevProps.clave !== this.props.clave && this.state.error) {
      this.setState({ error: null })
    }
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div style={{
        border: '1px solid #c00', background: '#fee', color: '#900',
        padding: '1rem', margin: '1rem 0', textAlign: 'left',
      }}>
        <h3 style={{ marginTop: 0 }}>Esta pantalla falló</h3>
        <p>
          El resto de la aplicación sigue funcionando: podés usar el menú de
          arriba para ir a otra pantalla. Nada de lo que hayas registrado antes
          se perdió — el error es de la pantalla, no de los datos.
        </p>
        <p style={{ fontSize: '0.85em' }}>
          Si el error se repite, este es el detalle técnico (sirve para
          reportarlo):
        </p>
        <pre style={{
          whiteSpace: 'pre-wrap', fontSize: '0.8em',
          background: '#fff', padding: '0.5rem', border: '1px solid #e99',
        }}>
          {String(this.state.error && (this.state.error.stack || this.state.error.message))}
        </pre>
      </div>
    )
  }
}

export default LimiteError
