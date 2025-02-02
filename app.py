from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import PyPDF2
import pyttsx3
import threading
import re
from gtts import gTTS
import os
import pdfplumber

app = Flask(__name__)

# Habilitar CORS globalmente
CORS(app, resources={r"/*": {"origins": "*"}})

# Carpeta donde se guardarán los PDFs subidos
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Variable global para almacenar el último archivo subido
latest_file = None

@app.route('/upload', methods=['POST'])
def upload_pdf():
    global latest_file  # Usamos la variable global

    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "El archivo no tiene nombre"}), 400

    # Guarda el archivo en la carpeta de uploads
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    
    latest_file = file.filename  # Guardamos el último archivo subido

    return jsonify({
        "message": "Archivo subido exitosamente",
        "file_name": file.filename,
        "file_path": file_path
    })
@app.route('/test', methods=['GET'])
def test_pdf():
    # Especifica el nombre del archivo PDF que deseas probar
    file_name = "las4disciplinas.pdf"

    try:
        # Obtén el número de página solicitado como parámetro de consulta (query param)
        page_num = request.args.get('page', default=1, type=int)

        # Abre el archivo PDF desde la misma carpeta
        with open(file_name, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            # Verifica si el número de página es válido
            total_pages = len(reader.pages)
            if page_num < 1 or page_num > total_pages:
                return jsonify({
                    "error": "Número de página fuera de rango",
                    "total_pages": total_pages
                }), 400

            # Extrae el texto de la página solicitada
            page = reader.pages[page_num - 1]  # Las páginas empiezan en 0
            text = page.extract_text()

            return jsonify({
                "page": page_num,
                "total_pages": total_pages,
                "text": text
            })
    except FileNotFoundError:
        return jsonify({"error": f"El archivo '{file_name}' no se encontró"}), 404
    except Exception as e:
        return jsonify({"error": f"Error procesando el archivo: {str(e)}"}), 500

@app.route('/read', methods=['GET'])
def read_pdf():
    global latest_file  # Usamos la variable global

    if not latest_file:
        return jsonify({"error": "No hay archivos subidos aún"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], latest_file)

    try:
        text_pages = []

        # Usamos pdfplumber para leer el texto con estructura correcta
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    # Asegurar que haya un salto de línea después de cada párrafo
                    page_text = re.sub(r'(?<=[a-zA-Z0-9])(\n)(?=[a-zA-Z0-9])', ' ', page_text)  # Evita cortes en palabras
                    page_text = re.sub(r'\n{2,}', '\n\n', page_text)  # Asegura saltos de línea correctos
                    page_text = page_text.strip()

                    # Agregar separador visible entre páginas
                    text_pages.append(f"\n\n--- Página {i+1} ---\n\n{page_text}\n")

        # Unir el texto respetando los saltos de línea
        text = "\n\n".join(text_pages)

        # Limpieza final
        text = re.sub(r"\s{2,}", " ", text)  # Evita espacios dobles

        # Dividir en bloques de 500 palabras
        words = text.split()
        total_blocks = len(words) // 500 + (1 if len(words) % 500 != 0 else 0)
        blocks = [" ".join(words[i * 500:(i + 1) * 500]) for i in range(total_blocks)]

        return jsonify({
            "file_name": latest_file,
            "total_pages": len(text_pages),
            "total_blocks": total_blocks,
            "text_blocks": blocks
        })

    except FileNotFoundError:
        return jsonify({"error": f"El archivo '{latest_file}' no se encontró"}), 404
    except Exception as e:
        return jsonify({"error": f"Error procesando el archivo: {str(e)}"}), 500
@app.route('/generate_mp3', methods=['GET'])
def generate_mp3():
    global latest_file  # Usamos la variable global

    if not latest_file:
        return jsonify({"error": "No hay archivos subidos aún"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], latest_file)
    output_file = f"{latest_file.split('.')[0]}.mp3"  # Usar el nombre del archivo subido

    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = " ".join([page.extract_text() for page in reader.pages])

            # Limpiar texto
            text = re.sub(r"\n+", " ", text)
            text = re.sub(r"\s+", " ", text)

            # Generar MP3 con gTTS
            tts = gTTS(text, lang='es')
            tts.save(output_file)

            return send_file(output_file, as_attachment=True)

    except FileNotFoundError:
        return jsonify({"error": f"El archivo '{latest_file}' no se encontró"}), 404
    except Exception as e:
        return jsonify({"error": f"Error al generar MP3: {str(e)}"}), 500

# Función para síntesis de voz
def leer_voz(texto):
    engine = pyttsx3.init()
    velocidad_voz = 130
    engine.setProperty("rate", velocidad_voz)
    engine.say(texto)
    engine.runAndWait()


if __name__ == '__main__':
    app.run(debug=True)
