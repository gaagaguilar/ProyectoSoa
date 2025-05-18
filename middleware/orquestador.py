from flask import Flask, request, Response, send_file
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
    "eliminar_base": ["admin"],
    "crear_tabla": ["admin", "editor"],
    "eliminar_tabla": ["admin", "editor"],
    "insertar_registro": ["admin", "editor"],
    "modificar_registro": ["admin", "editor"],
    "eliminar_registro": ["admin", "editor"],
    "listar_bases": ["admin", "editor", "lector"],
    "listar_tablas": ["admin", "editor", "lector"],
    "consultar": ["admin", "editor", "lector"],
    "listar_usuarios": ["admin", "editor"],
    "cambiar_rol": ["admin"],
    "consulta_avanzada": ["admin", "editor", "lector"],
    "listall": ["admin", "editor", "lector"]
}

@app.route('/wsdl', methods=['GET'])
def wsdl():
    # Cambia esta ruta al lugar donde tengas guardado el archivo wsdl
    return send_file(r'C:\Users\alfre\OneDrive\Escritorio\9no Semestre\Servicios Web\ProyectoSoa\wsdl\KioskCloudService.wsdl', mimetype='text/xml')

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
        xml_str = xml.decode('utf-8')
        print(f"[ORQUESTADOR] XML recibido:\n{xml_str}\n")
        tree = etree.fromstring(xml)
        body = tree.xpath('//soap:Body', namespaces={'soap': 'http://schemas.xmlsoap.org/soap/envelope/'})
        if not body:
            return generar_respuesta_soap("Error: No se encontró el Body en el mensaje SOAP")
        body_elem = body[0]

        if body_elem is None or len(body_elem) == 0:
            return generar_respuesta_soap("Error: No se encontró operación dentro del Body")

        print("[ORQUESTADOR] Contenido de body_elem:\n", etree.tostring(body_elem, pretty_print=True).decode())

        operacion_elem = body_elem[0]
        operacion = operacion_elem.tag
        if '}' in operacion:
            operacion = operacion.split('}', 1)[1]
        operacion = operacion.lower()

        print(f"[ORQUESTADOR] Operacion detectada: '{operacion}'")

        token = operacion_elem.findtext('token')
        interfaz = operacion_elem.findtext('interfaz') or "sql"
        interfaz = interfaz.lower()

        print(f"[ORQUESTADOR] Interfaz seleccionada: {interfaz}")
        print(f"[ORQUESTADOR] Validando token para operación: {operacion}")

        respuesta_auth = enviar_y_esperar_respuesta('servicio_auth', token)
        print(f"[ORQUESTADOR] Respuesta auth: {respuesta_auth}")

        if respuesta_auth is None or not isinstance(respuesta_auth, str):
            return generar_respuesta_soap("Error: No se recibió una respuesta válida del servicio de autenticación.")

        if "autenticado" not in respuesta_auth.lower():
            return generar_respuesta_soap(respuesta_auth)

        rol = None
        if "rol:" in respuesta_auth.lower():
            rol = respuesta_auth.lower().split("rol:")[1].strip()
        else:
            return generar_respuesta_soap("No se pudo determinar el rol del usuario.")

        if operacion not in PERMISOS:
            return generar_respuesta_soap(f"Operación '{operacion}' no soportada.")

        if rol not in PERMISOS[operacion]:
            return generar_respuesta_soap(f"Acceso denegado. Rol '{rol}' no tiene permiso para '{operacion}'.")

        if operacion == "validar_token":
            return generar_respuesta_soap(respuesta_auth)

        if operacion == "listall":
            return generar_respuesta_soap(listar_operaciones())

        mensaje = etree.tostring(operacion_elem, encoding='unicode')

        if operacion in ["listar_usuarios", "cambiar_rol"]:
            queue = "servicio_roles"
        else:
            queue = "servicio_nosql" if interfaz == "nosql" else "servicio_crud"

        print(f"[ORQUESTADOR] Enrutando operación '{operacion}' a cola '{queue}'")

        respuesta_servicio = enviar_y_esperar_respuesta(queue, mensaje)
        return generar_respuesta_soap(respuesta_servicio)

    except Exception as e:
        print(f"[ORQUESTADOR] ERROR: {str(e)}")
        return generar_respuesta_soap(f"Error en el orquestador: {str(e)}")

def generar_respuesta_soap(mensaje):
    return Response(f"""<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <orquestadorResponse>
          <resultado>{mensaje}</resultado>
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
        "consulta_avanzada": "Ejecutar consultas avanzadas SQL y NoSQL",
        "listall": "Listar operaciones disponibles"
    }
    return json.dumps(operaciones, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
