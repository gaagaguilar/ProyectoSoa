import pika
import mysql.connector
from lxml import etree

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'sistema_autenticacion',  # Cambia si es necesario
    'port': 3306
}

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='servicio_crud')

def crear_base(nombre):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {nombre}")
        conn.commit()
        cursor.close()
        conn.close()
        return f"Base de datos '{nombre}' creada correctamente."
    except Exception as e:
        return f"Error creando base: {str(e)}"

def eliminar_base(nombre):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS {nombre}")
        conn.commit()
        cursor.close()
        conn.close()
        return f"Base de datos '{nombre}' eliminada correctamente."
    except Exception as e:
        return f"Error eliminando base: {str(e)}"

def crear_tabla(base, tabla, campos):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {base}")

        campos_sql = []
        pk_fields = []
        for c in campos:
            linea = f"{c['nombre']} {c['tipo']}"
            if c.get('no_nulo', False):
                linea += " NOT NULL"
            campos_sql.append(linea)
            if c.get('clave_primaria', False):
                pk_fields.append(c['nombre'])
        pk_sql = f", PRIMARY KEY ({','.join(pk_fields)})" if pk_fields else ""
        sql = f"CREATE TABLE IF NOT EXISTS {tabla} ({', '.join(campos_sql)}{pk_sql})"
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        return f"Tabla '{tabla}' creada correctamente en la base '{base}'."
    except Exception as e:
        return f"Error creando tabla: {str(e)}"

def eliminar_tabla(base, tabla):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {base}")
        cursor.execute(f"DROP TABLE IF EXISTS {tabla}")
        conn.commit()
        cursor.close()
        conn.close()
        return f"Tabla '{tabla}' eliminada correctamente de la base '{base}'."
    except Exception as e:
        return f"Error eliminando tabla: {str(e)}"

def insertar_registros(base, tabla, registros):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {base}")

        if len(registros) == 0:
            return "No hay registros para insertar."

        for reg in registros:
            columnas = ', '.join(reg.keys())
            valores_placeholder = ', '.join(['%s'] * len(reg))
            valores = tuple(reg.values())
            sql = f"INSERT INTO {tabla} ({columnas}) VALUES ({valores_placeholder})"
            cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return f"Registros insertados correctamente en la tabla '{tabla}'."
    except Exception as e:
        return f"Error insertando registros: {str(e)}"

def modificar_registro(base, tabla, criterio, nuevos_valores):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {base}")

        set_clause = ', '.join([f"{k} = %s" for k in nuevos_valores.keys()])
        where_clause = ' AND '.join([f"{k} = %s" for k in criterio.keys()])
        sql = f"UPDATE {tabla} SET {set_clause} WHERE {where_clause}"
        valores = tuple(nuevos_valores.values()) + tuple(criterio.values())

        cursor.execute(sql, valores)
        conn.commit()
        afectadas = cursor.rowcount
        cursor.close()
        conn.close()
        if afectadas == 0:
            return "No se modificó ningún registro."
        return f"Registros modificados correctamente en la tabla '{tabla}'."
    except Exception as e:
        return f"Error modificando registros: {str(e)}"

def eliminar_registro(base, tabla, criterio):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {base}")

        where_clause = ' AND '.join([f"{k} = %s" for k in criterio.keys()])
        sql = f"DELETE FROM {tabla} WHERE {where_clause}"
        valores = tuple(criterio.values())

        cursor.execute(sql, valores)
        conn.commit()
        afectadas = cursor.rowcount
        cursor.close()
        conn.close()
        if afectadas == 0:
            return "No se eliminó ningún registro."
        return f"Registros eliminados correctamente de la tabla '{tabla}'."
    except Exception as e:
        return f"Error eliminando registros: {str(e)}"

def listar_bases():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        bases = cursor.fetchall()
        cursor.close()
        conn.close()
        xml_resp = "<bases>"
        for b in bases:
            xml_resp += f"<base>{b[0]}</base>"
        xml_resp += "</bases>"
        return xml_resp
    except Exception as e:
        return f"Error listando bases: {str(e)}"

