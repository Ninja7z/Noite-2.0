# Build do lançador Windows

O executável é um lançador desktop do checkout local: inicia o aplicativo usando o ambiente virtual preparado neste projeto. Ele não embute o interpretador, as dependências Python, o Ollama ou os pesos do modelo. O checkout e o ambiente virtual são requisitos documentados; este formato não é um instalador portátil. O ícone da janela e do executável usa `assets/noite.ico`, recortado da marca da lua roxa presente nas referências do produto.

## Construção

No PowerShell, a partir da raiz do repositório, crie um venv Python 3.13 e instale as dependências:

    py -3.13 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -e ".[desktop,build]"
    .\scripts\build_windows.ps1

O resultado padrão fica em `dist\Noite.exe`. Para gerar um nome separado e preservar um executável anterior, informe `-Name`:

    .\scripts\build_windows.ps1 -Name Noite-2.0-Evolution-20261101

Para copiar esse artefato à Área de Trabalho:

    .\scripts\build_windows.ps1 -Name Noite-2.0-Evolution-20261101 -CopyToDesktop

O lançador registra o caminho do checkout usado na construção. Se o checkout ou o ambiente virtual for movido ou recriado, gere um novo lançador. O primeiro uso requer que as dependências de desktop e build estejam instaladas no venv.

## Por que este executável é um lançador

A captura enviada mostra o cx_Freeze encerrando ao importar `QtWidgets` com `DLL load failed` / “Não foi possível encontrar o procedimento especificado”. Esse texto aponta para uma falha na resolução ou compatibilidade de DLLs nativas do Qt; não identifica sozinho qual DLL ou versão divergiu. Os testes locais de congelamento também reproduziram a falha com um exemplo PySide6 mínimo no cx_Freeze e no PyInstaller. A tentativa com Nuitka/pyside6-deploy parou durante a compilação de uma dependência do LiteLLM.

Para entregar um atalho executável que abre o aplicativo nesta máquina, `Noite.exe` empacota somente um bootstrap e inicia `pythonw.exe` do venv do checkout. Assim, o Qt é carregado pelo ambiente em que a interface foi validada. Isso contorna o erro observado, mas não corrige nem valida um pacote independente. O executável deixará de funcionar se o checkout ou `.venv` for removido/movido; para distribuição a outros PCs, falta concluir um build standalone e testá-lo em Windows limpo. A documentação oficial do Qt recomenda `pyside6-deploy` e classifica o suporte PyInstaller a Qt 6 como parcial.

## Dependências, configurações e dados

Inicie o Ollama e instale manualmente o modelo indicado nas configurações (padrão `qwen2.5:3b`). O endereço padrão é `http://127.0.0.1:11434`. O lançador herda as variáveis de ambiente. O arquivo `.env` permanece fora do executável.

O histórico e as configurações ficam em %USERPROFILE%\.noite, separados do checkout, do venv e do executável. Reconstruir ou substituir Noite.exe não os apaga.

Roblox Studio e seus servidores MCP não são instalados pelo lançador. Cada integração MCP continua configurada localmente pelo usuário.

## Validação

Execute compileall, `ruff check .`, `pytest -q` e `git diff --check` antes do build. Inicie o executável criado e confirme a janela, ícone e encerramento. Este smoke test não comprova distribuição standalone nem substitui um teste manual de conversa com Ollama. Os diretórios build e dist são artefatos locais ignorados pelo Git.
