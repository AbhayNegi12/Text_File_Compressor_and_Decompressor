# app.py
from flask import Flask, render_template, request, jsonify
import base64
from huffman_compression import (
    huffman_compress_bytes,
    huffman_decompress_bytes
)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

# --------- COMPRESS ----------
@app.route("/compress", methods=["POST"])
def compress():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    data = file.read() 
    compressed_blob, original_bits, compressed_bits = huffman_compress_bytes(data)

    result = {
        "original_size": len(data),
        "compressed_size": len(compressed_blob),
        "original_bits": original_bits,
        "compressed_bits": compressed_bits,
        "percent": round((1 - (compressed_bits / original_bits)) * 100, 2) if original_bits else 0.0,
        "filedata": base64.b64encode(compressed_blob).decode("ascii"),
        "filename": "compressed_output.huf",
        "mimetype": "application/octet-stream"
    }
    return jsonify(result)

# --------- DECOMPRESS ----------
@app.route("/decompress", methods=["POST"])
def decompress():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    blob = file.read() 
    try:
        decoded = huffman_decompress_bytes(blob)
    except Exception as e:
        return jsonify({"error": f"Invalid .huf file: {e}"}), 400

    try:
        decoded_text = decoded.decode("utf-8")
    except:
        return jsonify({"error": "Decompressed data is not valid UTF-8 text"}), 400

    result = {
        "original_size": len(decoded_text),
        "filedata": base64.b64encode(decoded_text.encode("utf-8")).decode("ascii"),
        "filename": "decompressed_output.txt",  
        "mimetype": "text/plain"
    }
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
