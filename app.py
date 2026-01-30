from flask import Flask, request, jsonify, send_from_directory
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
from traceback import format_exc
from datetime import datetime
import unicodedata
from werkzeug.utils import secure_filename
import requests
import tempfile


app = Flask(__name__)

UPLOAD_FOLDER = "/curriculo"
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

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

def selecionar_dropdown_ant(driver, wait, input_id, valor, delay_apos=1.5, max_scrolls=15):
    try:
        import unicodedata

        def normalizar(texto):
            if not texto:
                return ""
            return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII").strip()

        # 1. Localiza o input e clica para abrir o dropdown
        input_elem = wait.until(EC.presence_of_element_located((By.ID, input_id)))
        ant_select_container = input_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'ant-select')]")
        seletor = ant_select_container.find_element(By.CLASS_NAME, "ant-select-selector")
        ActionChains(driver).move_to_element(seletor).click().perform()
        time.sleep(0.5)

        # 2. Localiza a listbox pelo ID composto
        listbox_id = f"{input_id}_list"
        listbox_elem = wait.until(EC.presence_of_element_located((By.ID, listbox_id)))

        # 3. Sobe para o dropdown container correspondente
        dropdown_container = listbox_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'ant-select-dropdown') and not(contains(@class, 'ant-select-dropdown-hidden'))]")

        # 4. Dentro do dropdown certo, localiza o scroll container
        scroll_container = dropdown_container.find_element(By.CLASS_NAME, "rc-virtual-list-holder")

        scrolls_feitos = 0
        ultima_qtd_opcoes = 0

        while scrolls_feitos <= max_scrolls:
            opcoes = dropdown_container.find_elements(By.CLASS_NAME, "ant-select-item-option")

            for opcao in opcoes:
                try:
                    titulo = opcao.get_attribute("title")
                    if normalizar(titulo) == normalizar(valor):
                        driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                        wait.until(EC.element_to_be_clickable(opcao))
                        opcao.click()
                        time.sleep(delay_apos)

                        # Captura o valor visível selecionado
                        valor_selecionado = ant_select_container.find_element(By.CLASS_NAME, "ant-select-selection-item").text.strip()
                        return valor_selecionado
                except Exception:
                    continue

            # Scroll incremental
            driver.execute_script("arguments[0].scrollTop += 100;", scroll_container)
            time.sleep(0.5)

            qtd_atual = len(opcoes)
            if qtd_atual == ultima_qtd_opcoes:
                scrolls_feitos += 1
            else:
                ultima_qtd_opcoes = qtd_atual
                scrolls_feitos = 0  # reset contador se aparecerem mais opções

        raise Exception(f"Opção '{valor}' não encontrada após {max_scrolls} scrolls.")

    except Exception as e:
        raise Exception(f"Erro ao selecionar valor '{valor}' para o campo '{input_id}': {e}")

