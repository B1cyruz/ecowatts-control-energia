from flask import Blueprint, render_template
from flask import Blueprint, jsonify, request
from app.database import db
from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template, request, jsonify, session, redirect, url_for
from bson.objectid import ObjectId

main = Blueprint('main', __name__)

@main.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('main.vista_login'))
    return render_template('dashboard.html')

    status_db = "Desconectado"
    if db is not None:
        try:
            db.command('ping')
            status_db = "Conectado"
        except Exception:
            status_db = "Error"

    return jsonify({
        "app": "EcoWatts API",
        "status": "online",
        "database": status_db
    })

# ==========================================
# VISTAS DE AUTENTICACION
# ==========================================

@main.route('/registro')
def vista_registro():
    return render_template('registro.html')

@main.route('/login')
def vista_login():
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.vista_login'))

# ==========================================
# ENDPOINTS API DE AUTENTICACIÓN
# ==========================================

@main.route('/api/auth/registro', methods=['POST'])
def api_registro():
    try:
        data = request.get_json() or {}
        nombre = data.get('nombre', '').strip()
        username = data.get('username', '').strip().lower()
        email = data.get('email', '').strip().lower()
        telefono = data.get('telefono', '').strip()
        direccion = data.get('direccion', '').strip()
        password = data.get('password', '')

        # 1. Validaciones básicas
        if not all([nombre, username, email, telefono, direccion, password]):
            return jsonify({"error": "Todos los campos son obligatorios."}), 400

        # 2. Validación de contraseña (mínimo 8 caracteres y al menos 1 carácter especial)
        pattern_especial = r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]'
        if len(password) < 8 or not re.search(pattern_especial, password):
            return jsonify({
                "error": "La contraseña debe tener al menos 8 caracteres y contener al menos un carácter especial (!@#$%...)."
            }), 400

        # 3. Verificar si el usuario o email ya existen en MongoDB
        if db.usuarios.find_one({"$or": [{"email": email}, {"username": username}]}):
            return jsonify({"error": "El correo o el nombre de usuario ya se encuentran registrados."}), 400

        # 4. Crear usuario con hash de contraseña
        nuevo_usuario = {
            "nombre": nombre,
            "username": username,
            "email": email,
            "telefono": telefono,
            "direccion": direccion,
            "password_hash": generate_password_hash(password),
            "creado_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        db.usuarios.insert_one(nuevo_usuario)
        return jsonify({"message": "Usuario registrado exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Vista de recuperación
@main.route('/recuperar')
def vista_recuperar():
    return render_template('recuperar.html')

# ==========================================
# ENDPOINT API DE RECUPERACIÓN DE CONTRASEÑA Y LOGIN
# ==========================================

@main.route('/api/auth/recuperar', methods=['POST'])
def api_recuperar_password():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({"error": "Ingresa tu correo electrónico."}), 400

        usuario = db.usuarios.find_one({"email": email})

        # Por seguridad no revelamos si el correo existe o no, pero si existe mostramos su usuario
        if usuario:
            # Aquí se integrará el envío de correo SMTP con Flask-Mail
            return jsonify({
                "message": f"Si el correo existe, enviamos un enlace de recuperación. Tu nombre de usuario registrado es: '{usuario['username']}'."
            }), 200
        else:
            return jsonify({
                "message": "Si el correo existe en nuestro sistema, hemos enviado las instrucciones."
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json() or {}
        login_id = data.get('login_id', '').strip().lower()
        password = data.get('password', '')

        if not login_id or not password:
            return jsonify({"error": "Por favor ingresa usuario/correo y contraseña."}), 400

        # Buscar por email o username
        usuario = db.usuarios.find_one({"$or": [{"email": login_id}, {"username": login_id}]})

        if not usuario or not check_password_hash(usuario['password_hash'], password):
            return jsonify({"error": "Credenciales incorrectas. Verifica tus datos."}), 400

        # Guardar datos esenciales en la sesión
        session['user_id'] = str(usuario['_id'])
        session['user_nombre'] = usuario['nombre']

        return jsonify({"message": "Inicio de sesión exitoso."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# RUTAS DE GESTIÓN DE TARIFAS DINÁMICAS
# ==========================================

@main.route('/api/tarifas', methods=['POST'])
def guardar_tarifa():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    try:
        data = request.get_json() or {}
        estrato = int(data.get('estrato', 3))
        operador = data.get('operador', 'Afinia').strip()
        tarifa_kwh = float(data.get('tarifa_kwh', 0))
        periodo = data.get('periodo', datetime.now().strftime("%Y-%m")) # Formato 'YYYY-MM'

        if tarifa_kwh <= 0:
            return jsonify({"error": "Ingresa una tarifa válida mayor a 0 COP."}), 400

        doc_tarifa = {
            "estrato": estrato,
            "operador": operador,
            "tarifa_kwh": tarifa_kwh,
            "periodo": periodo,
            "actualizado_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Guardar en la colección de tarifas históricas
        db.tarifas_historicas.replace_one(
            {"estrato": estrato, "operador": operador, "periodo": periodo},
            doc_tarifa,
            upsert=True
        )

        # También actualizamos la tarifa vigente por defecto
        db.tarifas.replace_one(
            {"estrato": estrato},
            {"estrato": estrato, "operador": operador, "tarifa_kwh": tarifa_kwh},
            upsert=True
        )

        return jsonify({"message": "Tarifa configurada exitosamente.", "tarifa": doc_tarifa}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/tarifas', methods=['GET'])
def obtener_tarifa_actual():
    try:
        estrato = int(request.args.get('estrato', 3))
        operador = request.args.get('operador', 'Afinia')
        periodo_actual = datetime.now().strftime("%Y-%m")

        # Buscar en tarifas históricas del mes actual
        tarifa_doc = db.tarifas_historicas.find_one({
            "estrato": estrato,
            "operador": operador,
            "periodo": periodo_actual
        })

        # Si no hay histórico para este mes, buscar la última configurada
        if not tarifa_doc:
            tarifa_doc = db.tarifas.find_one({"estrato": estrato})

        tarifa_kwh = tarifa_doc['tarifa_kwh'] if tarifa_doc else 850.0 # Tarifa base por defecto (COP)

        return jsonify({
            "estrato": estrato,
            "operador": operador,
            "periodo": periodo_actual,
            "tarifa_kwh": tarifa_kwh
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# RUTAS API DE LECTURAS (FILTRADAS POR USUARIO)
# ==========================================

@main.route('/api/lecturas', methods=['POST'])
def registrar_lectura():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado. Inicia sesión."}), 401

    try:
        data = request.get_json() or {}
        lectura_actual = float(data.get('lectura_kwh', 0))
        fecha_str = data.get('fecha', datetime.now().strftime("%Y-%m-%d"))
        usuario_id = session['user_id']

        # 1. Obtener la tarifa configurada
        tarifa_doc = db.tarifas.find_one({"estrato": 3})
        tarifa_vigente = tarifa_doc['tarifa_kwh'] if tarifa_doc else 850.0  # Valor base COP/kWh

        # 2. Buscar la lectura anterior del MISMO usuario
        lectura_anterior = db.lecturas.find_one(
            {
                "usuario_id": usuario_id,
                "fecha": {"$lt": fecha_str}
            },
            sort=[("fecha", -1)]
        )

        consumo_dia = 0.0
        if lectura_anterior and 'lectura_kwh' in lectura_anterior:
            consumo_dia = max(0.0, lectura_actual - lectura_anterior['lectura_kwh'])

        costo_dia = round(consumo_dia * tarifa_vigente, 2)

        doc = {
            "usuario_id": usuario_id,  # <-- Vinculación clave al usuario
            "fecha": fecha_str,
            "lectura_kwh": lectura_actual,
            "consumo_dia_kwh": round(consumo_dia, 2),
            "costo_dia_cop": costo_dia,
            "tarifa_aplicada": tarifa_vigente,
            "creado_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Actualizar o insertar según la fecha Y el usuario
        db.lecturas.replace_one(
            {"usuario_id": usuario_id, "fecha": fecha_str}, 
            doc, 
            upsert=True
        )

        doc.pop('_id', None)
        return jsonify({"message": "Lectura registrada con éxito", "data": doc}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/lecturas', methods=['GET'])
def obtener_lecturas():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    try:
        usuario_id = session['user_id']
        # Consultar SOLO las lecturas del usuario activo
        lecturas = list(db.lecturas.find({"usuario_id": usuario_id}, {"_id": 0}).sort("fecha", -1))
        return jsonify({"lecturas": lecturas}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/auth/perfil', methods=['GET'])
def obtener_perfil():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    try:
        usuario = db.usuarios.find_one({"_id": ObjectId(session['user_id'])})
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify({
            "nombre": usuario.get('nombre', ''),
            "username": usuario.get('username', ''),
            "email": usuario.get('email', ''),
            "telefono": usuario.get('telefono', ''),
            "direccion": usuario.get('direccion', '')
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ==========================================
# RUTAS DE GESTIÓN DE PERFIL DE USUARIO
# ==========================================

@main.route('/api/auth/perfil', methods=['PUT'])
def actualizar_perfil():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    try:
        data = request.get_json() or {}
        nombre = data.get('nombre', '').strip()
        telefono = data.get('telefono', '').strip()
        direccion = data.get('direccion', '').strip()
        password = data.get('password', '')

        if not all([nombre, telefono, direccion]):
            return jsonify({"error": "Nombre, teléfono y dirección son obligatorios."}), 400

        update_fields = {
            "nombre": nombre,
            "telefono": telefono,
            "direccion": direccion
        }

        # Si el usuario ingresó una nueva contraseña, la validamos e igualamos en hash
        if password:
            pattern_especial = r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]'
            if len(password) < 8 or not re.search(pattern_especial, password):
                return jsonify({
                    "error": "La nueva contraseña debe tener al menos 8 caracteres y contener un símbolo especial."
                }), 400
            
            update_fields["password_hash"] = generate_password_hash(password)

        # Actualizar en MongoDB
        db.usuarios.update_one(
            {"_id": ObjectId(session['user_id'])},
            {"$set": update_fields}
        )

        # Actualizar el nombre en la sesión actual
        session['user_nombre'] = nombre

        return jsonify({"message": "Perfil actualizado correctamente."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/reporte/mensual', methods=['GET'])
def reporte_mensual():
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    try:
        usuario_id = session['user_id']
        
        # Agregación en MongoDB filtrando por usuario_id
        pipeline = [
            {"$match": {"usuario_id": usuario_id}},
            {
                "$project": {
                    "mes": {"$substr": ["$fecha", 0, 7]},
                    "consumo_dia_kwh": "$consumo_dia_kwh",
                    "costo_dia_cop": "$costo_dia_cop"
                }
            },
            {
                "$group": {
                    "_id": "$mes",
                    "total_consumo_kwh": {"$sum": "$consumo_dia_kwh"},
                    "total_costo_cop": {"$sum": "$costo_dia_cop"},
                    "dias_registrados": {"$sum": 1}
                }
            },
            {"$sort": {"_id": -1}}
        ]

        reportes_db = list(db.lecturas.aggregate(pipeline))
        reporte = []

        for i, doc in enumerate(reportes_db):
            total_kwh = round(doc['total_consumo_kwh'], 2)
            total_cop = round(doc['total_costo_cop'], 2)
            
            variacion_pct = None
            mensaje_comparativo = "Sin datos de mes anterior para comparar"

            if i + 1 < len(reportes_db):
                mes_anterior_kwh = reportes_db[i + 1]['total_consumo_kwh']
                if mes_anterior_kwh > 0:
                    variacion_pct = round(((total_kwh - mes_anterior_kwh) / mes_anterior_kwh) * 100, 2)
                    if variacion_pct > 0:
                        mensaje_comparativo = f"Aumento del {variacion_pct}% respecto al mes anterior"
                    elif variacion_pct < 0:
                        mensaje_comparativo = f"Reducción del {abs(variacion_pct)}% respecto al mes anterior"
                    else:
                        mensaje_comparativo = "Consumo idéntico al mes anterior"

            reporte.append({
                "mes": doc['_id'],
                "total_consumo_kwh": total_kwh,
                "total_costo_cop": total_cop,
                "dias_registrados": doc['dias_registrados'],
                "variacion_vs_mes_anterior_pct": variacion_pct,
                "analisis": mensaje_comparativo
            })

        return jsonify({"reporte_mensual": reporte}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500