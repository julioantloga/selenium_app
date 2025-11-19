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
from datetime import datetime
import unicodedata

app = Flask(__name__)


def formatar_data_nascimento(data):
    formatos_possiveis = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for fmt in formatos_possiveis:
        try:
            dt = datetime.strptime(data, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue

    raise ValueError(f"Formato de data inválido: '{data}'. Use DD/MM/AAAA ou formatos comuns.")


def normalizar(texto):
    if not texto:
        return ""
    return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII").strip()


def selecionar_dropdown_ant(driver, wait, input_id, valor, delay_apos=1.5, max_scrolls=10):
    try:
        input_elem = wait.until(EC.presence_of_element_located((By.ID, input_id)))
        ant_select_container = input_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'ant-select')]")
        seletor = ant_select_container.find_element(By.CLASS_NAME, "ant-select-selector")
        ActionChains(driver).move_to_element(seletor).click().perform()

        # Espera dropdown abrir
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ant-select-item-option")))
        time.sleep(0.5)

        dropdown_popup = driver.find_element(By.CLASS_NAME, "ant-select-dropdown")
        scroll_container = dropdown_popup.find_element(By.CLASS_NAME, "rc-virtual-list-holder-inner")

        scroll_attempts = 0
        ultima_qtd_opcoes = 0

        while scroll_attempts < max_scrolls:
            opcoes = dropdown_popup.find_elements(By.CLASS_NAME, "ant-select-item-option")

            for opcao in opcoes:
                texto = opcao.text.strip()
                if normalizar(texto) == normalizar(valor):
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                    wait.until(EC.element_to_be_clickable(opcao))
                    opcao.click()
                    time.sleep(delay_apos)
                    valor_selecionado = ant_select_container.find_element(By.CLASS_NAME, "ant-select-selection-item").text.strip()
                    return valor_selecionado

            # Scroll para baixo
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop + 100;", scroll_container)
            time.sleep(0.5)

            # Verifica se surgiram novas opções
            nova_qtd = len(dropdown_popup.find_elements(By.CLASS_NAME, "ant-select-item-option"))
            if nova_qtd == ultima_qtd_opcoes:
                scroll_attempts += 1
            else:
                scroll_attempts = 0  # reseta se encontrar mais opções
                ultima_qtd_opcoes = nova_qtd

        raise Exception(f"Opção '{valor}' não encontrada após {max_scrolls} scrolls.")

    except Exception as e:
        raise Exception(f"Erro ao selecionar valor '{valor}' para o campo '{input_id}': {e}")


def preencher_formulario(nome, email, telefone, data_nascimento, cpf, origem, tenant, job_code, linkedin, pretencao, pais, estado, cidade):
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
        url = f"https://oportunidades.mindsight.com.br/{tenant}/{job_code}/register"
        driver.get(url)
        wait = WebDriverWait(driver, 10)

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

        campo_linkedin = driver.find_element(By.ID, "linkedInProfile")
        campo_linkedin.send_keys(linkedin or "")
        campo_pretencao = driver.find_element(By.ID, "salaryExpectation")
        campo_pretencao.send_keys(pretencao or "")

        # Dropdowns encadeados
        valor_pais = selecionar_dropdown_ant(driver, wait, "country", pais, delay_apos=2)
        valor_estado = selecionar_dropdown_ant(driver, wait, "state", estado, delay_apos=2)
        valor_cidade = selecionar_dropdown_ant(driver, wait, "city", cidade, delay_apos=1)
        valor_origem = selecionar_dropdown_ant(driver, wait, "candidateSource", origem)

        valores_no_dom = {
            "nome": campo_nome.get_attribute("value"),
            "email": campo_email.get_attribute("value"),
            "telefone": campo_telefone.get_attribute("value"),
            "data_nascimento": campo_data.get_attribute("value"),
            "cpf": campo_cpf.get_attribute("value"),
            "linkedin": campo_linkedin.get_attribute("value"),
            "pretencao": campo_pretencao.get_attribute("value"),
            "pais": valor_pais,
            "estado": valor_estado,
            "cidade": valor_cidade,
            "origem": valor_origem
        }

        botao = driver.find_element(By.XPATH, "//button[.//span[text()='Enviar candidatura']]")
        driver.execute_script("arguments[0].click();", botao)

        time.sleep(5)

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
    origem = request.args.get("origem", "Instagram")
    tenant = request.args.get("tenant")
    job_code = request.args.get("job_code")
    linkedin = request.args.get("linkedin", "")
    pretencao = request.args.get("pretencao", "")
    pais = request.args.get("pais")
    estado = request.args.get("estado")
    cidade = request.args.get("cidade")

    if not all([tenant, job_code]):
        return jsonify({
            "status": "erro",
            "mensagem": "Parâmetros 'tenant' e 'job_code' são obrigatórios."
        }), 400

    if not all([pais, estado, cidade]):
        return jsonify({
            "status": "erro",
            "mensagem": "Parâmetros 'pais', 'estado' e 'cidade' são obrigatórios."
        }), 400

    try:
        data_nascimento_raw = request.args.get("data_nascimento")
        data_nascimento = formatar_data_nascimento(data_nascimento_raw)
    except Exception as e:
        return jsonify({
            "status": "erro",
            "mensagem": f"Data de nascimento inválida: {e}"
        }), 400

    if not all([nome, email, telefone, cpf, data_nascimento]):
        return jsonify({
            "status": "erro",
            "mensagem": "Parâmetros obrigatórios ausentes."
        }), 400

    sucesso, logs, valores_dom = preencher_formulario(
        nome, email, telefone, data_nascimento, cpf,
        origem, tenant, job_code, linkedin, pretencao,
        pais, estado, cidade
    )

    if sucesso:
        return jsonify({
            "status": "ok",
            "mensagem": "Formulário enviado com sucesso.",
            "valores_no_dom": valores_dom
        })
    else:
        return jsonify({
            "status": "erro",
            "mensagem": "Erro ao enviar formulário.",
            "valores_no_dom": valores_dom,
            "logs": logs
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
