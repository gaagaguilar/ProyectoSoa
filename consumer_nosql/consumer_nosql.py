import pika
from pymongo import MongoClient
from lxml import etree
import json

MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='servicio_nosql')

def crear_base(nombre):
    try:
        db = client[nombre]
        db.create_collection("init_collection")
        db.drop_collection("init_collection")
        return f"Base de datos '{nombre}' creada correctamente en MongoDB."
    except Exception as e:
        return f"Error creando base: {str(e)}"

def eliminar_base(nombre):
    try:
        client.drop_database(nombre)
        return f"Base de datos '{nombre}' eliminada correctamente en MongoDB."
    except Exception as e:
        return f"Error eliminando base: {str(e)}"

def crear_tabla(base, tabla):
    try:
        db = client[base]
        db.create_collection(tabla)
        return f"Tabla '{tabla}' creada correctamente en base '{base}'."
    except Exception as e:
        return f"Error creando tabla: {str(e)}"

def eliminar_tabla(base, tabla):
    try:
        db = client[base]
        db.drop_collection(tabla)
        return f"Tabla '{tabla}' eliminada correctamente en base '{base}'."
    except Exception as e:
        return f"Error eliminando tabla: {str(e)}"

def insertar_registros(base, tabla, registros):
    try:
        db = client[base]
        coleccion = db[tabla]
        if len(registros) == 0:
            return "No hay registros para insertar."
        coleccion.insert_many(registros)
        return f"Registros insertados correctamente en la tabla '{tabla}'."
    except Exception as e:
        return f"Error insertando registros: {str(e)}"

def modificar_registro(base, tabla, criterio, nuevos_valores):
    try:
        db = client[base]
        coleccion = db[tabla]
        result = coleccion.update_many(criterio, {'$set': nuevos_valores})
        if result.matched_count == 0:
            return "No se modificó ningún registro."
        return f"Registros modificados correctamente en la tabla '{tabla}'."
    except Exception as e:
        return f"Error modificando registros: {str(e)}"

def eliminar_registro(base, tabla, criterio):
    try:
        db = client[base]
        coleccion = db[tabla]
        result = coleccion.delete_many(criterio)
        if result.deleted_count == 0:
            return "No se eliminó ningún registro."
        return f"Registros eliminados correctamente de la tabla '{tabla}'."
    except Exception as e:
        return f"Error eliminando registros: {str(e)}"

def listar_bases():
    try:
        bases = client.list_database_names()
        xml_resp = "<bases>"
        for base in bases:
            xml_resp += f"<base>{base}</base>"
        xml_resp += "</bases>"
        return xml_resp
    except Exception as e:
        return f"Error listando bases: {str(e)}"

def listar_tablas(base):
    try:
        db = client[base]
        tablas = db.list_collection_names()
        xml_resp = "<tablas>"
        for tabla in tablas:
            xml_resp += f"<tabla>{tabla}</tabla>"
        xml_resp += "</tablas>"
        return xml_resp
    except Exception as e:
        return f"Error listando tablas: {str(e)}"

def parsear_campos(campos_xml):
    resultado = {}
    for campo_xml in campos_xml.findall("campo"):
        nombre = campo_xml.attrib.get("nombre")
        valor = campo_xml.text
        try:
            if valor is not None:
                if '.' in valor:
                    valor = float(valor)
                else:
                    valor = int(valor)
        except (ValueError, TypeError):
            pass
        resultado[nombre] = valor
    return resultado

