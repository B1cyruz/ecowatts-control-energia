from flask import Blueprint, jsonify, request
from app.database import db
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
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
# 1. RUTAS PARA CONFIGURAR LA TARIFA (kWh)
# ==========================================

@main.route('/api/tarifa', methods=['POST'])
def guardar_tarifa():
    """Registra o actualiza el precio del kWh para estrato 3"""
    try:
        data = request.get_json()
        tarifa_kwh = float(data.get('tarifa_kwh'))
        
        doc = {
            "tarifa_kwh": tarifa_kwh,
            "estrato": 3,
            "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Guardamos la tarifa activa (reemplazando la previa o insertando nueva)
        db.tarifas.replace_one({"estrato": 3}, doc, upsert=True)
        
        return jsonify({"message": "Tarifa guardada exitosamente", "data": doc}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@main.route('/api/tarifa', methods=['GET'])
def obtener_tarifa():
    """Obtiene la tarifa vigente"""
    tarifa = db.tarifas.find_one({"estrato": 3}, {"_id": 0})
    if tarifa:
        return jsonify(tarifa), 200
    return jsonify({"message": "No hay tarifa registrada"}), 404

# ==========================================
# 2. RUTAS PARA LECTURAS DEL CONTADOR
# ==========================================

@main.route('/api/lectura', methods=['POST'])
def registrar_lectura():
    """Registra una lectura diaria y calcula el consumo respecto a la fecha anterior"""
    try:
        data = request.get_json()
        lectura_actual = float(data.get('lectura_kwh'))
        fecha_str = data.get('fecha', datetime.now().strftime("%Y-%m-%d"))

        # 1. Obtener la tarifa configurada para estrato 3
        tarifa_doc = db.tarifas.find_one({"estrato": 3})
        tarifa_vigente = tarifa_doc['tarifa_kwh'] if tarifa_doc else 0.0

        # 2. Buscar la lectura con fecha INFERIOR o IGUAL más cercana a la fecha ingresada
        lectura_anterior = db.lecturas.find_one(
            {"fecha": {"$lt": fecha_str}},
            sort=[("fecha", -1)]
        )
        
        consumo_dia = 0.0
        if lectura_anterior and 'lectura_kwh' in lectura_anterior:
            consumo_dia = max(0.0, lectura_actual - lectura_anterior['lectura_kwh'])

        costo_dia = round(consumo_dia * tarifa_vigente, 2)

        doc = {
            "fecha": fecha_str,
            "lectura_kwh": lectura_actual,
            "consumo_dia_kwh": round(consumo_dia, 2),
            "costo_dia_cop": costo_dia,
            "tarifa_aplicada": tarifa_vigente,
            "creado_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Actualizamos si ya existe registro en esa fecha o insertamos uno nuevo
        db.lecturas.replace_one({"fecha": fecha_str}, doc, upsert=True)
        
        doc.pop('_id', None)
        return jsonify({"message": "Lectura registrada o actualizada con éxito", "data": doc}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@main.route('/api/lecturas', methods=['GET'])
def listar_lecturas():
    """Obtiene el historial de todas las lecturas"""
    lecturas = list(db.lecturas.find({}, {"_id": 0}).sort("fecha", -1))
    return jsonify({"total": len(lecturas), "lecturas": lecturas}), 200

# ==========================================
# 3. REPORTES Y COMPARATIVAS MENSUALES
# ==========================================

@main.route('/api/reporte/mensual', methods=['GET'])
def reporte_mensual():
    """Genera un resumen acumulado de todos los meses y la comparativa entre ellos"""
    try:
        # Pipeline de agregación de MongoDB para agrupar lecturas por mes (YYYY-MM)
        pipeline = [
            {
                "$project": {
                    "mes": {"$substr": ["$fecha", 0, 7]},  # Extrae 'YYYY-MM' de 'YYYY-MM-DD'
                    "consumo_dia_kwh": 1,
                    "costo_dia_cop": 1
                }
            },
            {
                "$group": {
                    "_id": "$mes",
                    "total_kwh": {"$sum": "$consumo_dia_kwh"},
                    "total_cop": {"$sum": "$costo_dia_cop"},
                    "dias_registrados": {"$sum": 1}
                }
            },
            {"$sort": {"_id": -1}}  # Meses más recientes primero
        ]

        resumen_meses = list(db.lecturas.aggregate(pipeline))

        # Formateamos y calculamos la variación porcentual entre meses
        reporte = []
        for i, mes in enumerate(resumen_meses):
            mes_actual_kwh = mes['total_kwh']
            variacion_porcentual = None
            mensaje_comparativo = "Sin mes anterior para comparar"

            # Si existe un mes anterior en el historial, calculamos la diferencia %
            if i + 1 < len(resumen_meses):
                mes_anterior_kwh = resumen_meses[i + 1]['total_kwh']
                if mes_anterior_kwh > 0:
                    diferencia = mes_actual_kwh - mes_anterior_kwh
                    variacion_porcentual = round((diferencia / mes_anterior_kwh) * 100, 2)
                    
                    if variacion_porcentual > 0:
                        mensaje_comparativo = f"Aumento del {variacion_porcentual}% respecto al mes anterior"
                    elif variacion_porcentual < 0:
                        mensaje_comparativo = f"Reducción del {abs(variacion_porcentual)}% respecto al mes anterior"
                    else:
                        mensaje_comparativo = "Consumo idéntico al mes anterior"

            reporte.append({
                "mes": mes['_id'],
                "total_consumo_kwh": round(mes_actual_kwh, 2),
                "total_costo_cop": round(mes['total_cop'], 2),
                "dias_registrados": mes['dias_registrados'],
                "variacion_vs_mes_anterior_pct": variacion_porcentual,
                "analisis": mensaje_comparativo
            })

        return jsonify({"reporte_mensual": reporte}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500