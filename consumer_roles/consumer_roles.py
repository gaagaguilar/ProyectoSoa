import pika
import mysql.connector
from lxml import etree

# Configuración base de datos MySQL para usuarios y roles
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'sistema_autenticacion',
    'port': 3306
}

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='servicio_roles')

def listar_usuarios():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT correo, nombre, rol FROM usuarios")
        usuarios = cursor.fetchall()
        print(f"[Roles] Usuarios recuperados: {usuarios}")  # Log para depuración
        cursor.close()
        conn.close()

        xml_resp = "<usuarios>"
        for u in usuarios:
            xml_resp += f"""
            <usuario>
                <correo>{u['correo']}</correo>
                <nombre>{u['nombre']}</nombre>
                <rol>{u['rol']}</rol>
            </usuario>"""
        xml_resp += "</usuarios>"
        return xml_resp
    except Exception as e:
        print(f"[Roles] Error listando usuarios: {e}")
        return f"Error al listar usuarios: {str(e)}"

def cambiar_rol(correo, nuevo_rol):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET rol = %s WHERE correo = %s", (nuevo_rol, correo))
        conn.commit()
        afectadas = cursor.rowcount
        cursor.close()
        conn.close()
        if afectadas == 0:
            return f"No se encontró usuario con correo {correo}"
        return f"Rol actualizado a '{nuevo_rol}' para usuario {correo}."
    except Exception as e:
        print(f"[Roles] Error cambiando rol: {e}")
        return f"Error al cambiar rol: {str(e)}"

def callback(ch, method, properties, body):
    try:
        print(f"[Roles] Mensaje recibido: {body.decode()}")  # Log para ver mensaje recibido
        xml_root = etree.fromstring(body)
        operacion = xml_root.tag

        if operacion == "listar_usuarios":
            resultado = listar_usuarios()

        elif operacion == "cambiar_rol":
            correo = xml_root.findtext("correo")
            nuevo_rol = xml_root.findtext("rol")
            resultado = cambiar_rol(correo, nuevo_rol)

        else:
            resultado = f"Operación '{operacion}' no soportada por servicio roles."

        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=resultado
        )
        print(f"[Roles] Respuesta enviada: {resultado}")

    except Exception as e:
        print(f"[Roles] Error procesando mensaje: {str(e)}")
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=f"Error en servicio roles: {str(e)}"
        )

channel.basic_consume(queue='servicio_roles', on_message_callback=callback, auto_ack=True)

print("[Roles] Servicio roles escuchando en cola 'servicio_roles'...")
channel.start_consuming()