def listar_tablas(base):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"USE {base}")
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()
        cursor.close()
        conn.close()
        xml_resp = "<tablas>"
        for t in tablas:
            xml_resp += f"<tabla>{t[0]}</tabla>"
        xml_resp += "</tablas>"
        return xml_resp
    except Exception as e:
        return f"Error listando tablas: {str(e)}"

def callback(ch, method, properties, body):
    mensaje_recibido = body.decode()
    print(f"[SQL] Mensaje recibido:\n{mensaje_recibido}\n")

    try:
        xml_root = etree.fromstring(body)
        operacion = xml_root.tag

        if operacion == "crear_base":
            nombre = xml_root.findtext("nombre")
            resultado = crear_base(nombre)

        elif operacion == "eliminar_base":
            nombre = xml_root.findtext("nombre")
            resultado = eliminar_base(nombre)

        elif operacion == "crear_tabla":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            campos_xml = xml_root.find("campos")
            campos = []
            if campos_xml is not None:
                for campo_xml in campos_xml.findall("campo"):
                    campos.append({
                        'nombre': campo_xml.findtext('nombre'),
                        'tipo': campo_xml.findtext('tipo'),
                        'clave_primaria': campo_xml.findtext('clave_primaria') == 'true',
                        'no_nulo': campo_xml.findtext('no_nulo') == 'true'
                    })
            resultado = crear_tabla(base, tabla, campos)

        elif operacion == "eliminar_tabla":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            resultado = eliminar_tabla(base, tabla)

        elif operacion == "insertar_registro":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            registros_xml = xml_root.find("registros")
            registros = []
            if registros_xml is not None:
                for registro_xml in registros_xml.findall("registro"):
                    doc = {}
                    for campo_xml in registro_xml.findall("campo"):
                        nombre = campo_xml.attrib.get("nombre")
                        valor = campo_xml.text
                        doc[nombre] = valor
                    registros.append(doc)
            resultado = insertar_registros(base, tabla, registros)

        elif operacion == "modificar_registro":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            criterio_xml = xml_root.find("criterio")
            nuevos_valores_xml = xml_root.find("nuevos_valores")
            criterio = {}
            nuevos_valores = {}
            if criterio_xml is not None:
                for campo_xml in criterio_xml.findall("campo"):
                    nombre = campo_xml.attrib.get("nombre")
                    valor = campo_xml.text
                    criterio[nombre] = valor
            if nuevos_valores_xml is not None:
                for campo_xml in nuevos_valores_xml.findall("campo"):
                    nombre = campo_xml.attrib.get("nombre")
                    valor = campo_xml.text
                    nuevos_valores[nombre] = valor
            resultado = modificar_registro(base, tabla, criterio, nuevos_valores)

        elif operacion == "eliminar_registro":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            criterio_xml = xml_root.find("criterio")
            criterio = {}
            if criterio_xml is not None:
                for campo_xml in criterio_xml.findall("campo"):
                    nombre = campo_xml.attrib.get("nombre")
                    valor = campo_xml.text
                    criterio[nombre] = valor
            resultado = eliminar_registro(base, tabla, criterio)

        elif operacion == "listar_bases":
            resultado = listar_bases()

        elif operacion == "listar_tablas":
            base = xml_root.findtext("base")
            resultado = listar_tablas(base)

        else:
            resultado = f"Operación '{operacion}' no soportada por SQL."

        print(f"[SQL] Respuesta a enviar:\n{resultado}\n")

        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=resultado
        )

    except Exception as e:
        error_msg = f"Error en servicio SQL: {str(e)}"
        print(f"[SQL] {error_msg}")
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=error_msg
        )

channel.basic_consume(queue='servicio_crud', on_message_callback=callback, auto_ack=True)

print("[SQL] Esperando mensajes en cola 'servicio_crud'...")
channel.start_consuming()
