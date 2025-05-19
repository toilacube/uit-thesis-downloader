import os
from flask import Flask, request, jsonify, send_file
import requests
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import logging
from flask_cors import CORS
import img2pdf
from urllib.parse import quote

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/create-pdf', methods=['POST'])
def create_pdf():
    pdf_path = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400

        url_template = data.get('url_template')
        output_filename = data.get('output_filename')
        logger.info(f"Received request with url_template={url_template} and output_filename={output_filename}")
        if not url_template or not output_filename:
            return jsonify({'error': 'Missing required parameters'}), 400

        os.makedirs('/tmp', exist_ok=True)
        images = []
        counter = 1

        retry =  3

        while True:
            url = url_template.format(counter=counter)
            try:
                response = requests.get(url, verify=False)
                response.raise_for_status()

                if counter == 43:
                    counter += 1
                    continue

                if "Error converting document" in response.text or "errors" in response.text:
                    if (retry <= 0):
                        logger.info("Downloaded all pages")
                        break
                    retry -= 1
                    logger.info("Error converting document, retrying")
                    counter += 1
                    continue                    
                if counter > 500:
                    break

                logger.info(f"Processing page {counter}")
                logger.info(f"Request url: {url}")

                img = Image.open(BytesIO(response.content))

                # Ensure the image is in RGB format (required for JPEG compression)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize the image if necessary (optional)
                resize_factor = 1
                img = img.resize((int(img.width * resize_factor), int(img.height * resize_factor)), Image.Resampling.LANCZOS)

                # Save the image to a buffer in JPEG format
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format="JPEG", quality=30)
                images.append(img_byte_arr.getvalue())
                counter += 1

            except UnidentifiedImageError as e:
                print(f"Error: Cannot identify the image file. The content may not be an image: {e}")
                break
            except IOError as e:
                print(f"Error opening the image: {e}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Error on page {counter}: {e}")
                break

        if not images:
            return jsonify({'error': 'No pages were processed'}), 400

        # Create the PDF using img2pdf
        safe_filename = quote(output_filename.encode('utf-8'))

        pdf_path = f"/tmp/{safe_filename}"
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(images))

        def generate_pdf_chunks():
            """Generator to read and yield chunks of the PDF."""
            with open(pdf_path, "rb") as f:
                while chunk := f.read(4096):  # Read in 4KB chunks
                    yield chunk

        response = app.response_class(
            generate_pdf_chunks(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename*=UTF-8\'\'{safe_filename}'
            }
        )

        @response.call_on_close
        def cleanup():
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"Cleaned up file: {pdf_path}")

        return response

    except Exception as e:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    app.run(debug=True)
