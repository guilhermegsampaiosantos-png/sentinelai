# Como gerar o instalador do SentinelAI

Isso transforma o projeto em um `SentinelAI_Setup.exe` único: o usuário final
clica duas vezes, segue o assistente e o app aparece pronto na Área de
Trabalho e no Menu Iniciar — **sem precisar instalar Python, pip ou
dependência nenhuma**.

Esse processo precisa ser feito **uma vez, em um computador Windows**, por
quem for distribuir o programa. Depois disso, o `SentinelAI_Setup.exe`
gerado pode ser copiado e enviado para qualquer outro Windows normalmente.

## Pré-requisitos (só na máquina que vai *gerar* o instalador)

1. **Python 3.11+** — https://python.org/downloads (marque "Add python.exe
   to PATH" durante a instalação)
2. **Inno Setup** (gratuito) — https://jrsoftware.org/isdl.php

## Passo a passo

1. Extraia o projeto (o .zip inteiro) em uma pasta.
2. Entre na pasta `packaging` e dê duplo clique em **`build_exe.bat`**.
   - Isso cria um ambiente virtual, instala as dependências do
     `requirements.txt`, instala o PyInstaller e gera
     `dist\SentinelAI.exe` (um executável único, com ícone, sem console).
   - Leva alguns minutos na primeira vez.
3. Abra o arquivo **`packaging\installer.iss`** com o Inno Setup (duplo
   clique nele, se o Inno Setup já estiver instalado, abre direto).
4. No Inno Setup, aperte **Compile** (ícone de engrenagem verde, ou F9).
5. Pronto: o instalador final fica em
   `packaging\Output\SentinelAI_Setup.exe`.

## O que o instalador faz pelo usuário final

- Assistente de instalação em português, sem precisar ser administrador.
- Cria atalho no Menu Iniciar e (opcionalmente, já vem marcado) na Área de
  Trabalho, com o ícone do SentinelAI.
- Registra um desinstalador (aparece em "Aplicativos instalados" do
  Windows).
- Ao final, oferece abrir o SentinelAI na hora.

## Sobre os dados salvos (Contexto da Empresa)

Quando rodando como `.exe` instalado, o app salva o Contexto da Empresa em
`%APPDATA%\SentinelAI\company_context.json` (pasta pessoal do usuário —
persiste entre aberturas e atualizações do programa). Quando rodando a
partir do código-fonte (`py main.py`), continua salvando em `data/` dentro
do projeto, como antes.

## Atualizando uma versão nova

Para gerar uma nova versão do instalador depois de alterar o código, repita
os passos 2 a 4. Se quiser, aumente o número em `MyAppVersion` no topo do
`installer.iss` antes de compilar.

## Nota

Este ambiente (usado para editar o código) não tem Windows, então não é
possível gerar o `.exe` final diretamente aqui — o PyInstaller precisa
rodar no mesmo sistema operacional do executável de destino. Os scripts
acima automatizam tudo; falta apenas rodá-los uma vez em uma máquina
Windows.
