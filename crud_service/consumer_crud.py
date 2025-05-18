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

def consulta_avanzada(sql_query):
    try:
        if not sql_query.strip().lower().startswith("select"):
            return "Solo se permiten consultas SELECT para operaciones avanzadas."

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        xml_resp = "<resultados>"
        for row in rows:
            xml_resp += "<registro>"
            for key, val in row.items():
                xml_resp += f"<{key}>{val}</{key}>"
            xml_resp += "</registro>"
        xml_resp += "</resultados>"
        return xml_resp
    except Exception as e:
        return f"Error en consulta avanzada: {str(e)}"

def construir_consulta_sql(xml_root):
    try:
        base = xml_root.findtext('base')
        if not base:
            raise ValueError("No se especificó la base de datos")

        tablas_xml = xml_root.find('tablas')
        campos_xml = xml_root.find('campos')
        relaciones_xml = xml_root.find('relaciones')
        filtros_xml = xml_root.find('filtros')
        agrupaciones_xml = xml_root.find('agrupaciones')
        ordenamientos_xml = xml_root.find('ordenamientos')
        limite = xml_root.findtext('limite')

        if tablas_xml is None or len(tablas_xml.findall('tabla')) == 0:
            raise ValueError("Debe especificar al menos una tabla")

        tablas = []
        for t in tablas_xml.findall('tabla'):
            nombre = t.attrib.get('nombre')
            alias = t.attrib.get('alias')
            if not nombre:
                raise ValueError("Cada tabla debe tener atributo 'nombre'")
            tablas.append((nombre, alias))

        campos = []
        if campos_xml is not None:
            for c in campos_xml.findall('campo'):
                tabla_campo = c.attrib.get('tabla')
                nombre_campo = c.attrib.get('nombre')
                if not tabla_campo or not nombre_campo:
                    raise ValueError("Cada campo debe tener 'tabla' y 'nombre'")
                funcion = c.attrib.get('funcion')
                alias = c.attrib.get('alias')
                if funcion:
                    funcion = funcion.upper()
                    if funcion not in ['SUM', 'COUNT', 'AVG', 'MIN', 'MAX']:
                        raise ValueError(f"Función agregada no permitida: {funcion}")
                campos.append({'tabla': tabla_campo, 'nombre': nombre_campo, 'funcion': funcion, 'alias': alias})

        relaciones = []
        if relaciones_xml is not None:
            for r in relaciones_xml.findall('relacion'):
                tabla1 = r.attrib.get('tabla1')
                campo1 = r.attrib.get('campo1')
                tabla2 = r.attrib.get('tabla2')
                campo2 = r.attrib.get('campo2')
                tipo = r.attrib.get('tipo', 'INNER').upper()
                if not all([tabla1, campo1, tabla2, campo2]):
                    raise ValueError("Relación incompleta (falta tabla o campo)")
                if tipo not in ['INNER', 'LEFT', 'RIGHT']:
                    raise ValueError(f"Tipo de JOIN inválido: {tipo}")
                relaciones.append({'tabla1': tabla1, 'campo1': campo1, 'tabla2': tabla2, 'campo2': campo2, 'tipo': tipo})

        filtros = []
        if filtros_xml is not None:
            operadores_validos = ['=', '<>', '!=', '<', '>', '<=', '>=']
            for f in filtros_xml.findall('filtro'):
                tabla_f = f.attrib.get('tabla')
                campo_f = f.attrib.get('campo')
                operador = f.attrib.get('operador')
                valor = f.attrib.get('valor')
                if operador not in operadores_validos:
                    raise ValueError(f"Operador inválido en filtro: {operador}")
                filtros.append({'tabla': tabla_f, 'campo': campo_f, 'operador': operador, 'valor': valor})

        agrupaciones = []
        if agrupaciones_xml is not None:
            for a in agrupaciones_xml.findall('campo'):
                tabla_a = a.attrib.get('tabla')
                nombre_a = a.attrib.get('nombre')
                if tabla_a and nombre_a:
                    agrupaciones.append(f"{tabla_a}.{nombre_a}")

        ordenamientos = []
        if ordenamientos_xml is not None:
            for o in ordenamientos_xml.findall('orden'):
                campo_o = o.attrib.get('campo')
                direccion = o.attrib.get('direccion', 'ASC').upper()
                if direccion not in ['ASC', 'DESC']:
                    raise ValueError(f"Dirección de orden inválida: {direccion}")
                ordenamientos.append((campo_o, direccion))

        limit_clause = ""
        if limite:
            try:
                lim_val = int(limite)
                if lim_val <= 0:
                    raise ValueError()
                limit_clause = f"LIMIT {lim_val}"
            except:
                raise ValueError("El límite debe ser un entero positivo")

        # Construir SELECT
        select_parts = []
        for c in campos:
            part = ""
            if c['funcion']:
                part += f"{c['funcion']}({c['tabla']}.{c['nombre']})"
            else:
                part += f"{c['tabla']}.{c['nombre']}"
            if c['alias']:
                part += f" AS {c['alias']}"
            select_parts.append(part)
        select_clause = ", ".join(select_parts) if select_parts else "*"

        # Construir FROM con JOINs
        principal = tablas[0]
        from_clause = f"FROM {principal[0]} {principal[1] if principal[1] else ''}".strip()
        for rel in relaciones:
            from_clause += f" {rel['tipo']} JOIN {rel['tabla2']} ON {rel['tabla1']}.{rel['campo1']} = {rel['tabla2']}.{rel['campo2']}"

        # Construir WHERE
        where_clause = ""
        if filtros:
            condiciones = []
            for f in filtros:
                val = f["valor"].replace("'", "''")
                condiciones.append(f"{f['tabla']}.{f['campo']} {f['operador']} '{val}'")
            where_clause = "WHERE " + " AND ".join(condiciones)

        # Construir GROUP BY
        group_by_clause = ""
        if agrupaciones:
            group_by_clause = "GROUP BY " + ", ".join(agrupaciones)

        # Construir ORDER BY
        order_by_clause = ""
        if ordenamientos:
            order_by_clause = "ORDER BY " + ", ".join([f"{o[0]} {o[1]}" for o in ordenamientos])

        consulta = f"SELECT {select_clause} {from_clause} {where_clause} {group_by_clause} {order_by_clause} {limit_clause}"
        print(f"[SQL] Consulta generada:\n{consulta}\n")

        return consulta.strip()

    except Exception as e:
        raise ValueError(f"Error construyendo consulta SQL: {str(e)}")

def callback(ch, method, properties, body):
    mensaje_recibido = body.decode()
    print(f"[SQL] Mensaje recibido:\n{mensaje_recibido}\n")

    try:
        xml_tree = etree.fromstring(body)
        body_elem = xml_tree.xpath('//soap:Body', namespaces={'soap': 'http://schemas.xmlsoap.org/soap/envelope/'})
        if body_elem and len(body_elem[0]) > 0:
            operacion_elem = body_elem[0][0]
            operacion = operacion_elem.tag
            if '}' in operacion:
                operacion = operacion.split('}', 1)[1]
            operacion = operacion.lower()
            xml_root = operacion_elem
        else:
            operacion = xml_tree.tag.lower()
            xml_root = xml_tree

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

        elif operacion == "consulta_avanzada":
            try:
                consulta_sql = construir_consulta_sql(xml_root)
                resultado = consulta_avanzada(consulta_sql)
            except Exception as e:
                resultado = f"Error en consulta avanzada: {str(e)}"

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
