# app.py
import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Importando o que criamos no outro arquivo:
from config import RECEITA_SCHEMA, SYSTEM_INSTRUCTION

# Carrega as variáveis de ambiente e inicia o Gemini
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Inicializa o Flask
app = Flask(__name__)
CORS(app)


def generate_recipe(ingredientes):
    """Chama o Gemini para gerar a receita"""
    lista_ingredientes = ", ".join(ingredientes)
    conteudo_prompt = f"Crie uma receita utilizando obrigatoriamente estes ingredientes: {lista_ingredientes}."
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=conteudo_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=RECEITA_SCHEMA,
        )
    )
    return response.text


@app.route("/")
def root():
    return jsonify({
        "status": "success",
        "message": "API Gerador de Receitas funcionando!",
        "version": "2.0"
    }), 200


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    
    # Validação 1: O JSON foi enviado?
    if not data or "ingredientes" not in data:
        return jsonify({
            "status": "error",
            "message": "Por favor, envie uma lista de ingredientes no formato JSON."
        }), 400
        
    ingredientes = data.get("ingredientes", [])
    
    # Validação 2: É uma lista e possui no mínimo 1 item?
    if not isinstance(ingredientes, list) or len(ingredientes) < 1:
        return jsonify({
            "status": "error",
            "message": "Você precisa fornecer pelo menos 1 ingrediente."
        }), 400
    
    try:
        # Pega a resposta do Gemini (JSON string)
        receita_json_string = generate_recipe(ingredientes)
        
        # Converte para dicionário Python
        receita_estruturada = json.loads(receita_json_string)
        
        # VERIFICA SE FOI RECUSADO
        if receita_estruturada.get("status") == "recusada":
            return jsonify({
                "status": "recusado",
                "mensagem": receita_estruturada.get("motivo_recusa", "Ingrediente não permitido para receita."),
                "ingredientes_enviados": ingredientes
            }), 400  # Bad Request
        
        # Se chegou aqui, foi aceito → retorna a receita normal
        return jsonify({
            "status": "success",
            "ingredientes_enviados": ingredientes,
            "dados_receita": {
                "nome": receita_estruturada.get("nome_da_receita"),
                "porcoes": receita_estruturada.get("porcoes"),
                "tempo_preparo": receita_estruturada.get("tempo_de_preparo"),
                "ingredientes": receita_estruturada.get("ingredientes", []),
                "modo_preparo": receita_estruturada.get("modo_de_preparo", [])
            }
        }), 200
        
    except json.JSONDecodeError as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao processar resposta do Gemini: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro ao gerar a receita: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(debug=True)