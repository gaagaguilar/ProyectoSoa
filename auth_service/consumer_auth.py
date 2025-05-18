import pika
import mysql.connector
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

CLIENT_ID = "1047544597889-tqmj3t57fka16ms7fcjgcii8mseu0cc3.apps.googleusercontent.com"  # Coloca aquí tu Client ID

def verificar_usuario(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
        correo = idinfo["email"]
        nombre = idinfo.get("name", "SinNombre")
        proveedor = "google"
    except Exception as e:
        return f"❌ Token inválido: {str(e)}"

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="sistema_autenticacion"
        )
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT rol FROM usuarios WHERE correo = %s", (correo,))
        usuario = cursor.fetchone()

        if usuario:
            rol = usuario["rol"]
        else:
            cursor.execute(
                "INSERT INTO usuarios (correo, nombre, rol, proveedor) VALUES (%s, %s, %s, %s)",
                (correo, nombre, "lector", proveedor)
            )
            conn.commit()
            rol = "lector"

        cursor.close()
        conn.close()
        return f"Autenticado. Rol: {rol}"

    except Exception as e:
        return f"❌ Error al consultar la base de datos: {str(e)}"

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()
channel.queue_declare(queue="servicio_auth")

def callback(ch, method, properties, body):
    token = body.decode()
    print(f"[AUTH] Token recibido: {token[:30]}...")

    resultado = verificar_usuario(token)

    ch.basic_publish(
        exchange='',
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        body=resultado
    )
    print(f"[AUTH] Respuesta enviada: {resultado}")

channel.basic_consume(queue="servicio_auth", on_message_callback=callback, auto_ack=True)
print("[AUTH] Esperando tokens desde el orquestador...")
channel.start_consuming()
