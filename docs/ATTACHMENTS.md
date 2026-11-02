# Anexos no chat

Use o botão de anexo ou arraste arquivos locais para o campo de mensagem. A Noite processa cada item em um worker; não executa o arquivo.

## Formatos e limites

- Texto: TXT, MD, PY, JSON, CSV, XML, LOG, YAML e YML.
- Documentos: PDF, DOCX, XLSX e PPTX.
- Até quatro arquivos por mensagem; 5 MiB por arquivo; expansão de arquivos Office ZIP limitada a 20 MiB; até 40 mil caracteres extraídos por arquivo.
- O chat envia no máximo 12 mil caracteres de anexos por mensagem, com trechos de até 3 mil caracteres por arquivo. Trechos longos são ranqueados por sobreposição de palavras da pergunta; partes omitidas são sinalizadas.
- O PDF usa `PySide6.QtPdf` já fornecido pelo ambiente desktop. PDFs digitalizados sem camada de texto não passam por OCR e são recusados com mensagem explícita.

Os dados extraídos entram como conteúdo da mensagem do usuário, delimitados e descritos como dados não confiáveis. Instruções no documento não substituem as instruções do sistema. A aplicação não envia anexos para serviços externos por conta própria; se o usuário escolher um modelo remoto habilitado, o gateway e as regras de privacidade configuradas determinam o destino da mensagem.

O conteúdo de anexos é mantido na memória da sessão e incluído na mensagem persistida da conversa; portanto, arquivos não são copiados para uma pasta oculta. Remova o histórico da conversa se quiser remover esse conteúdo persistido.