def construir_pipeline_mongo(xml_root):
    try:
        pipeline = []

        filtros_xml = xml_root.find('filtros')
        relaciones_xml = xml_root.find('relaciones')
        campos_xml = xml_root.find('campos')
        agrupaciones_xml = xml_root.find('agrupaciones')
        ordenamientos_xml = xml_root.find('ordenamientos')
        limite = xml_root.findtext('limite')

        if filtros_xml is not None:
            match = {}
            operadores_validos = ['=', '<>', '!=', '<', '>', '<=', '>=']
            for f in filtros_xml.findall('filtro'):
                operador = f.attrib.get('operador', '=')
                if operador not in operadores_validos:
                    raise ValueError(f"Operador inválido en filtro NoSQL: {operador}")
                campo = f"{f.attrib['tabla']}.{f.attrib['campo']}"
                valor = f.attrib['valor']
                # Solo filtro igualdad para demo
                if operador in ['=', '==']:
                    match[campo] = valor
                else:
                    raise ValueError(f"Operador NoSQL no implementado: {operador}")
            if match:
                pipeline.append({'$match': match})

        if relaciones_xml is not None:
            for r in relaciones_xml.findall('relacion'):
                local_field = f"{r.attrib['tabla1']}.{r.attrib['campo1']}"
                foreign_field = r.attrib['campo2']
                from_collection = r.attrib['tabla2']
                pipeline.append({
                    '$lookup': {
                        'from': from_collection,
                        'localField': local_field,
                        'foreignField': foreign_field,
                        'as': from_collection
                    }
                })

        project = {}
        if campos_xml is not None:
            for c in campos_xml.findall('campo'):
                alias = c.attrib.get('alias', c.attrib['nombre'])
                campo_full = f"{c.attrib['tabla']}.{c.attrib['nombre']}"
                project[alias] = f"${campo_full}"
        if project:
            pipeline.append({'$project': project})

        if agrupaciones_xml is not None:
            group_id = {}
            for a in agrupaciones_xml.findall('campo'):
                group_id[a.attrib['nombre']] = f"${a.attrib['tabla']}.{a.attrib['nombre']}"
            if group_id:
                pipeline.append({'$group': {'_id': group_id}})

        if ordenamientos_xml is not None:
            sort_stage = {}
            for o in ordenamientos_xml.findall('orden'):
                direccion = 1 if o.attrib['direccion'].upper() == 'ASC' else -1
                sort_stage[o.attrib['campo']] = direccion
            if sort_stage:
                pipeline.append({'$sort': sort_stage})

        if limite:
            try:
                lim_val = int(limite)
                if lim_val <= 0:
                    raise ValueError()
                pipeline.append({'$limit': lim_val})
            except:
                raise ValueError("El límite debe ser un entero positivo")

        print(f"[NoSQL] Pipeline generado:\n{json.dumps(pipeline, indent=2)}\n")

        return pipeline
    except Exception as e:
        raise ValueError(f"Error construyendo pipeline MongoDB: {str(e)}")

def consulta_avanzada(base, tabla, pipeline_json):
    try:
        db = client[base]
        coleccion = db[tabla]
        pipeline = json.loads(pipeline_json)
        resultados = coleccion.aggregate(pipeline)
        xml_resp = "<resultados>"
        for doc in resultados:
            xml_resp += "<registro>"
            for k, v in doc.items():
                if k == "_id":
                    continue
                xml_resp += f"<{k}>{v}</{k}>"
            xml_resp += "</registro>"
        xml_resp += "</resultados>"
        return xml_resp
    except Exception as e:
        return f"Error en consulta avanzada NoSQL: {str(e)}"

def callback(ch, method, properties, body):
    mensaje_recibido = body.decode()
    print(f"[NoSQL] Mensaje recibido:\n{mensaje_recibido}\n")

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
            resultado = crear_tabla(base, tabla)

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
                        try:
                            if valor is not None:
                                if '.' in valor:
                                    valor = float(valor)
                                else:
                                    valor = int(valor)
                        except:
                            pass
                        doc[nombre] = valor
                    registros.append(doc)
            resultado = insertar_registros(base, tabla, registros)

        elif operacion == "modificar_registro":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            criterio_xml = xml_root.find("criterio")
            nuevos_valores_xml = xml_root.find("nuevos_valores")
            criterio = parsear_campos(criterio_xml) if criterio_xml is not None else {}
            nuevos_valores = parsear_campos(nuevos_valores_xml) if nuevos_valores_xml is not None else {}
            resultado = modificar_registro(base, tabla, criterio, nuevos_valores)

        elif operacion == "eliminar_registro":
            base = xml_root.findtext("base")
            tabla = xml_root.findtext("tabla")
            criterio_xml = xml_root.find("criterio")
            criterio = parsear_campos(criterio_xml) if criterio_xml is not None else {}
            resultado = eliminar_registro(base, tabla, criterio)

        elif operacion == "listar_bases":
            resultado = listar_bases()

        elif operacion == "listar_tablas":
            base = xml_root.findtext("base")
            resultado = listar_tablas(base)

        elif operacion == "consulta_avanzada":
            base = xml_root.findtext('base')
            tabla = None
            tablas_xml = xml_root.find('tablas')
            if tablas_xml is not None:
                tabla_tag = tablas_xml.find('tabla')
                if tabla_tag is not None:
                    tabla = tabla_tag.attrib.get('nombre')
            if not base or not tabla:
                resultado = "Error: Debe especificar base y tabla para consulta avanzada NoSQL"
            else:
                pipeline = construir_pipeline_mongo(xml_root)
                resultado = consulta_avanzada(base, tabla, json.dumps(pipeline))

        else:
            resultado = f"Operación '{operacion}' no soportada por NoSQL."

        print(f"[NoSQL] Respuesta a enviar:\n{resultado}\n")

        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=resultado
        )

    except Exception as e:
        error_msg = f"Error en servicio NoSQL: {str(e)}"
        print(f"[NoSQL] {error_msg}")
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=error_msg
        )

channel.basic_consume(queue='servicio_nosql', on_message_callback=callback, auto_ack=True)

print("[NoSQL] Esperando mensajes en cola 'servicio_nosql'...")
channel.start_consuming()
