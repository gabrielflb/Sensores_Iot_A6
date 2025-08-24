# Sensores_Iot_A6
Implementação de sensores Iot para atividade 6 de tópicos avançado em web 2. 

Instruções de Execução Local
A execução do projeto é gerenciada integralmente com Docker, simplificando a configuração do ambiente.

1. Pré-requisitos:

Docker e Docker Compose instalados e em execução.

2. Configuração do Ambiente:

Crie um arquivo chamado .env na raiz do projeto.

Adicione as seguintes chaves secretas a ele:

Ini, TOML

AES_KEY=sua-chave-secreta-de-32-caracteres
JWT_SECRET=seu-jwt-super-secreto-qualquer
3. Execução da Aplicação:

Abra um terminal na pasta raiz do projeto e execute o comando abaixo para construir e iniciar todos os serviços (Broker MQTT, Backend e Frontend):

Bash

docker-compose up --build
Acesse a interface web em http://localhost.

4. Execução dos Sensores:

Em novos terminais, execute os scripts dos sensores para começar a enviar dados:

Bash

# Iniciar sensor de temperatura
python Sensores_Iot/Iot-A6/app/sensor_temperatura_mqtt.py

# Iniciar sensor de presença
python Sensores_Iot/Iot-A6/app/sensor_presenca_mqtt.py

# Iniciar sensor de gás
python Sensores_Iot/Iot-A6/app/sensor_gas_coap.py
5. Simulação de Ataque:

Para simular o envio de dados não criptografados e observar o alerta no frontend, execute o sensor malicioso:

Bash

python Sensores_Iot/Iot-A6/app/sensor_temperatura_malicioso_mqtt.py
6. Parar a Aplicação:

Para encerrar todos os serviços, pressione Ctrl + C no terminal onde o docker-compose está rodando, e depois execute:

Bash

docker-compose down
