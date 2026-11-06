# language: es

Característica: Coordinación integral de Eventos Nova

  @US01
  Escenario: US01 criterio 1
    Dado un cliente activo, fecha futura y servicios habilitados
    Cuando el Coordinador registra el evento
    Entonces se conserva el evento BORRADOR y la propuesta V1.0 con el total decimal

  @US01
  Escenario: US01 criterio 2
    Dado un aforo de cero
    Cuando se intenta registrar el evento
    Entonces la API responde 422 y no persiste el alta

  @US02
  Escenario: US02 criterio 1
    Dado una propuesta ENVIADA del Cliente autenticado
    Cuando el Cliente acepta
    Entonces la propuesta queda ACEPTADA y el evento ACEPTADO

  @US02
  Escenario: US02 criterio 2
    Dado una propuesta ya aceptada
    Cuando el Cliente vuelve a aceptar
    Entonces la API responde 409

  @US03
  Escenario: US03 criterio 1
    Dado un contrato firmado por 1000.00 MXN
    Cuando Administración registra 300.00 MXN
    Entonces el evento pasa a CONFIRMADO

  @US03
  Escenario: US03 criterio 2
    Dado un contrato firmado por 1000.00 MXN
    Cuando se registran 299.99 MXN
    Entonces el evento permanece ACEPTADO

  @US04
  Escenario: US04 criterio 1
    Dado un evento CONFIRMADO y proveedor activo
    Cuando Coordinación solicita el servicio
    Entonces se crea solicitud PENDIENTE y evento con destinatario y vencimiento

  @US04
  Escenario: US04 criterio 2
    Dado un evento BORRADOR
    Cuando Coordinación intenta asignar proveedor
    Entonces la API responde 409

  @US05
  Escenario: US05 criterio 1
    Dado una solicitud PENDIENTE de mi identidad y menos de 48 horas
    Cuando respondo que acepto
    Entonces la solicitud pasa a CONFIRMADO y se reserva la fecha

  @US05
  Escenario: US05 criterio 2
    Dado 48 horas exactas desde el envío
    Cuando intento aceptar
    Entonces la API responde 422 por vencimiento

  @US06
  Escenario: US06 criterio 1
    Dado una solicitud PENDIENTE con 48 horas cumplidas
    Cuando el temporizador ejecuta su revisión
    Entonces la solicitud pasa a EXPIRADO y queda alerta interna a Coordinación

  @US06
  Escenario: US06 criterio 2
    Dado una solicitud ya expirada
    Cuando se revisa nuevamente
    Entonces no se duplica la alerta

  @US07
  Escenario: US07 criterio 1
    Dado una propuesta BORRADOR V1.0
    Cuando Coordinación cambia servicios con motivo
    Entonces se agrega V1.1 sin modificar V1.0

  @US07
  Escenario: US07 criterio 2
    Dado una propuesta ENVIADA
    Cuando se intenta editar directamente
    Entonces se rechaza la modificación hasta resolver la propuesta

  @US08
  Escenario: US08 criterio 1
    Dado un proveedor asignado al evento
    Cuando se aplica un cambio de horario o menú
    Entonces CambioAplicado conserva la nueva versión y el proveedor como destinatario

  @US08
  Escenario: US08 criterio 2
    Dado un error antes del commit
    Cuando falla la actualización de propuesta
    Entonces evento, propuesta y notificación se revierten juntos

  @US09
  Escenario: US09 criterio 1
    Dado un evento a 15 días naturales o más
    Cuando el Cliente solicita aumentar invitados
    Entonces se calcula recargo 0.00 y espera revisión comercial

  @US09
  Escenario: US09 criterio 2
    Dado una cotización revisada de un cambio dentro de plazo
    Cuando Administración la autoriza
    Entonces se actualizan aforo y versión sin penalización

  @US10
  Escenario: US10 criterio 1
    Dado un evento a 14 días con incremento de 100.00 MXN
    Cuando se solicita el cambio
    Entonces queda PENDIENTE con cargo calculado de 15.00 MXN sin cambiar aún el total

  @US10
  Escenario: US10 criterio 2
    Dado un cambio tardío pendiente
    Cuando Administración autoriza
    Entonces se aplican incremento y cargo con responsable y nueva versión

  @US11
  Escenario: US11 criterio 1
    Dado un proveedor CONFIRMADO
    Cuando el Proveedor cancela con motivo
    Entonces se libera su reserva y se devuelve la lista Backup activa

  @US11
  Escenario: US11 criterio 2
    Dado una solicitud cancelada y proveedor Backup activo
    Cuando Coordinación registra su sustitución
    Entonces la nueva solicitud conserva el identificador de la anterior

  @US12
  Escenario: US12 criterio 1
    Dado un total de 5990.00 y proveedores por 1000.00 MXN
    Cuando Administración consulta rentabilidad
    Entonces obtiene margen de 4990.00 MXN e importes cobrados por separado

  @US12
  Escenario: US12 criterio 2
    Dado un Cliente autenticado
    Cuando intenta consultar la rentabilidad
    Entonces la API responde 403

  @US13
  Escenario: US13 criterio 1
    Dado un evento EN_EJECUCION y adicional registrado
    Cuando Administración registra su pago específico por terminal
    Entonces el adicional queda pagado y puede prestarse

  @US13
  Escenario: US13 criterio 2
    Dado un adicional sin pago
    Cuando Coordinación intenta marcarlo prestado
    Entonces la API responde 422

  @US14
  Escenario: US14 criterio 1
    Dado un evento FINALIZADO con saldo de 4123.00 MXN
    Cuando Administración registra 4123.00 MXN
    Entonces el saldo queda en 0.00 sin duplicar el anticipo

  @US14
  Escenario: US14 criterio 2
    Dado un saldo de 4123.00 MXN
    Cuando se intenta registrar un pago de 4123.01 MXN
    Entonces la API responde 422

  @US15
  Escenario: US15 criterio 1
    Dado un evento FINALIZADO sin saldo ni pendientes
    Cuando Coordinación registra el acta de cierre
    Entonces el estado queda CERRADO con fecha y responsable

  @US15
  Escenario: US15 criterio 2
    Dado un evento con saldo pendiente
    Cuando se intenta cerrar
    Entonces la API responde 422 y conserva su estado