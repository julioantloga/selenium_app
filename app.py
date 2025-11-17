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
        driver.find_element(By.ID, "birthday").send_keys("17/11/2000")
        driver.find_element(By.ID, "candidateCPF").send_keys(cpf)
        
        # Clica no container do dropdown (não no input invisível)
        select_container = driver.find_element(By.CLASS_NAME, "ant-select")
        driver.execute_script("arguments[0].click();", select_container)

        # Espera o dropdown aparecer de verdade
        wait = WebDriverWait(driver, 10)
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "ant-select-dropdown")))

        # Aguarda que a lista de opções fique disponível e visível
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ant-select-item-option")))

        # Busca as opções pelo texto interno
        opcoes = driver.find_elements(By.CLASS_NAME, "ant-select-item-option")

        # Define a opção que você quer selecionar (pode vir da URL ou fixo)
        texto_desejado = origem.strip() if origem else "Instagram"

        clicou = False
        for opcao in opcoes:
            try:
                texto_opcao = opcao.text.strip().lower()
                if texto_opcao == texto_desejado.lower():
                    # Scroll até a opção (importante para listas com scroll virtual)
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)

                    # Espera que esteja clicável
                    wait.until(EC.element_to_be_clickable(opcao))

                    # Usa ActionChains para simular um clique real
                    actions = ActionChains(driver)
                    actions.move_to_element(opcao).click().perform()
                    clicou = True
                    break
            except Exception as e:
                print("Erro ao tentar clicar na opção:", e)

        if not clicou:
            raise Exception(f"⚠️ Não foi possível encontrar ou clicar na opção '{texto_desejado}' do dropdown.")


        # Enviar o formulário
        botao = driver.find_element(By.XPATH, "//button[.//span[text()='Enviar candidatura']]")
        driver.execute_script("arguments[0].click();", botao)

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