def preencher_formulario(nome, email, telefone, data_nascimento, cpf, origem, tenant, job_code, linkedin, pretencao, estado, cidade, curriculo_url):
    
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

        if nome:
            campo_nome = wait.until(EC.presence_of_element_located((By.ID, "name")))
            campo_nome.send_keys(nome)
            valores_no_dom["nome"] = campo_nome.get_attribute("value")

        if email:
            campo_email = driver.find_element(By.ID, "email")
            campo_email.send_keys(email)
            valores_no_dom["email"] = campo_email.get_attribute("value")

        if telefone:
            campo_telefone = driver.find_element(By.ID, "candidatePhoneNumbers_0_phoneNumber")
            campo_telefone.send_keys(telefone)
            valores_no_dom["telefone"] = campo_telefone.get_attribute("value")

        if data_nascimento:
            campo_data = driver.find_element(By.ID, "birthday")
            campo_data.send_keys(data_nascimento)
            valores_no_dom["data_nascimento"] = campo_data.get_attribute("value")

        if cpf:
            campo_cpf = driver.find_element(By.ID, "candidateCPF")
            campo_cpf.send_keys(cpf)
            valores_no_dom["cpf"] = campo_cpf.get_attribute("value")

        if linkedin:
            campo_linkedin = driver.find_element(By.ID, "linkedInProfile")
            campo_linkedin.send_keys(linkedin)
            valores_no_dom["linkedin"] = campo_linkedin.get_attribute("value")

        if pretencao:
            campo_pretencao = driver.find_element(By.ID, "salaryExpectation")
            campo_pretencao.send_keys(pretencao)
            valores_no_dom["pretencao"] = campo_pretencao.get_attribute("value")

        if estado:
            valor_estado = selecionar_dropdown_ant(driver, wait, "state", estado, delay_apos=2)
            valores_no_dom["estado"] = valor_estado

        if cidade:
            valor_cidade = selecionar_dropdown_ant(driver, wait, "city", cidade, delay_apos=1)
            valores_no_dom["cidade"] = valor_cidade

        if origem:
            valor_origem = selecionar_dropdown_ant(driver, wait, "candidateSource", origem)

        if curriculo_url:
            try:
                response = requests.get(curriculo_url, timeout=15)
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(response.content)
                        tmp_file_path = tmp_file.name

                    try:
                        input_curriculo = wait.until(EC.presence_of_element_located((By.ID, "attachment")))
                        # Remove o display:none temporariamente para permitir o send_keys
                        driver.execute_script("arguments[0].style.display = 'block';", input_curriculo)
                        input_curriculo.send_keys(tmp_file_path)
                        valores_no_dom["curriculo"] = curriculo_url
                        time.sleep(1.5)
                    except Exception as e:
                        browser_logs.append({
                            "level": "ERROR",
                            "message": f"Falha ao preencher campo de currículo: {e}"
                        })
                else:
                    browser_logs.append({
                        "level": "ERROR",
                        "message": f"Falha ao baixar currículo (status {response.status_code})"
                    })
            except Exception as e:
                browser_logs.append({
                    "level": "ERROR",
                    "message": f"Erro ao processar currículo: {e}"
                })

        try:
            botao = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Enviar candidatura']")))
            driver.execute_script("arguments[0].click();", botao)
            time.sleep(5)
        except Exception as e:
            browser_logs.append({
                "level": "ERROR",
                "message": f"Falha ao clicar em 'Enviar candidatura': {e}"
            })

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
    nome = request.args.get("nome") or None
    email = request.args.get("email") or None
    telefone = request.args.get("telefone") or None
    cpf = request.args.get("cpf") or None
    origem = request.args.get("origem") or None
    tenant = request.args.get("tenant") or None
    job_code = request.args.get("job_code") or None
    linkedin = request.args.get("linkedin") or None
    pretencao = request.args.get("pretencao") or None
    estado = request.args.get("estado") or None
    cidade = request.args.get("cidade") or None
    curriculo_url = request.args.get("curriculo_url") or None

    if not tenant or not job_code:
        return jsonify({
            "status": "erro",
            "mensagem": "Parâmetros 'tenant' e 'job_code' são obrigatórios."
        }), 400

    # Validação de data de nascimento (mantida)
    if request.args.get("data_nascimento"):
        try:
            data_nascimento_raw = request.args.get("data_nascimento")
            data_nascimento = formatar_data_nascimento(data_nascimento_raw)
        except Exception as e:
            return jsonify({
                "status": "erro",
                "mensagem": f"Data de nascimento inválida: {e}"
            }), 400
    else:
        data_nascimento = None

    # Chama a função Selenium com o novo parâmetro
    sucesso, logs, valores_dom = preencher_formulario(
        nome, email, telefone, data_nascimento, cpf,
        origem, tenant, job_code, linkedin, pretencao,
        estado, cidade, curriculo_url
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

#UPLOAD DO ARQUIV NO RAILWAY
@app.route("/curriculo/<filename>")
def get_curriculo(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/upload-curriculo", methods=["POST"])
def upload_curriculo():

    entry_id = request.form.get("entry_id")

    if not entry_id:
        return jsonify({"erro": "Parâmetro 'entry_id' é obrigatório."}), 400

    if "file" not in request.files:
        return jsonify({"erro": "Arquivo não enviado"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"erro": "Nome de arquivo inválido"}), 400

    # Validação da extensão
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else None
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "erro": f"Extensão não permitida. Tipos aceitos: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # Validação de tamanho
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    if file_length > MAX_FILE_SIZE:
        return jsonify({"erro": "Arquivo excede o tamanho máximo de 2MB"}), 400

    # Garante que o diretório existe
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Nome do arquivo padronizado: entry_id.extensão
    safe_entry_id = secure_filename(str(entry_id))
    filename = f"{safe_entry_id}.{ext}"

    # Salva o arquivo
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    # URL pública no Railway
    base_url = "https://seleniumapp-production.up.railway.app"
    file_url = f"{base_url}/curriculo/{filename}"

    return jsonify({
        "status": "ok",
        "mensagem": "Arquivo enviado com sucesso.",
        "url": file_url,
        "filename": filename
    }), 200

#FUNÇÕES AUXILIARES
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def obter_arquivo_curriculo(cpf):
    pasta = "/curriculo"
    extensoes = [".pdf", ".doc", ".docx", ".jpg", ".png", ".jpeg", ".webp"]
    tamanho_maximo = 2 * 1024 * 1024  # 2MB

    for ext in extensoes:
        caminho = os.path.join(pasta, f"{cpf}{ext}")
        if os.path.isfile(caminho):
            tamanho = os.path.getsize(caminho)
            if tamanho > tamanho_maximo:
                raise ValueError("O tamanho do arquivo excedeu o limite de 2Mb")
            return caminho

    raise FileNotFoundError("Arquivo de currículo não encontrado")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
