import pandas as pd
import datetime
import requests
import os

# Configuración de Telegram (usar variables de entorno para seguridad)
TELEGRAM_BOT_TOKEN = os.environ.get('7641312771:AAH3TDYHrZd2g6RiEAb1m6f7EHSVFuSO2_s')
TELEGRAM_CHAT_ID = os.environ.get('7641312771')

# URL de tu archivo CSV en GitHub (si es un repositorio público, puedes usar la URL raw)
# Si es privado, necesitarás una forma de autenticación o una forma de leerlo localmente si ejecutas en tu máquina
# Para GitHub Actions, lo ideal es que el script acceda al archivo dentro del mismo repositorio
CSV_FILE_PATH = 'https://github.com/riv1matias/AvisoComidas/blob/main/Comidas.xlsx' # Asumiendo que el CSV está en la raíz de tu repositorio

def get_preparations_for_today():
    try:
        df = pd.read_csv(CSV_FILE_PATH)
    except FileNotFoundError:
        return "Error: No se encontró el archivo del cronograma."

    now = datetime.datetime.now()
    current_day_of_week = now.weekday() # 0=Lunes, 6=Domingo
    current_hour = now.hour

    day_map = {
        0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes",
        5: "Sábado", 6: "Domingo"
    }

    # Determinar si es "Noche" o "Mediodía"
    schedule_time_key = ""
    if 9 <= current_hour <= 12: # Horario de Mediodía (9, 10, 11, 12)
        schedule_time_key = "Mediodía"
    elif 19 <= current_hour <= 22: # Horario de Noche (19, 20, 21, 22)
        schedule_time_key = "Noche"
    else:
        return None # No es un horario de alerta

    column_name = f"{day_map[current_day_of_week]} {schedule_time_key}"

    if column_name not in df.columns:
        return f"Error: La columna '{column_name}' no se encontró en el cronograma."

    preparations = []
    for index, row in df.iterrows():
        if pd.notna(row[column_name]) and str(row[column_name]).strip() != "":
            preparations.append(f"- {row['Comida']}: {row[column_name]}")

    if not preparations:
        return f"No hay preparaciones para {column_name} hoy."
    else:
        return f"¡Es hora de preparar para {column_name}!\n\n" + "\n".join(preparations)

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown' # Puedes usar 'HTML' o 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP erróneos
        print("Mensaje enviado exitosamente a Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

if __name__ == "__main__":
    message_to_send = get_preparations_for_today()
    if message_to_send:
        send_telegram_message(message_to_send)
    else:
        print("No es un horario para enviar alertas o no hay preparaciones.")
