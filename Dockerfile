FROM python:3.10-slim

# Instalar Chromium + ChromeDriver + libs do sistema
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxss1 \
    libappindicator3-1 libasound2 libatk-bridge2.0-0 libgtk-3-0 \
    wget curl unzip gnupg && apt-get clean

# Variáveis para localizar os binários
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Expõe a porta usada pelo Flask
EXPOSE 5000

CMD ["python", "app.py"]