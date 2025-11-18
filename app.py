from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import time
from traceback import format_exc

app = Flask(__name__)


def selecionar_origem(driver, wait, origem):
    try:
        # Localiza o input com id candidateSource
        input_elem = wait.until(EC.presence_of_element_located((By.ID, "candidateSource")))

        # Sobe até o componente ant-select pai
        ant_select_container = input_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'ant-select')]")

        # Dentro do container, localiza o seletor clicável
        seletor = ant_select_container.find_element(By.CLASS_NAME, "ant-select-selector")
        ActionChains(driver).move_to_element(seletor).click().perform()

        # Aguarda as opções renderizadas visíveis
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ant-select-item-option")))

        opcoes = driver.find_elements(By.CLASS_NAME, "ant-select-item-option")
        for opcao in opcoes:
            texto = opcao.text.strip()
            if texto.lower() == origem.lower():
                driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                wait.until(EC.element_to_be_clickable(opcao))
                opcao.click()
                break

        # Captura o valor visível selecionado
        valor_selecionado = ant_select_container.find_element(By.CLASS_NAME, "ant-select-selection-item").text.strip()
        return valor_selecionado

    except Exception as e:
        raise Exception(f"Erro ao selecionar origem '{origem}': {e}")



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
    valores_no_dom = {}

    try:
        driver.get("https://oportunidades.mindsight.com.br/demoprodutos/458/register")
        wait = WebDriverWait(driver, 10)

        # Preenche os campos
        campo_nome = wait.until(EC.presence_of_element_located((By.ID, "name")))
        campo_nome.send_keys(nome)
        campo_email = driver.find_element(By.ID, "email")
        campo_email.send_keys(email)
        campo_telefone = driver.find_element(By.ID, "candidatePhoneNumbers_0_phoneNumber")
        campo_telefone.send_keys(telefone)
        campo_data = driver.find_element(By.ID, "birthday")
        campo_data.send_keys(data_nascimento)
        campo_cpf = driver.find_element(By.ID, "candidateCPF")
        campo_cpf.send_keys(cpf)

        # Seleciona a origem via dropdown Ant Design
        valor_origem = selecionar_origem(driver, wait, origem)

        # Captura os valores reais no DOM
        valores_no_dom = {
            "nome": campo_nome.get_attribute("value"),
            "email": campo_email.get_attribute("value"),
            "telefone": campo_telefone.get_attribute("value"),
            "data_nascimento": campo_data.get_attribute("value"),
            "cpf": campo_cpf.get_attribute("value"),
            "origem": valor_origem
        }

        # Clica no botão "Enviar candidatura"
        botao = driver.find_element(By.XPATH, "//button[.//span[text()='Enviar candidatura']]")
        driver.execute_script("arguments[0].click();", botao)

        time.sleep(5)

        # Captura os logs do navegador
        logs = driver.get_log("browser")
        for entry in logs:
            browser_logs.append({
                "level": entry.get("level"),
                "message": entry.get("message")
            })

        return True, browser_logs, valores_no_dom

    except Exception as e:
        browser_logs.append({
            "level": "ERROR",
            "message": str(e),
            "traceback": format_exc()
        })
        return False, browser_logs, valores_no_dom

    finally:
        driver.quit()


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Olá! Sistema de automação ativo."})


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

    sucesso, logs, valores_dom = preencher_formulario(nome, email, telefone, data_nascimento, cpf, origem)

    valores_enviados = {
        "nome": nome,
        "email": email,
        "telefone": telefone,
        "data_nascimento": data_nascimento,
        "cpf": cpf,
        "origem": origem
    }

    if sucesso:
        return jsonify({
            "status": "ok",
            "mensagem": "Formulário enviado com sucesso.",
            "valores_enviados": valores_enviados,
            "valores_no_dom": valores_dom,
            "logs": logs
        })
    else:
        return jsonify({
            "status": "erro",
            "mensagem": "Erro ao enviar formulário.",
            "valores_enviados": valores_enviados,
            "valores_no_dom": valores_dom,
            "logs": logs
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
