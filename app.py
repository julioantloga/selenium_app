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

    # Caminho para o ChromeDriver no container
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://oportunidades.mindsight.com.br/demoprodutos/428/register")
        wait = WebDriverWait(driver, 10)

        # Preencher campos obrigatórios
        wait.until(EC.presence_of_element_located((By.ID, "name"))).send_keys(nome)
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "candidatePhoneNumbers_0_phoneNumber").send_keys(telefone)
        driver.find_element(By.ID, "birthday").send_keys(data_nascimento)
        driver.find_element(By.ID, "candidateCPF").send_keys(cpf)

        # Clicar no container real do select (não no input oculto)
        select_container = driver.find_element(By.CLASS_NAME, "ant-select")
        driver.execute_script("arguments[0].click();", select_container)

        # Esperar o dropdown renderizar no DOM
        wait = WebDriverWait(driver, 5)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ant-select-dropdown")))

        # Agora buscar as opções visíveis
        dropdown_container = driver.find_element(By.CLASS_NAME, "ant-select-dropdown")
        opcoes = dropdown_container.find_elements(By.CLASS_NAME, "ant-select-item-option")

        if len(opcoes) >= 2:
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ant-select-item-option")))
            opcoes[1].click()  # clica na segunda opção
        else:
            raise Exception("Menos de 2 opções encontradas no selectbox.")


        # # Enviar o formulário
        # botao = driver.find_element(By.XPATH, "//button[.//span[text()='Enviar candidatura']]")
        # driver.execute_script("arguments[0].click();", botao)

        time.sleep(5)  # espera resposta
        return True

    except Exception as e:
        print("🚨 Erro ao preencher/enviar formulário:")
        print(format_exc())  # mostra traceback completo
        return False

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
        return jsonify({"status": "erro", "mensagem": "Parâmetros obrigatórios ausentes."}), 400

    sucesso = preencher_formulario(nome, email, telefone, data_nascimento, cpf, origem)

    if sucesso:
        return jsonify({"status": "ok", "mensagem": "Formulario enviado com sucesso."})
    else:
        return jsonify({"status": "erro", "mensagem": "Erro ao enviar formulario."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
