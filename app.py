from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time
from traceback import format_exc

app = Flask(__name__)

def preencher_formulario(nome, email, telefone, data_nascimento, cpf, origem):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    browser_logs = []

    try:
        driver.get("https://oportunidades.mindsight.com.br/demoprodutos/458/register")
        wait = WebDriverWait(driver, 10)

        # Preencher campos
        wait.until(EC.presence_of_element_located((By.ID, "name"))).send_keys(nome)
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "candidatePhoneNumbers_0_phoneNumber").send_keys(telefone)
        driver.find_element(By.ID, "birthday").send_keys("17/11/2000")
        driver.find_element(By.ID, "candidateCPF").send_keys(cpf)

        # Campo origem: remove obrigatoriedade
        campo_origem = driver.find_element(By.ID, "candidateSource")
        driver.execute_script("arguments[0].removeAttribute('required')", campo_origem)
        driver.execute_script("arguments[0].removeAttribute('aria-required')", campo_origem)
        driver.execute_script("arguments[0].removeAttribute('readonly')", campo_origem)
        campo_origem.send_keys(origem)

        # Clicar no botão Enviar
        botao = driver.find_element(By.XPATH, "//button[.//span[text()='Enviar candidatura']]")
        driver.execute_script("arguments[0].click();", botao)

        # Esperar algo acontecer
        time.sleep(5)

        # Captura os logs do navegador
        logs = driver.get_log("browser")
        for entry in logs:
            browser_logs.append({
                "level": entry.get("level"),
                "message": entry.get("message")
            })

        return True, browser_logs

    except Exception as e:
        browser_logs.append({
            "level": "ERROR",
            "message": str(e),
            "traceback": format_exc()
        })
        return False, browser_logs

    finally:
        driver.quit()


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Olá!"})


@app.route("/inscricaofinal", methods=["GET"])
def inscricao_final():
    nome = request.args.get("nome")
    email = request.args.get("email")
    telefone = request.args.get("telefone")
    cpf = request.args.get("cpf")
    data_nascimento = request.args.get("data_nascimento")
    origem = request.args.get("origem", "Instagram")

    if not all([nome, email, telefone, cpf, data_nascimento]):
        return jsonify({
            "status": "erro",
            "mensagem": "Parâmetros obrigatórios ausentes."
        }), 400

    sucesso, logs = preencher_formulario(nome, email, telefone, data_nascimento, cpf, origem)

    if sucesso:
        return jsonify({
            "status": "ok",
            "mensagem": "Formulário enviado com sucesso.",
            "logs": logs
        })
    else:
        return jsonify({
            "status": "erro",
            "mensagem": "Erro ao enviar formulário.",
            "logs": logs
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
