from flask import Flask, request, Response
from flask_cors import CORS
import pika
import uuid
from lxml import etree
import json

app = Flask(__name__)
CORS(app)

PERMISOS = {
    "validar_token": ["admin", "editor", "lector"],
    "crear_base": ["admin"],
    "eliminar_base": ["admin"],                # Nueva operación
    "crear_tabla": ["admin", "editor"],
    "eliminar_tabla": ["admin", "editor"],    # Nueva operación
    "insertar_registro": ["admin", "editor"],
    "modificar_registro": ["admin", "editor"],# Nueva operación
    "eliminar_registro": ["admin", "editor"], # Nueva operación
    "listar_bases": ["admin", "editor", "lector"],
    "listar_tablas": ["admin", "editor", "lector"],
    "consultar": ["admin", "editor", "lector"],
    "listar_usuarios": ["admin", "editor"],
    "cambiar_rol": ["admin"],
    "listAll": ["admin", "editor", "lector"]
}

def enviar_y_esperar_respuesta(queue_name, mensaje):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name)

    correlation_id = str(uuid.uuid4())
    respuesta = None

    def callback(ch, method, properties, body):
        nonlocal respuesta
        if properties.correlation_id == correlation_id:
            print(f"[RabbitMQ] Respuesta recibida en cola '{queue_name}': {body.decode()}")
            respuesta = body.decode()

    result = channel.queue_declare(queue='', exclusive=True)
    callback_queue = result.method.queue

    channel.basic_consume(queue=callback_queue, on_message_callback=callback, auto_ack=True)

    print(f"[RabbitMQ] Publicando mensaje en cola '{queue_name}' con correlation_id {correlation_id}")
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        properties=pika.BasicProperties(
            reply_to=callback_queue,
            correlation_id=correlation_id
        ),
        body=mensaje
    )
    print(f"[RabbitMQ] Mensaje publicado en cola '{queue_name}'")

    while respuesta is None:
        connection.process_data_events()

    connection.close()
    return respuesta

@app.route('/', methods=['POST'])
def recibir_peticion():
    try:
        xml = request.data
        tree = etree.fromstring(xml)
        body = tree.xpath('//soap:Body', namespaces={'soap': 'http://schemas.xmlsoap.org/soap/envelope/'})[0]

        operacion = etree.QName(body[0]).localname
        print(f"[ORQUESTADOR] Operación recibida: {operacion}")
        token = body[0].findtext('token')
        interfaz = body[0].findtext('interfaz') or "sql"

        print(f"[ORQUESTADOR] Interfaz seleccionada: {interfaz}")
        print(f"[ORQUESTADOR] Validando token para operación: {operacion}")

        respuesta_auth = enviar_y_esperar_respuesta('servicio_auth', token)
        print(f"[ORQUESTADOR] Respuesta auth: {respuesta_auth}")

        if respuesta_auth is None or not isinstance(respuesta_auth, str):
            return generar_respuesta_soap("Error: No se recibió una respuesta válida del servicio de autenticación.")

        if "Autenticado" not in respuesta_auth:
            return generar_respuesta_soap(respuesta_auth)

        rol = None
        if "Rol:" in respuesta_auth:
            rol = respuesta_auth.split("Rol:")[1].strip()
        else:
            return generar_respuesta_soap("No se pudo determinar el rol del usuario.")

        if operacion not in PERMISOS:
            return generar_respuesta_soap(f"Operación '{operacion}' no soportada.")

        if rol not in PERMISOS[operacion]:
            return generar_respuesta_soap(f"Acceso denegado. Rol '{rol}' no tiene permiso para '{operacion}'.")

        if operacion == "validar_token":
            return generar_respuesta_soap(respuesta_auth)

        if operacion == "listAll":
            return generar_respuesta_soap(listar_operaciones())

        mensaje = etree.tostring(body[0], encoding='unicode')

        if operacion in ["listar_usuarios", "cambiar_rol"]:
            queue = "servicio_roles"
        else:
            if interfaz == "nosql":
                queue = "servicio_nosql"
            else:
                queue = "servicio_crud"

        print(f"[ORQUESTADOR] Enrutando operación '{operacion}' a cola '{queue}'")

        respuesta_servicio = enviar_y_esperar_respuesta(queue, mensaje)
        return generar_respuesta_soap(respuesta_servicio)

    except Exception as e:
        return generar_respuesta_soap(f"Error en el orquestador: {str(e)}")

def generar_respuesta_soap(mensaje):
    return Response(f"""<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <orquestadorResponse>
          <return>{mensaje}</return>
        </orquestadorResponse>
      </soap:Body>
    </soap:Envelope>""", mimetype="text/xml")

def listar_operaciones():
    operaciones = {
        "validar_token": "Validar token y obtener rol (todos los roles)",
        "crear_base": "Crear bases de datos (admin)",
        "eliminar_base": "Eliminar bases de datos (admin)",
        "crear_tabla": "Crear tablas (admin, editor)",
        "eliminar_tabla": "Eliminar tablas (admin, editor)",
        "insertar_registro": "Insertar registros (admin, editor)",
        "modificar_registro": "Modificar registros (admin, editor)",
        "eliminar_registro": "Eliminar registros (admin, editor)",
        "listar_bases": "Listar bases de datos (todos los roles)",
        "listar_tablas": "Listar tablas de una base (todos los roles)",
        "consultar": "Consultar datos (todos los roles)",
        "listar_usuarios": "Listar usuarios (admin, editor)",
        "cambiar_rol": "Cambiar rol usuario (solo admin)",
        "listAll": "Listar operaciones disponibles"
    }
    return json.dumps(operaciones, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
