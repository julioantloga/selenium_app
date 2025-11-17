FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt‑get update && \
    apt‑get install -y --no-install-recommends \
      chromium-browser \
      chromium-chromedriver \
      libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxss1 \
      libappindicator3-1 libasound2 libatk-bridge2.0-0 libgtk-3-0 \
      wget curl unzip gnupg && \
    apt‑get clean && rm ‑rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python","app.py"]
