import pandas as pd
import datetime
import requests
import os

# --- Configuración de Telegram (usar variables de entorno para seguridad) ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- Ruta a tu archivo Excel ---
# Asegúrate de que el archivo 'comidas.xlsx' esté en la misma carpeta raíz que este script.
EXCEL_FILE_PATH = 'comidas.xlsx'

def get_preparations_for_today():
    """
    Lee el cronograma de comidas de un archivo Excel,
    identifica las preparaciones para el día y la franja horaria actual,
    y formatea el mensaje para Telegram.
    """
    try:
        # Intenta leer el archivo Excel usando openpyxl como motor.
        df = pd.read_excel(EXCEL_FILE_PATH, engine='openpyxl')
        print("Archivo Excel leído exitosamente.")
    except FileNotFoundError:
        # Si el archivo no se encuentra.
        print(f"Error: No se encontró el archivo del cronograma en la ruta: {EXCEL_FILE_PATH}")
        return "Error: No se encontró el archivo del cronograma (Excel). Asegúrate de que 'comidas.xlsx' esté en la raíz del repositorio."
    except Exception as e:
        # Para cualquier otro error al leer el Excel (ej. formato inválido).
        print(f"Error inesperado al leer el archivo Excel: {e}")
        return f"Error al leer el archivo Excel: {e}. Por favor, verifica el formato de 'comidas.xlsx'."

    # --- Obtener el día y la hora actual (en UTC, como lo ve GitHub Actions) ---
    now = datetime.datetime.now() # Hora actual en el servidor de GitHub Actions (UTC)
    current_day_of_week = now.weekday() # 0=Lunes, 1=Martes, ..., 6=Domingo
    current_hour = now.hour # Hora en formato 0-23 (UTC)

    # Mensajes de depuración para los logs de GitHub Actions
    print(f"Día actual (Python weekday - 0=Lunes, 6=Domingo): {current_day_of_week}")
    print(f"Hora actual (UTC): {current_hour}")

    # --- Determinar la franja horaria de alerta (Mediodía o Noche) ---
    # Ajusta estos rangos de 'current_hour' para que coincidan con la hora UTC
    # en la que quieres que se active tu alerta de Argentina.
    # Argentina (GMT-3). Por ejemplo:
    # 9 AM Argentina = 12 PM UTC
    # 12 PM Argentina = 3 PM UTC (15:00 UTC)
    # 7 PM Argentina = 10 PM UTC (22:00 UTC)
    # 10 PM Argentina = 1 AM UTC (del día siguiente)
    schedule_time_key = ""
    if 12 <= current_hour <= 15: # Horarios de Mediodía (9, 10, 11, 12hs Argentina = 12, 13, 14, 15hs UTC)
        schedule_time_key = "Mediodia" # Sin tilde, para coincidir con tu posible columna
    elif 22 <= current_hour <= 23 or 0 <= current_hour <= 1: # Horarios de Noche (19, 20, 21, 22hs Argentina = 22, 23, 0, 1hs UTC)
        schedule_time_key = "Noche"
    else:
        # Si la hora actual no cae en ninguna de las franjas de alerta.
        print("No es un horario de alerta configurado en UTC para envío.")
        return None # No es un horario de alerta, no enviar mensaje.

    # --- Mapeo de Python weekday a los nombres de los días en tus columnas del Excel ---
    python_weekday_to_excel_day_name = {
        0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
        4: "Viernes", 5: "Sábado", 6: "Domingo"
    }
    current_excel_day_name = python_weekday_to_excel_day_name[current_day_of_week]

    # --- Lista de nombres de columnas como aparecen *exactamente* en tu Excel ---
    # ¡Es crucial que estos nombres coincidan perfectamente con los encabezados de tu archivo comidas.xlsx!
    # Incluye tildes si las usas, y respeta mayúsculas/minúsculas.
    column_names_in_order = [
        "Domingo Noche", "Lunes Noche", "Martes Noche", "Miercoles Noche", # 'Miercoles' sin tilde según tu input
        "Jueves Noche", "Viernes Noche", "Sabado Mediodia", "Sabado Noche", "Domingo Mediodia"
    ]

    # --- Encontrar el nombre de la columna objetivo para el día y la hora actuales ---
    target_column = None
    for col_name_in_excel in column_names_in_order:
        # Verifica si el día de la semana actual y la franja horaria coinciden con el nombre de la columna
        if current_excel_day_name in col_name_in_excel and schedule_time_key in col_name_in_excel:
            target_column = col_name_in_excel
            break

    if not target_column:
        # Si no se encuentra una columna que coincida con el día y la hora.
        print(f"No se encontró una columna en el Excel que coincida con el día '{current_excel_day_name}' y el tipo de hora '{schedule_time_key}'.")
        return None # No se pudo determinar la columna, no enviar mensaje.

    # --- Verificar si la columna objetivo existe en el DataFrame leído ---
    if target_column not in df.columns:
        print(f"La columna '{target_column}' esperada no se encontró en las columnas reales del DataFrame: {df.columns.tolist()}")
        return f"Error: La columna '{target_column}' no se encontró en el cronograma. Por favor, verifica los encabezados de tu Excel."

    # --- Verificar si la columna 'Comida' existe (donde están los nombres de los platos/ingredientes) ---
    # Asumo que tu primera columna de datos se llama "Comida". Si se llama "Ingrediente", "Plato", etc., cámbialo aquí.
    if 'Comida' not in df.columns:
        print("Error: La columna 'Comida' no se encontró en el Excel. Asegúrate de que la primera columna se llame 'Comida'.")
        return "Error: La columna 'Comida' no se encontró en el archivo Excel. Revisa el nombre de tu primera columna."

    # --- Recopilar las preparaciones para el día y la hora seleccionados ---
    preparations = []
    # Iterar sobre cada fila del DataFrame
    for index, row in df.iterrows():
        # Obtener el nombre de la "Comida" de la primera columna
        meal_name = row['Comida']
        # Obtener el detalle de la preparación para la columna del día/hora actual
        preparation_detail = row[target_column]

        # Si el detalle de preparación no es nulo y no es solo espacios en blanco, agrégalo a la lista
        if pd.notna(preparation_detail) and str(preparation_detail).strip() != "":
            preparations.append(f"- {meal_name}: {preparation_detail}")

    # --- Construir el mensaje final para Telegram ---
    if not preparations:
        # Si no hay preparaciones para ese día/hora
        return f"No hay preparaciones para {target_column} hoy."
    else:
        # Si hay preparaciones, listarlas.
        return f"¡Es hora de preparar para {target_column}!\n\n" + "\n".join(preparations)

def send_telegram_message(message):
    """
    Envía el mensaje generado a Telegram usando el bot y el chat ID configurados.
    """
    # Verificar que los tokens estén configurados
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados como Secrets en GitHub.")
        return

    # Construir la URL de la API de Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown' # Para que el formato de lista (- item) se vea bien.
    }
    try:
        # Enviar la solicitud POST a la API de Telegram
        response = requests.post(url, data=payload)
        response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        print("Mensaje enviado exitosamente a Telegram.")
    except requests.exceptions.RequestException as e:
        # Capturar cualquier error de red o HTTP.
        print(f"Error al enviar mensaje a Telegram: {e}")

# --- Punto de entrada principal del script ---
if __name__ == "__main__":
    message_to_send = get_preparations_for_today()
    if message_to_send:
        # Si se generó un mensaje, intentar enviarlo a Telegram.
        send_telegram_message(message_to_send)
    else:
        # Si get_preparations_for_today devolvió None (no es hora de alerta, etc.)
        print("No se generó un mensaje para enviar (posiblemente no es un horario de alerta o no hay preparaciones para hoy).")
