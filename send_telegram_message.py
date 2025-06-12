import pandas as pd
import datetime
import requests
import os
import sys # <-- Nueva importación

# --- Configuración de Telegram (usar variables de entorno para seguridad) ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- Ruta a tu archivo Excel ---
EXCEL_FILE_PATH = 'Comidas.xlsx'

def get_preparations_for_today(target_column):
    """
    Lee el cronograma de comidas de un archivo Excel y
    obtiene las preparaciones para la columna especificada.
    """
    if not target_column: # <-- Añadida validación para columna vacía
        print("Error: El nombre de la columna objetivo está vacío.")
        return "Error: El nombre de la columna para obtener preparaciones no fue especificado."

    try:
        df = pd.read_excel(EXCEL_FILE_PATH, engine='openpyxl')
        print(f"Archivo Excel leído exitosamente para la columna: '{target_column}'")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo del cronograma en la ruta: {EXCEL_FILE_PATH}")
        return "Error: No se encontró el archivo del cronograma (Excel). Asegúrate de que 'comidas.xlsx' esté en la raíz del repositorio."
    except Exception as e:
        print(f"Error inesperado al leer el archivo Excel: {e}")
        return f"Error al leer el archivo Excel: {e}. Por favor, verifica el formato de 'comidas.xlsx'."

    if target_column not in df.columns:
        print(f"Error: La columna '{target_column}' no se encontró en el cronograma.")
        return f"Error: La columna '{target_column}' no se encontró en el cronograma. Por favor, verifica los encabezados de tu Excel."

    if 'Comida' not in df.columns:
        print("Error: La columna 'Comida' no se encontró en el Excel. Asegúrate de que la primera columna se llame 'Comida'.")
        return "Error: La columna 'Comida' no se encontró en el archivo Excel. Revisa el nombre de tu primera columna."

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

    if not preparations:
        return f"No hay preparaciones para {target_column}."
    else:
        return f"Preparaciones para {target_column}:\n\n" + "\n".join(preparations)


def send_telegram_message(message):
    """
    Envía el mensaje generado a Telegram.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados como Secrets en GitHub.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Mensaje enviado exitosamente a Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

# --- Función principal que se llamará desde el workflow ---
def main(target_column, aclaracion=""):
    """
    Función principal que orquesta la lectura del Excel y el envío del mensaje.
    """
    print(f"Iniciando main() con columna='{target_column}' y aclaración='{aclaracion}'")
    message_to_send = get_preparations_for_today(target_column)
    if message_to_send:
        if aclaracion:
           message_to_send = aclaracion + "\n\n" + message_to_send
        send_telegram_message(message_to_send)
    else:
        print("No se generó un mensaje para enviar (la función get_preparations_for_today no devolvió contenido).")

# --- Punto de entrada principal del script al ser ejecutado desde la línea de comandos ---
if __name__ == "__main__":
    # sys.argv[0] es el nombre del script
    # sys.argv[1] será el nombre de la columna (ej. "Lunes Noche")
    # sys.argv[2] será la aclaración (ej. "La comida de la noche y mañana")

    if len(sys.argv) >= 2:
        target_column_arg = sys.argv[1]
        aclaracion_arg = sys.argv[2] if len(sys.argv) >= 3 else ""
        print(f"Script ejecutado con argumentos de línea de comandos: target_column='{target_column_arg}', aclaracion='{aclaracion_arg}'")
        main(target_column_arg, aclaracion_arg)
    else:
        print("Error: El script debe ser llamado con al menos un argumento (nombre de la columna del Excel).")
        print("Ejemplo: python send_telegram_message.py 'Lunes Noche' 'La comida de la noche y mañana'")
